"""Routes pour l'entraînement (analyse de patterns)."""

import json
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from redis import Redis
from rq import Queue

from backend.config import settings
from backend.api.models.training import (
    TrainingStartRequest,
    TrainingStartResponse,
    TrainingStatusResponse,
)
from backend.api.services.training_status import (
    set_training_status,
    get_training_status,
)
from backend.workers.training_worker import training_analysis_job

router = APIRouter(prefix="/training")

# Redis connection (même pattern que reports.py)
redis_conn = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=False,  # Must match worker configuration
)

# Queue RQ pour les jobs training
training_queue = Queue("training", connection=redis_conn)


@router.post("/start", response_model=TrainingStartResponse)
def training_start(req: TrainingStartRequest):
    """Démarre une analyse d'entraînement en arrière-plan.
    
    Crée un job dans Redis, l'enqueue dans RQ, et retourne immédiatement.
    Le worker RQ exécutera l'analyse de manière asynchrone.
    """
    job_id = uuid4().hex
    payload = req.model_dump()

    # Initialiser le statut en "queued"
    set_training_status(
        job_id,
        status="queued",
        message="Job en file d'attente",
        progress=0
    )

    # Enqueue le job dans RQ (pattern recommandé : job_id via get_current_job)
    rq_job = training_queue.enqueue(
        training_analysis_job,
        payload,  # Passer payload comme argument positionnel
        job_id=job_id,  # job_id pour RQ (récupérable via get_current_job())
        job_timeout='30m',
        result_ttl=86400,
        failure_ttl=86400,
    )

    return TrainingStartResponse(job_id=job_id, status="queued")


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
    job = get_training_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Unknown training job_id")

    return TrainingStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        message=job.get("message"),
        progress=job.get("progress"),
        artifact_path=job.get("artifact_path"),
    )
