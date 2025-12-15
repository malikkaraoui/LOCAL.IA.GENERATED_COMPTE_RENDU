"""Export DOCX -> PDF via LibreOffice."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def docx_to_pdf(docx_path: Path, output_dir: Path | None = None) -> Path:
    soffice_bin = shutil.which("soffice")
    if not soffice_bin:
        raise RuntimeError("LibreOffice (soffice) introuvable. Installe-le pour l'export PDF.")

    docx_path = Path(docx_path).expanduser().resolve()
    target_dir = Path(output_dir).expanduser().resolve() if output_dir else docx_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        soffice_bin,
        "--headless",
        "--nologo",
        "--nolockcheck",
        "--nodefault",
        "--nofirststartwizard",
        "--convert-to",
        "pdf:writer_pdf_Export",
        "--outdir",
        str(target_dir),
        str(docx_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Échec conversion PDF: {proc.stderr.strip()[:500]}")

    pdf_path = target_dir / f"{docx_path.stem}.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF non trouvé après conversion: {pdf_path}")
    return pdf_path
