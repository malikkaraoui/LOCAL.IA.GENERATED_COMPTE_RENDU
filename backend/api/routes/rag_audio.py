"""Routes RAG audio: upload + job RQ pour STT (faster-whisper) puis ingestion.

Chemin exposé via backend.main avec API_PREFIX:
- POST /api/rag/audio/ingest

Contraintes:
- 100% local (pas de cloud)
- Français forcé (côté STT)
- Audios courts (< AUDIO_MAX_SECONDS)
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Query, Request
from redis import Redis
from rq import Queue

from backend.config import settings
from script_ai.workers.jobs.audio_rag import transcribe_and_ingest_audio_job

logger = logging.getLogger(__name__)

router = APIRouter()

# Redis connection and queue
redis_conn = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=False,
)

# Queue dédiée pour ne pas mélanger avec les rapports (mais le worker peut écouter plusieurs queues).
queue = Queue("rag", connection=redis_conn)

ALLOWED_AUDIO_EXTS = {".m4a", ".mp3", ".wav"}


def _audio_deps_status() -> Dict[str, Any]:
    """Retourne l'état des dépendances nécessaires à la transcription audio."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")

    faster_whisper_ok = True
    faster_whisper_error: Optional[str] = None
    try:
        import faster_whisper  # type: ignore  # noqa: F401
    except Exception as exc:
        faster_whisper_ok = False
        faster_whisper_error = f"{type(exc).__name__}: {exc}"

    return {
        "ffmpeg": {"ok": bool(ffmpeg), "path": ffmpeg},
        "ffprobe": {"ok": bool(ffprobe), "path": ffprobe},
        "faster_whisper": {"ok": faster_whisper_ok, "error": faster_whisper_error},
    }


def _ensure_audio_deps_or_412() -> None:
    deps = _audio_deps_status()

    missing: list[str] = []
    if not deps["ffmpeg"]["ok"] or not deps["ffprobe"]["ok"]:
        missing.append("ffmpeg/ffprobe")
    if not deps["faster_whisper"]["ok"]:
        missing.append("faster-whisper")

    if not missing:
        return

    # 412 = prérequis manquant (plus parlant qu'un 500 après exécution du job)
    hint_parts: list[str] = []
    if "ffmpeg/ffprobe" in missing:
        hint_parts.append("macOS: `brew install ffmpeg` (inclut ffprobe)")
    if "faster-whisper" in missing:
        hint_parts.append("Python: installez les deps via `pip install -r requirements.txt` (ou `backend/requirements.txt`)")

    detail = {
        "message": f"Dépendances audio manquantes: {', '.join(missing)}",
        "hints": hint_parts,
        "deps": deps,
    }
    raise HTTPException(status_code=412, detail=detail)


def _ensure_localhost(request: Request) -> None:
    host = getattr(getattr(request, "client", None), "host", None)
    if host not in {"127.0.0.1", "::1"}:
        raise HTTPException(status_code=403, detail="RAG audio endpoints (local scan): localhost only")


def _safe_filename(name: str) -> str:
    # Évite les chemins fournis par le navigateur.
    return Path(name).name


def _parse_metadata(metadata_json: str) -> Dict[str, Any]:
    text = (metadata_json or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        # On tolère et on ignore silencieusement pour ne pas bloquer l'upload.
        return {}


@router.post("/rag/audio/ingest")
async def ingest_audio(
    source_id: str = Form(..., description="Identifiant de la source (souvent: nom du client)"),
    cleanup: bool = Form(True, description="Supprimer le fichier uploadé après ingestion"),
    metadata_json: str = Form("", description="JSON optionnel (dict) de métadonnées additionnelles"),
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """Upload un audio et enfile un job RQ (STT + ingestion)."""

    _ensure_audio_deps_or_412()

    source_id = (source_id or "").strip()
    if not source_id:
        raise HTTPException(status_code=400, detail="source_id manquant")

    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant")

    safe_name = _safe_filename(filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Format audio non supporté: {ext or '(sans extension)'} (attendu: {', '.join(sorted(ALLOWED_AUDIO_EXTS))})",
        )

    upload_dir = Path(settings.AUDIO_UPLOAD_DIR).expanduser().resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = upload_dir / f"{Path(safe_name).stem}_{ts}{ext}"

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Fichier audio vide")
        dest.write_bytes(content)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Échec sauvegarde audio: {exc}")

    extra_metadata = _parse_metadata(metadata_json)

    job = queue.enqueue(
        transcribe_and_ingest_audio_job,
        file_path=str(dest),
        source_id=source_id,
        extra_metadata=extra_metadata,
        cleanup=cleanup,
        job_timeout=max(int(getattr(settings, "AUDIO_MAX_SECONDS", 300)) * 4, 600),
        result_ttl=86400,
        failure_ttl=86400,
    )

    logger.info(
        "audio ingest queued",
        extra={"job_id": job.id, "file": str(dest), "source_id": source_id, "queue": "rag"},
    )

    return {"job_id": job.id, "status": "queued"}


@router.get("/rag/audio/status")
async def rag_audio_status(
    request: Request,
    source_id: str = Query(..., description="Identifiant de la source (souvent: nom du client)"),
) -> Dict[str, Any]:
    """Retourne le statut d'ingestion audio pour une source.

    Donne le nombre de transcriptions présentes dans:
    - CLIENTS/<source_id>/sources/ingested_audio
    """
    _ensure_localhost(request)

    source_id = (source_id or "").strip()
    if not source_id:
        raise HTTPException(status_code=400, detail="source_id manquant")

    client_dir = Path(settings.CLIENTS_DIR).expanduser().resolve() / source_id
    ingested_dir = client_dir / "sources" / "ingested_audio"

    txt = len(list(ingested_dir.glob("*.txt"))) if ingested_dir.exists() else 0
    js = len(list(ingested_dir.glob("*.json"))) if ingested_dir.exists() else 0

    return {
        "source_id": source_id,
        "client_dir": str(client_dir),
        "ingested_dir": str(ingested_dir),
        "audio_ingested": {"txt": txt, "json": js},
        "deps": _audio_deps_status(),
    }


@router.post("/rag/audio/ingest-local")
async def ingest_audio_local(
    request: Request,
    source_id: str = Query(..., description="Identifiant de la source (souvent: nom du client)"),
    max_files: int = Query(25, ge=1, le=200, description="Limite de fichiers audio à ingérer"),
    skip_already_ingested: bool = Query(True, description="Ignorer les audios déjà présents dans les manifests ingested_audio/*.json"),
) -> Dict[str, Any]:
    """Enfile des jobs RQ pour ingérer les audios déjà présents sur disque (sans upload).

    ⚠️ Endpoint localhost-only.
    - Ne supprime pas les fichiers audio d'origine (cleanup=False).
    - Écrit les transcriptions dans CLIENTS/<source_id>/sources/ingested_audio/.
    """
    _ensure_localhost(request)

    _ensure_audio_deps_or_412()

    source_id = (source_id or "").strip()
    if not source_id:
        raise HTTPException(status_code=400, detail="source_id manquant")

    client_dir = Path(settings.CLIENTS_DIR).expanduser().resolve() / source_id
    if not client_dir.exists() or not client_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Client introuvable: {client_dir}")

    # On scanne tout le dossier client : dans la pratique, les audios peuvent être rangés
    # dans des sous-dossiers (devis, stages, etc.) en dehors de `sources/`.
    # On garde `max_files` pour limiter le coût du rglob.
    scan_root = client_dir

    # Récupérer les audio_path déjà ingérés (via manifests JSON)
    seen_audio_paths: set[str] = set()
    if skip_already_ingested:
        ingested_dir = client_dir / "sources" / "ingested_audio"
        if ingested_dir.exists() and ingested_dir.is_dir():
            for mf in ingested_dir.glob("*.json"):
                try:
                    payload = json.loads(mf.read_text(encoding="utf-8"))
                    ap = payload.get("audio_path")
                    if isinstance(ap, str) and ap:
                        seen_audio_paths.add(str(Path(ap).expanduser().resolve()))
                except Exception:
                    # non bloquant
                    continue

    audio_files: list[Path] = []
    for ext in sorted(ALLOWED_AUDIO_EXTS):
        audio_files.extend(scan_root.rglob(f"*{ext}"))

    # Exclure les fichiers dans ingested_audio (et normaliser)
    filtered: list[Path] = []
    for p in audio_files:
        try:
            rp = p.expanduser().resolve()
        except Exception:
            continue
        if "sources/ingested_audio" in str(rp).replace("\\", "/"):
            continue
        if skip_already_ingested and str(rp) in seen_audio_paths:
            continue
        filtered.append(rp)

    # Limiter
    filtered = filtered[:max_files]

    jobs: list[Dict[str, Any]] = []
    for p in filtered:
        job = queue.enqueue(
            transcribe_and_ingest_audio_job,
            file_path=str(p),
            source_id=source_id,
            extra_metadata={"origin": "local_scan", "relative_path": str(p.relative_to(client_dir)) if str(p).startswith(str(client_dir)) else str(p)},
            cleanup=False,
            job_timeout=max(int(getattr(settings, "AUDIO_MAX_SECONDS", 300)) * 4, 600),
            result_ttl=86400,
            failure_ttl=86400,
        )
        jobs.append({"job_id": job.id, "file": str(p)})

    return {
        "source_id": source_id,
        "scan_root": str(scan_root),
        "queued": len(jobs),
        "max_files": max_files,
        "skip_already_ingested": skip_already_ingested,
        "jobs": jobs,
    }
