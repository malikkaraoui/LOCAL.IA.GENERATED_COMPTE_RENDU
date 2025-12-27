"""Routes pour l'entraînement (analyse de patterns)."""

import json
from uuid import uuid4
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
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


# ============================================================================
# NOUVEAUX ENDPOINTS : Analyse et normalisation de clients
# ============================================================================

class ClientAnalyzeRequest(BaseModel):
    """Requête d'analyse d'un dossier client."""
    client_folder_path: str


class ClientNormalizeRequest(BaseModel):
    """Requête de normalisation d'un client."""
    client_folder_path: str
    batch_name: str
    sandbox_root: str = "./sandbox"
    create_normalized_alias: bool = True


class BatchNormalizeRequest(BaseModel):
    """Requête de normalisation batch."""
    dataset_root: str
    client_names: list[str]
    batch_name: str
    sandbox_root: str = "./sandbox"
    continue_on_error: bool = True


@router.post("/analyze-client")
async def analyze_client(req: ClientAnalyzeRequest):
    """
    Analyse un dossier client pour détecter GOLD et sources RAG.
    
    Args:
        req: Requête avec client_folder_path
        
    Returns:
        Résultat du scan (gold, rag_sources, warnings, pipeline_ready)
        
    Raises:
        HTTPException 400 si le dossier n'existe pas ou est invalide
    """
    try:
        # Import local pour éviter dépendances circulaires
        from src.rhpro.client_scanner import scan_client_folder
        
        client_path = Path(req.client_folder_path)
        
        if not client_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Dossier client introuvable : {req.client_folder_path}"
            )
        
        if not client_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Pas un dossier : {req.client_folder_path}"
            )
        
        # Scanner le dossier
        scan_result = scan_client_folder(str(client_path))
        
        return {
            "success": True,
            "scan_result": scan_result,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du scan : {str(e)}"
        )


@router.post("/normalize-client")
async def normalize_client(req: ClientNormalizeRequest):
    """
    Normalise un client scanné en sandbox.
    
    Args:
        req: Requête avec client_folder_path, batch_name, sandbox_root
        
    Returns:
        Résultat de la normalisation (paths créés, meta)
        
    Raises:
        HTTPException 400 si le client n'est pas pipeline-ready
    """
    try:
        from src.rhpro.client_scanner import scan_client_folder
        from src.rhpro.client_normalizer import normalize_client_to_sandbox
        
        # Scanner d'abord
        scan_result = scan_client_folder(req.client_folder_path)
        
        if not scan_result["pipeline_ready"]:
            raise HTTPException(
                status_code=400,
                detail=f"Client non pipeline-ready : {', '.join(scan_result['warnings'])}"
            )
        
        # Normaliser
        norm_result = normalize_client_to_sandbox(
            scan_result,
            batch_name=req.batch_name,
            sandbox_root=req.sandbox_root,
            create_normalized_alias=req.create_normalized_alias,
        )
        
        return {
            "success": True,
            "normalization_result": norm_result,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la normalisation : {str(e)}"
        )


@router.post("/normalize-batch")
async def normalize_batch(req: BatchNormalizeRequest):
    """
    Normalise plusieurs clients en batch.
    
    Args:
        req: Requête avec dataset_root, client_names, batch_name
        
    Returns:
        Résultat batch (success count, errors, stats)
    """
    try:
        from src.rhpro.client_normalizer import normalize_batch_to_sandbox
        
        batch_result = normalize_batch_to_sandbox(
            dataset_root=req.dataset_root,
            client_names=req.client_names,
            batch_name=req.batch_name,
            sandbox_root=req.sandbox_root,
            continue_on_error=req.continue_on_error,
        )
        
        return {
            "success": True,
            "batch_result": batch_result,
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du batch : {str(e)}"
        )

