"""Routes pour l'entraînement (analyse de patterns)."""

import json
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from redis import Redis

from backend.config import settings
from backend.api.models.training import (
    TrainingStartRequest,
    TrainingStartResponse,
    TrainingStatusResponse,
)

router = APIRouter(prefix="/training")

# Redis connection (même pattern que reports.py et rag_audio.py)
redis_conn = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
)


def _job_key(job_id: str) -> str:
    """Clé Redis pour un job d'entraînement."""
    return f"training:job:{job_id}"


@router.post("/start", response_model=TrainingStartResponse)
def training_start(req: TrainingStartRequest):
    """Démarre une analyse d'entraînement (stub pour l'instant).
    
    Crée un job dans Redis et retourne le job_id.
    Pour l'instant, marque directement le job comme 'done' (stub).
    Étape 3 : envoi au worker RQ pour vraie analyse.
    """
    job_id = uuid4().hex
    payload = req.model_dump()

    # ✅ Stockage minimal (pas de texte perso dans les logs)
    job = {
        "job_id": job_id,
        "status": "queued",
        "message": "queued",
        "batch_name": payload.get("batch_name"),
        "source_root": payload.get("source_root"),
        "sandbox_root": payload.get("sandbox_root"),
    }

    redis_conn.set(_job_key(job_id), json.dumps(job, ensure_ascii=False))

    # Stub: on marque direct "done" pour valider le wiring front/back
    # (étape 3 = envoi RQ worker + logs + vraie analyse)
    job["status"] = "done"
    job["message"] = "stub OK (backend branché)"
    redis_conn.set(_job_key(job_id), json.dumps(job, ensure_ascii=False))

    return TrainingStartResponse(job_id=job_id, status=job["status"])


@router.get("/{job_id}/status", response_model=TrainingStatusResponse)
def training_status(job_id: str):
    """Récupère le statut d'un job d'entraînement.
    
    Args:
        job_id: Identifiant unique du job
        
    Returns:
        TrainingStatusResponse avec le statut actuel
        
    Raises:
        HTTPException 404 si le job n'existe pas
    """
    raw = redis_conn.get(_job_key(job_id))
    if not raw:
        raise HTTPException(status_code=404, detail="Unknown training job_id")

    job = json.loads(raw)
    return TrainingStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        message=job.get("message"),
    )
