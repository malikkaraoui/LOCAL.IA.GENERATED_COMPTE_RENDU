"""Extraction des sources client (TXT/PDF/DOCX...)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import fitz  # PyMuPDF
from docx import Document

from .models import SourceDoc

LOG = logging.getLogger("core.extract")

SUPPORTED_DIRECT = {".pdf", ".docx", ".txt"}
SUPPORTED_SOFFICE = {".doc", ".rtf", ".odt", ".docm", ".dot", ".dotx", ".dotm"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def file_mtime_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except Exception:
        return ""


def extract_pdf(path: Path) -> Dict:
    pages_text = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            t = page.get_text("text") or ""
            t = normalize_text(t)
            pages_text.append({"page": i, "text": t})
    full_text = "\n\n".join(p["text"] for p in pages_text if p["text"]).strip()
    return {"text": full_text, "pages": pages_text}


def extract_docx(path: Path) -> Dict:
    doc = Document(path)
    parts: List[str] = []
    for p in doc.paragraphs:
        t = (p.text or "").strip()
        if t:
            parts.append(t)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    full_text = normalize_text("\n".join(parts))
    return {"text": full_text, "pages": None}


def extract_txt(path: Path) -> Dict:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    return {"text": normalize_text(text), "pages": None}


def soffice_available() -> Optional[str]:
    return shutil.which("soffice")


def extract_via_soffice(path: Path, soffice_bin: str) -> Dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        cmd = [
            soffice_bin,
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--nodefault",
            "--nofirststartwizard",
            "--convert-to",
            "txt:Text (encoded):UTF8",
            "--outdir",
            str(tmpdir_path),
            str(path),
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"soffice failed ({proc.returncode}): {proc.stderr.strip()[:500]}")
        out_txt = tmpdir_path / (path.stem + ".txt")
        if not out_txt.exists():
            candidates = list(tmpdir_path.glob("*.txt"))
            if not candidates:
                raise RuntimeError("soffice conversion produced no .txt output")
            out_txt = candidates[0]
        text = out_txt.read_text(encoding="utf-8", errors="ignore")
        return {"text": normalize_text(text), "pages": None}


def walk_files(root: Path) -> List[Path]:
    return sorted([p for p in root.rglob("*") if p.is_file()])


def extract_sources(
    root: Path,
    *,
    enable_soffice: bool = False,
    include_extensions: Optional[Sequence[str]] = None,
) -> Dict:
    root = Path(root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Dossier introuvable: {root}")

    allow_exts = set(include_extensions or [])
    files = walk_files(root)
    documents: List[SourceDoc] = []
    ok = errors = skipped = 0

    for path in files:
        ext = path.suffix.lower()
        allowed = not allow_exts or ext in allow_exts
        supported = ext in SUPPORTED_DIRECT or (enable_soffice and ext in SUPPORTED_SOFFICE)
        if not supported or not allowed:
            skipped += 1
            continue

        try:
            if ext == ".pdf":
                res = extract_pdf(path)
                text, pages, extractor = res["text"], res["pages"], "pymupdf"
            elif ext == ".docx":
                res = extract_docx(path)
                text, pages, extractor = res["text"], None, "python-docx"
            elif ext == ".txt":
                res = extract_txt(path)
                text, pages, extractor = res["text"], None, "txt"
            elif enable_soffice and ext in SUPPORTED_SOFFICE:
                soffice_bin = soffice_available()
                if not soffice_bin:
                    raise RuntimeError("LibreOffice (soffice) non trouvé")
                res = extract_via_soffice(path, soffice_bin)
                text, pages, extractor = res["text"], None, "soffice->txt"
            else:
                skipped += 1
                continue
            doc = SourceDoc(
                path=str(path),
                ext=ext,
                size_bytes=path.stat().st_size,
                mtime_iso=file_mtime_iso(path),
                extractor=extractor,
                text=text,
                text_sha256=sha256_text(text),
                pages=pages,
            )
            documents.append(doc)
            ok += 1
        except Exception as exc:
            documents.append(
                SourceDoc(
                    path=str(path),
                    ext=ext,
                    size_bytes=path.stat().st_size if path.exists() else 0,
                    mtime_iso=file_mtime_iso(path),
                    extractor="error",
                    text="",
                    text_sha256=sha256_text(""),
                    pages=None,
                    error=str(exc),
                )
            )
            errors += 1
            LOG.warning("FAIL %s -> %s", path.name, exc)

    payload = {
        "root": str(root),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "enable_soffice": enable_soffice,
        "counts": {
            "ok": ok,
            "errors": errors,
            "skipped": skipped,
            "total_seen": len(files),
        },
        "documents": [doc.__dict__ for doc in documents],
    }
    return payload


def write_payload(payload: Dict, out_path: Path) -> Path:
    out_path = Path(out_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
