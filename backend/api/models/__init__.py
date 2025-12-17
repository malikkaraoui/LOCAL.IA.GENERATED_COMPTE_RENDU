"""Modèles Pydantic pour l'API."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Statuts possibles d'un job."""
    PENDING = "pending"
    EXTRACTING = "extracting"
    GENERATING = "generating"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportCreateRequest(BaseModel):
    """Requête de création de rapport."""
    client_name: str = Field(..., description="Nom du client (dossier dans CLIENTS/)")
    source_file: Optional[str] = Field(None, description="Chemin vers le fichier source")
    extract_method: Optional[str] = Field("auto", description="Méthode d'extraction (auto, pypdf, docx, soffice)")
    template_name: Optional[str] = Field(None, description="Nom du template à utiliser")
    
    # Identité
    name: Optional[str] = Field(None, description="Prénom")
    surname: Optional[str] = Field(None, description="Nom de famille")
    civility: Optional[str] = Field("Monsieur", description="Civilité")
    avs_number: Optional[str] = Field(None, description="Numéro AVS")
    
    # Localisation
    location_city: Optional[str] = Field("Genève", description="Ville")
    location_date: Optional[str] = Field(None, description="Date formatée")
    auto_location_date: Optional[bool] = Field(True, description="Date automatique")
    
    # Chemins
    clients_root: Optional[str] = Field("./CLIENTS", description="Racine des dossiers clients")
    template_path: Optional[str] = Field(None, description="Chemin du template")
    output_dir: Optional[str] = Field("./out", description="Dossier de sortie")
    
    # LLM
    llm_host: Optional[str] = Field("http://localhost:11434", description="Serveur Ollama")
    llm_model: Optional[str] = Field("qwen2.5:latest", description="Modèle Ollama")
    temperature: Optional[float] = Field(0.2, ge=0, le=1, description="Température LLM")
    topk: Optional[int] = Field(10, description="Top-K passages")
    top_p: Optional[float] = Field(0.9, description="Top-p")
    
    # Filtres
    include_filters: Optional[str] = Field(None, description="Chemins à inclure (CSV)")
    exclude_filters: Optional[str] = Field(None, description="Chemins à exclure (CSV)")
    
    # Options
    force_reextract: Optional[bool] = Field(False, description="Forcer extraction")
    enable_soffice: Optional[bool] = Field(False, description="Activer LibreOffice")
    export_pdf: Optional[bool] = Field(False, description="Exporter en PDF")
    
    class Config:
        json_schema_extra = {
            "example": {
                "client_name": "KARAOUI Malik",
                "name": "Malik",
                "surname": "KARAOUI",
                "temperature": 0.2
            }
        }


class ReportResponse(BaseModel):
    """Réponse lors de la création d'un rapport."""
    job_id: str = Field(..., description="ID unique du job")
    status: JobStatus = Field(..., description="Statut du job")
    created_at: datetime = Field(..., description="Date de création")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "abc123def456",
                "status": "pending",
                "created_at": "2025-12-16T13:30:00"
            }
        }


class ReportStatusResponse(BaseModel):
    """Réponse de statut d'un rapport."""
    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: Optional[float | dict] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "abc123",
                "status": "generating",
                "created_at": "2025-12-16T13:30:00",
                "started_at": "2025-12-16T13:30:05",
                "progress": {
                    "current_field": "PROFESSION",
                    "completed_fields": 5,
                    "total_fields": 31
                }
            }
        }


class LogMessage(BaseModel):
    """Message de log streaming."""
    timestamp: datetime
    level: str
    message: str
    extra: Optional[dict] = None
