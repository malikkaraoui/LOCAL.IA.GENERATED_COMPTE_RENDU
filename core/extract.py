"""Extraction des sources client (TXT/PDF/DOCX...)."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from docx import Document

from .errors import Result, ExtractionError
from .logger import get_logger
from .models import SourceDoc

LOG = get_logger("core.extract")

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


def extract_pdf(path: Path) -> Result[dict]:
    """Extrait le texte d'un PDF avec PyMuPDF.
    
    Args:
        path: Chemin vers le fichier PDF
        
    Returns:
        Result[dict]: Succès avec {"text", "pages"} ou échec avec ExtractionError
    """
    try:
        LOG.info("Extraction PDF: %s", path.name)
        pages_text = []
        with fitz.open(path) as doc:
            for i, page in enumerate(doc, start=1):
                t = page.get_text("text") or ""
                t = normalize_text(t)
                pages_text.append({"page": i, "text": t})
        full_text = "\n\n".join(p["text"] for p in pages_text if p["text"]).strip()
        LOG.debug("PDF extrait: %d pages, %d caractères", len(pages_text), len(full_text))
        return Result.ok({"text": full_text, "pages": pages_text})
    except Exception as exc:
        error = ExtractionError(f"Échec extraction PDF {path.name}: {exc}")
        LOG.error("Erreur extraction PDF %s: %s", path.name, exc)
        return Result.fail(error)


def extract_docx(path: Path) -> Result[dict]:
    """Extrait le texte d'un DOCX avec python-docx.
    
    Args:
        path: Chemin vers le fichier DOCX
        
    Returns:
        Result[dict]: Succès avec {"text", "pages": None} ou échec avec ExtractionError
    """
    try:
        LOG.info("Extraction DOCX: %s", path.name)
        doc = Document(path)
        parts: list[str] = []
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
        LOG.debug("DOCX extrait: %d paragraphes, %d caractères", len(parts), len(full_text))
        return Result.ok({"text": full_text, "pages": None})
    except Exception as exc:
        error = ExtractionError(f"Échec extraction DOCX {path.name}: {exc}")
        LOG.error("Erreur extraction DOCX %s: %s", path.name, exc)
        return Result.fail(error)


def extract_txt(path: Path) -> Result[dict]:
    """Extrait le texte d'un fichier TXT avec détection d'encodage.
    
    Args:
        path: Chemin vers le fichier TXT
        
    Returns:
        Result[dict]: Succès avec {"text", "pages": None} ou échec avec ExtractionError
    """
    try:
        LOG.info("Extraction TXT: %s", path.name)
        try:
            text = path.read_text(encoding="utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")
            encoding = "latin-1"
        normalized = normalize_text(text)
        LOG.debug("TXT extrait (%s): %d caractères", encoding, len(normalized))
        return Result.ok({"text": normalized, "pages": None})
    except Exception as exc:
        error = ExtractionError(f"Échec extraction TXT {path.name}: {exc}")
        LOG.error("Erreur extraction TXT %s: %s", path.name, exc)
        return Result.fail(error)


def soffice_available() -> Optional[str]:
    return shutil.which("soffice")


def extract_via_soffice(path: Path, soffice_bin: str) -> Result[dict]:
    """Extrait le texte via LibreOffice en convertissant en TXT.
    
    Args:
        path: Chemin vers le fichier à convertir
        soffice_bin: Chemin vers l'exécutable soffice
        
    Returns:
        Result[dict]: Succès avec {"text", "pages": None} ou échec avec ExtractionError
    """
    try:
        LOG.info("Extraction soffice: %s", path.name)
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
                error_msg = f"soffice failed ({proc.returncode}): {proc.stderr.strip()[:500]}"
                LOG.error("Échec soffice %s: %s", path.name, error_msg)
                return Result.fail(ExtractionError(error_msg))
            out_txt = tmpdir_path / (path.stem + ".txt")
            if not out_txt.exists():
                candidates = list(tmpdir_path.glob("*.txt"))
                if not candidates:
                    error_msg = "soffice conversion produced no .txt output"
                    LOG.error("Aucun output soffice pour %s", path.name)
                    return Result.fail(ExtractionError(error_msg))
                out_txt = candidates[0]
            text = out_txt.read_text(encoding="utf-8", errors="ignore")
            normalized = normalize_text(text)
            LOG.debug("Soffice extrait: %d caractères", len(normalized))
            return Result.ok({"text": normalized, "pages": None})
    except Exception as exc:
        error = ExtractionError(f"Échec extraction soffice {path.name}: {exc}")
        LOG.error("Erreur soffice %s: %s", path.name, exc)
        return Result.fail(error)


def walk_files(root: Path) -> list[Path]:
    """Liste récursivement tous les fichiers, en excluant les fichiers/dossiers cachés."""
    def _is_hidden(path: Path) -> bool:
        """Retourne True si le fichier ou un de ses parents est caché."""
        for part in path.parts:
            if part.startswith('.'):
                return True
        return False

    return sorted([p for p in root.rglob("*") if p.is_file() and not _is_hidden(p.relative_to(root))])


def extract_sources(
    root: Path,
    *,
    enable_soffice: bool = False,
    include_extensions: Optional[Sequence[str]] = None,
) -> dict:
    root = Path(root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Dossier introuvable: {root}")

    allow_exts = set(include_extensions or [])
    files = walk_files(root)
    documents: list[SourceDoc] = []
    ok = errors = skipped = 0

    for path in files:
        ext = path.suffix.lower()
        allowed = not allow_exts or ext in allow_exts
        supported = ext in SUPPORTED_DIRECT or (enable_soffice and ext in SUPPORTED_SOFFICE)
        if not supported or not allowed:
            skipped += 1
            continue

        result: Optional[Result[dict]] = None
        extractor = "unknown"
        
        try:
            if ext == ".pdf":
                result = extract_pdf(path)
                extractor = "pymupdf"
            elif ext == ".docx":
                result = extract_docx(path)
                extractor = "python-docx"
            elif ext == ".txt":
                result = extract_txt(path)
                extractor = "txt"
            elif enable_soffice and ext in SUPPORTED_SOFFICE:
                soffice_bin = soffice_available()
                if not soffice_bin:
                    result = Result.fail(ExtractionError("LibreOffice (soffice) non trouvé"))
                else:
                    result = extract_via_soffice(path, soffice_bin)
                extractor = "soffice->txt"
            else:
                skipped += 1
                continue
                
            if result and result.success:
                data = result.value
                doc = SourceDoc(
                    path=str(path),
                    ext=ext,
                    size_bytes=path.stat().st_size,
                    mtime_iso=file_mtime_iso(path),
                    extractor=extractor,
                    text=data["text"],
                    text_sha256=sha256_text(data["text"]),
                    pages=data.get("pages"),
                )
                documents.append(doc)
                ok += 1
            elif result:
                # Échec explicite avec Result.fail
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
                        error=str(result.error),
                    )
                )
                errors += 1
        except Exception as exc:
            # Gestion des exceptions imprévues
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


def write_payload(payload: dict, out_path: Path) -> Path:
    out_path = Path(out_path).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
