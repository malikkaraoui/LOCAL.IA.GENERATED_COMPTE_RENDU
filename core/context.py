"""Construction d'index BM25 et récupération de passages."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from .models import Chunk

TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+")
FR_STOP = {
    "le","la","les","un","une","des","de","du","d","et","en","à","a","au","aux","pour","par",
    "sur","dans","avec","sans","ce","cet","cette","ces","il","elle","ils","elles","on",
    "que","qui","quoi","dont","où","se","sa","son","ses","leur","leurs","plus","moins",
    "est","sont","été","être","avoir","avait","ont","a","y","ne","pas","comme"
}


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    if chunk_size <= overlap:
        raise ValueError("chunk_size doit être > overlap")

    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


def tokenize(text: str, remove_stop: bool = True) -> list[str]:
    tokens = [m.group(0).lower() for m in TOKEN_RE.finditer(text)]
    if remove_stop:
        tokens = [t for t in tokens if t not in FR_STOP and len(t) > 1]
    return tokens


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b

        self.doc_len: list[int] = []
        self.avgdl: float = 0.0
        self.df: dict[str, int] = {}
        self.tf: list[dict[str, int]] = []
        self._build()

    def _build(self) -> None:
        total_len = 0
        for ch in self.chunks:
            toks = tokenize(ch.text)
            freqs: dict[str, int] = {}
            for t in toks:
                freqs[t] = freqs.get(t, 0) + 1
            self.tf.append(freqs)
            dl = sum(freqs.values())
            self.doc_len.append(dl)
            total_len += dl
            for t in freqs.keys():
                self.df[t] = self.df.get(t, 0) + 1
        self.avgdl = (total_len / len(self.chunks)) if self.chunks else 0.0

    def _idf(self, term: str) -> float:
        n = len(self.chunks)
        df = self.df.get(term, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5)) if n > 0 else 0.0

    def score(self, query: str, idx: int) -> float:
        q_terms = tokenize(query)
        if not q_terms:
            return 0.0
        freqs = self.tf[idx]
        dl = self.doc_len[idx]
        if dl == 0 or self.avgdl == 0:
            return 0.0
        score = 0.0
        for t in q_terms:
            if t not in freqs:
                continue
            tf = freqs[t]
            idf = self._idf(t)
            denom = tf + self.k1 * (1 - self.b + self.b * (dl / self.avgdl))
            score += idf * (tf * (self.k1 + 1)) / denom
        return score

    def topk(self, query: str, k: int = 8) -> list[tuple[int, float]]:
        scored = []
        for i in range(len(self.chunks)):
            s = self.score(query, i)
            if s > 0:
                scored.append((i, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


def path_allowed(path: str, include: Optional[Sequence[str]], exclude: Optional[Sequence[str]]) -> bool:
    low = path.lower()
    if exclude:
        for ex in exclude:
            if ex and ex.lower() in low:
                return False
    if include:
        return any(inc.lower() in low for inc in include if inc)
    return True


def make_chunks(
    payload: dict,
    *,
    chunk_size: int = 1200,
    overlap: int = 200,
    include: Optional[Sequence[str]] = None,
    exclude: Optional[Sequence[str]] = None,
) -> list[Chunk]:
    docs = payload.get("documents", [])
    chunks: list[Chunk] = []
    for d in docs:
        src = d.get("path", "")
        if not path_allowed(src, include, exclude):
            continue
        ext = d.get("ext", "")
        text = d.get("text", "") or ""
        pages = d.get("pages")
        if ext == ".pdf" and isinstance(pages, list) and pages:
            for page in pages:
                page_num = page.get("page")
                page_text = page.get("text", "") or ""
                for j, ct in enumerate(chunk_text(page_text, chunk_size, overlap)):
                    cid = f"{Path(src).name}::p{page_num}::c{j}"
                    chunks.append(Chunk(chunk_id=cid, source_path=src, page=page_num, text=ct))
        else:
            for j, ct in enumerate(chunk_text(text, chunk_size, overlap)):
                cid = f"{Path(src).name}::c{j}"
                chunks.append(Chunk(chunk_id=cid, source_path=src, page=None, text=ct))
    return chunks


def build_index(
    payload: dict,
    *,
    chunk_size: int = 1200,
    overlap: int = 200,
    include: Optional[Sequence[str]] = None,
    exclude: Optional[Sequence[str]] = None,
) -> tuple[list[Chunk], BM25Index]:
    chunks = make_chunks(payload, chunk_size=chunk_size, overlap=overlap, include=include, exclude=exclude)
    index = BM25Index(chunks)
    return chunks, index
