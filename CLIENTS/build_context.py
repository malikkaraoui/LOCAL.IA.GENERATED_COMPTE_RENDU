#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_context.py
----------------
Construit un "contexte RAG" à partir du JSON produit par extract_sources.py.

- Charge out/*_extracted.json
- Découpe en chunks (taille + overlap)
- Indexe en BM25 (sans dépendances)
- Permet de récupérer les TOP-K chunks pour une requête

Exemples :
  python3 build_context.py --extracted "out/karaoui_extracted.json" --query "profession et formation" --topk 8
  python3 build_context.py --extracted "out/karaoui_extracted.json" --query "résultats discussion avec l’assuré" --topk 10 --out "out/context.json"

Optionnel (debug) :
  python3 build_context.py --extracted "out/karaoui_extracted.json" --dump-chunks "out/chunks.jsonl"
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# -----------------------
# Chunking
# -----------------------

@dataclass
class Chunk:
    chunk_id: str
    source_path: str
    page: Optional[int]
    text: str


def normalize_text(t: str) -> str:
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    """
    Découpe un texte en morceaux de longueur approx chunk_size, avec overlap.
    Découpage par caractères (simple, rapide, fiable).
    """
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
        start = end - overlap
        if start < 0:
            start = 0
        if end == n:
            break
    return chunks


# -----------------------
# Tokenization (FR simple)
# -----------------------

TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+")

FR_STOP = {
    # stopwords minimalistes (tu peux en ajouter)
    "le","la","les","un","une","des","de","du","d","et","en","à","a","au","aux","pour","par",
    "sur","dans","avec","sans","ce","cet","cette","ces","il","elle","ils","elles","on",
    "que","qui","quoi","dont","où","se","sa","son","ses","leur","leurs","plus","moins",
    "est","sont","été","être","avoir","avait","ont","a","y","ne","pas","comme"
}

def tokenize(text: str, remove_stop: bool = True) -> List[str]:
    tokens = [m.group(0).lower() for m in TOKEN_RE.finditer(text)]
    if remove_stop:
        tokens = [t for t in tokens if t not in FR_STOP and len(t) > 1]
    return tokens


# -----------------------
# BM25
# -----------------------

class BM25Index:
    def __init__(self, chunks: List[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b

        self.doc_len: List[int] = []
        self.avgdl: float = 0.0
        self.df: Dict[str, int] = {}
        self.tf: List[Dict[str, int]] = []

        self._build()

    def _build(self) -> None:
        total_len = 0
        for ch in self.chunks:
            toks = tokenize(ch.text)
            freqs: Dict[str, int] = {}
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
        # IDF BM25 classique (avec smoothing)
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

    def topk(self, query: str, k: int = 8) -> List[Tuple[int, float]]:
        scored = []
        for i in range(len(self.chunks)):
            s = self.score(query, i)
            if s > 0:
                scored.append((i, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


# -----------------------
# Load extracted.json -> chunks
# -----------------------

def load_extracted(extracted_path: Path) -> dict:
    return json.loads(extracted_path.read_text(encoding="utf-8"))

def make_chunks(payload: dict, chunk_size: int, overlap: int) -> List[Chunk]:
    chunks: List[Chunk] = []
    docs = payload.get("documents", [])

    for d in docs:
        src = d.get("path", "")
        ext = d.get("ext", "")
        text = d.get("text", "") or ""

        # PDF: si pages disponibles, on chunk page par page (meilleure traçabilité)
        pages = d.get("pages", None)
        if ext == ".pdf" and isinstance(pages, list) and pages:
            for p in pages:
                page_num = p.get("page")
                page_text = p.get("text", "") or ""
                for j, ct in enumerate(chunk_text(page_text, chunk_size, overlap)):
                    cid = f"{Path(src).name}::p{page_num}::c{j}"
                    chunks.append(Chunk(chunk_id=cid, source_path=src, page=page_num, text=ct))
        else:
            for j, ct in enumerate(chunk_text(text, chunk_size, overlap)):
                cid = f"{Path(src).name}::c{j}"
                chunks.append(Chunk(chunk_id=cid, source_path=src, page=None, text=ct))

    return chunks


# -----------------------
# CLI
# -----------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extracted", required=True, help="JSON produit par extract_sources.py (ex: out/karaoui_extracted.json)")
    ap.add_argument("--query", default=None, help="Requête pour récupérer les passages pertinents")
    ap.add_argument("--topk", type=int, default=8, help="Nombre de chunks retournés")
    ap.add_argument("--chunk-size", type=int, default=1200, help="Taille des chunks (caractères)")
    ap.add_argument("--overlap", type=int, default=200, help="Chevauchement (caractères)")
    ap.add_argument("--out", default=None, help="(Optionnel) écrit un context.json avec les TOP-K résultats")
    ap.add_argument("--dump-chunks", default=None, help="(Optionnel) écrit tous les chunks en JSONL (debug)")
    args = ap.parse_args()

    extracted_path = Path(args.extracted).expanduser().resolve()
    if not extracted_path.exists():
        print(f"ERROR: fichier introuvable: {extracted_path}")
        return 2

    payload = load_extracted(extracted_path)
    chunks = make_chunks(payload, args.chunk_size, args.overlap)

    if args.dump_chunks:
        dump_path = Path(args.dump_chunks).expanduser().resolve()
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        with dump_path.open("w", encoding="utf-8") as f:
            for ch in chunks:
                f.write(json.dumps(asdict(ch), ensure_ascii=False) + "\n")
        print(f"OK: chunks dump -> {dump_path} ({len(chunks)} chunks)")

    print(f"OK: built {len(chunks)} chunks from extracted.json")

    if not args.query:
        print("Info: pas de --query, fin.")
        return 0

    index = BM25Index(chunks)
    top = index.topk(args.query, args.topk)

    results = []
    for rank, (i, score) in enumerate(top, start=1):
        ch = chunks[i]
        results.append({
            "rank": rank,
            "score": score,
            "chunk_id": ch.chunk_id,
            "source_path": ch.source_path,
            "page": ch.page,
            "text": ch.text,
        })

    # Affichage terminal lisible
    print("\n=== TOP MATCHES ===")
    for r in results:
        where = f"{Path(r['source_path']).name}"
        if r["page"] is not None:
            where += f" (page {r['page']})"
        print(f"\n[{r['rank']}] score={r['score']:.3f}  -> {where}")
        print(r["text"][:800] + ("..." if len(r["text"]) > 800 else ""))

    # Export JSON optionnel
    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_payload = {
            "query": args.query,
            "topk": args.topk,
            "generated_at": payload.get("generated_at"),
            "results": results
        }
        out_path.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nOK: context JSON -> {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
