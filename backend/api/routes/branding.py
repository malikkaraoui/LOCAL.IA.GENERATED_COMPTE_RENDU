"""Routes Branding (DOCX header/footer) pour l'application.

Expose un endpoint simple pour appliquer un branding (champs + logos) sur un
template DOCX côté serveur, puis renvoyer le DOCX résultant au navigateur.

Contraintes:
- Ne jamais modifier le template original.
- Validation des fichiers image (type/poids).
- Nettoyage des fichiers temporaires après réponse.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image  # type: ignore

from backend.config import settings
from core.docx_branding import apply_branding_to_docx

logger = logging.getLogger(__name__)

router = APIRouter()

# Sécurité basique: éviter les uploads énormes.
MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MiB

# Types acceptés (le script sait gérer plusieurs formats; PNG est le plus courant).
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/tiff"}

DEFAULT_TEMPLATE_NAME = "TEMPLATE_SIMPLE_BASE.docx"


def _resolve_template_path(template_name: Optional[str], template_path: Optional[str]) -> Path:
    """Résout le template DOCX à brander.

    Priorité:
    1) template_name (uploaded_templates/ ou CLIENTS/templates/)
    2) template_path (mode avancé/dev local côté serveur)
    3) uploaded_templates/TEMPLATE_SIMPLE_BASE.docx
    4) settings.TEMPLATE_PATH
    """

    def _ensure_docx(p: Path, label: str) -> Path:
        if not p.exists() or not p.is_file():
            raise HTTPException(status_code=404, detail=f"Template introuvable ({label}): {p}")
        if p.suffix.lower() != ".docx":
            raise HTTPException(status_code=400, detail=f"Template invalide ({label}): attendu .docx")
        return p

    # 1) template_name
    if template_name:
        safe_name = Path(str(template_name).strip()).name
        cand1 = settings.TEMPLATES_DIR / safe_name
        if cand1.exists():
            return _ensure_docx(cand1, f"template_name={safe_name}")
        cand2 = settings.CLIENTS_DIR / "templates" / safe_name
        if cand2.exists():
            return _ensure_docx(cand2, f"template_name={safe_name}")
        raise HTTPException(
            status_code=404,
            detail=(
                f"Template '{safe_name}' introuvable. "
                f"Attendu dans {settings.TEMPLATES_DIR} ou {settings.CLIENTS_DIR / 'templates'}"
            ),
        )

    # 2) template_path (mode avancé)
    if template_path:
        p = Path(str(template_path)).expanduser()
        return _ensure_docx(p, f"template_path={p}")

    # 3) default base template
    base = settings.TEMPLATES_DIR / DEFAULT_TEMPLATE_NAME
    if base.exists():
        return _ensure_docx(base, f"default={DEFAULT_TEMPLATE_NAME}")

    # 3bis) fallback: premier template disponible dans uploaded_templates
    try:
        if settings.TEMPLATES_DIR.exists():
            docxs = sorted([p for p in settings.TEMPLATES_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".docx"])
            if docxs:
                return _ensure_docx(docxs[0], "uploaded_templates:first")
    except Exception:
        # On ne veut pas masquer les erreurs plus loin; fallback silencieux.
        pass

    # 4) fallback global
    if getattr(settings, "TEMPLATE_PATH", None):
        return _ensure_docx(Path(settings.TEMPLATE_PATH), "settings.TEMPLATE_PATH")

    raise HTTPException(
        status_code=404,
        detail=(
            f"Aucun template disponible. "
            f"Dépose un .docx dans {settings.TEMPLATES_DIR} (ex: via /api/templates/upload)."
        ),
    )


def _safe_filename(name: str, default: str = "branding") -> str:
    name = (name or "").strip()
    if not name:
        return default
    # Remplacer tout ce qui n'est pas alphanum/_/- par '_'
    name = re.sub(r"[^a-zA-Z0-9_-]+", "_", name)
    return name.strip("_") or default


async def _save_validated_image(file: UploadFile, dest: Path) -> None:
    """Valide + écrit un UploadFile image.

    Validation:
    - extension autorisée
    - mime-type si présent
    - taille max
    - ouverture PIL (vérifie le format)
    """

    filename = (file.filename or "").strip()
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Format logo non supporté: {ext or '(sans extension)'} (attendu: {', '.join(sorted(ALLOWED_IMAGE_EXTS))})",
        )

    if file.content_type and file.content_type.lower() not in ALLOWED_IMAGE_MIMES:
        # Certains navigateurs peuvent envoyer image/jpg; on tolère via extension.
        logger.warning("branding: content_type inattendu=%s pour %s", file.content_type, filename)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Fichier logo vide")
    if len(data) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=413, detail=f"Logo trop volumineux (max {MAX_LOGO_BYTES} bytes)")

    # Validation image avec PIL
    try:
        from io import BytesIO

        with Image.open(BytesIO(data)) as im:
            im.verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Logo invalide/corrompu: {exc}")

    dest.write_bytes(data)


@router.post("/branding/apply")
async def apply_branding(
    background_tasks: BackgroundTasks,
    template_name: str = Form(""),
    template_path: str = Form(""),
    titre_document: str = Form(""),
    societe: str = Form(""),
    rue: str = Form(""),
    numero: str = Form(""),
    cp: str = Form(""),
    ville: str = Form(""),
    tel: str = Form(""),
    email: str = Form(""),
    logo_header: Optional[UploadFile] = File(None),
    logo_footer: Optional[UploadFile] = File(None),
):
    """Applique le branding au template DOCX de base et renvoie le DOCX en téléchargement."""

    resolved_template = _resolve_template_path(
        template_name=(template_name or "").strip() or None,
        template_path=(template_path or "").strip() or None,
    )

    workdir = Path(tempfile.mkdtemp(prefix="scriptia_branding_"))
    # Nettoyage après réponse
    background_tasks.add_task(shutil.rmtree, workdir, ignore_errors=True)

    # Préparer les chemins temporaires
    header_logo_path: Optional[Path] = None
    footer_logo_path: Optional[Path] = None

    if logo_header is not None:
        header_logo_path = workdir / f"logo_header{Path(logo_header.filename or 'logo.png').suffix.lower()}"
        await _save_validated_image(logo_header, header_logo_path)

    if logo_footer is not None:
        footer_logo_path = workdir / f"logo_footer{Path(logo_footer.filename or 'logo.png').suffix.lower()}"
        await _save_validated_image(logo_footer, footer_logo_path)

    fields = {
        "TITRE_DOCUMENT": titre_document,
        "SOCIETE": societe,
        "RUE": rue,
        "NUMERO": numero,
        "CP": cp,
        "VILLE": ville,
        "TEL": tel,
        "EMAIL": email,
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_hint = _safe_filename(societe or titre_document or "branding")
    out_name = f"{name_hint}_branded_{ts}.docx"
    out_path = workdir / out_name

    logger.info(
        "branding.apply: template=%s societe=%s titre=%s header_logo=%s footer_logo=%s",
        resolved_template.name,
        societe,
        titre_document,
        bool(header_logo_path),
        bool(footer_logo_path),
    )

    try:
        apply_branding_to_docx(
            template_docx=resolved_template,
            output_docx=out_path,
            fields=fields,
            logo_header=header_logo_path,
            logo_footer=footer_logo_path,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("branding.apply failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Échec branding DOCX: {exc}")

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise HTTPException(status_code=500, detail="DOCX généré vide")

    return FileResponse(
        path=str(out_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=out_name,
    )
