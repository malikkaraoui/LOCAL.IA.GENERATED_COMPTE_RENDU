"""Utilitaire pour gérer les statuts des jobs training dans Redis."""

import json
from datetime import datetime
from typing import Optional, Dict, Any
from redis import Redis

from backend.config import settings


def get_redis_client() -> Redis:
    """Retourne le client Redis configuré."""
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,
    )


def _training_key(job_id: str) -> str:
    """Clé Redis pour un job training."""
    return f"training:job:{job_id}"


def set_training_status(
    job_id: str,
    status: str,
    message: Optional[str] = None,
    progress: Optional[int] = None,
    artifact_path: Optional[str] = None,
) -> None:
    """Met à jour le statut d'un job training dans Redis.
    
    Args:
        job_id: Identifiant unique du job
        status: queued|running|done|error
        message: Message descriptif optionnel
        progress: Progression en % (0-100) optionnel
        artifact_path: Chemin relatif vers l'artefact généré (ruleset.json)
    """
    redis_client = get_redis_client()
    
    # Récupérer l'existant pour ne pas perdre de données
    existing = get_training_status(job_id)
    if existing:
        data = existing
    else:
        data = {"job_id": job_id}
    
    # Mettre à jour les champs fournis
    data["status"] = status
    data["updated_at"] = datetime.utcnow().isoformat()
    
    if message is not None:
        data["message"] = message
    if progress is not None:
        data["progress"] = progress
    if artifact_path is not None:
        data["artifact_path"] = artifact_path
    
    # Sauvegarder
    redis_client.set(
        _training_key(job_id),
        json.dumps(data, ensure_ascii=False),
        ex=86400  # TTL 24h
    )


def get_training_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Récupère le statut d'un job training depuis Redis.
    
    Args:
        job_id: Identifiant unique du job
        
    Returns:
        Dictionnaire avec les données du job, ou None si inexistant
    """
    redis_client = get_redis_client()
    raw = redis_client.get(_training_key(job_id))
    
    if not raw:
        return None
    
    return json.loads(raw)
