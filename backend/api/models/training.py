"""Modèles Pydantic pour l'entraînement."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class TrainingFolders(BaseModel):
    """Configuration des dossiers à analyser."""
    personal: str
    tests: str
    stages: str
    ai: str
    final: str


class TrainingStartRequest(BaseModel):
    """Requête pour démarrer une analyse d'entraînement."""
    batch_name: str
    source_root: str
    sandbox_root: str
    copy_mode: bool = True
    allowed_ext: List[str] = Field(default_factory=list)
    folders: TrainingFolders
    preprompt_system: str = ""


class TrainingStartResponse(BaseModel):
    """Réponse après création d'un job d'entraînement."""
    job_id: str
    status: str


class TrainingStatusResponse(BaseModel):
    """Statut d'un job d'entraînement."""
    job_id: str
    status: str
    message: Optional[str] = None
