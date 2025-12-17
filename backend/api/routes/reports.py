"""Routes pour la gestion des rapports avec Redis Queue.

Inclut aussi la gestion des templates (liste + upload) pour permettre au
frontend d'offrir un vrai bouton "Parcourir…" comme l'ancienne UI Streamlit.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Response, UploadFile, File
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from redis import Redis
from rq import Queue
from rq.job import Job

from backend.api.models import (
    ReportCreateRequest,
    ReportResponse,
    ReportStatusResponse,
    JobStatus,
)
from backend.config import settings
from backend.workers.report_worker import process_report_job

router = APIRouter()

# Redis connection and queue
redis_conn = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=False  # Must match worker configuration
)
queue = Queue("reports", connection=redis_conn)


@router.get("/templates")
async def list_templates():
    """Liste les templates DOCX disponibles côté serveur.

    Sources :
    - `uploaded_templates/` (settings.TEMPLATES_DIR)
    - `CLIENTS/templates/` (si présent)
    """
    templates: set[str] = set()

    # 1) uploaded_templates
    tpl_dir = settings.TEMPLATES_DIR
    if tpl_dir.exists():
        for p in tpl_dir.iterdir():
            if p.is_file() and p.suffix.lower() == ".docx":
                templates.add(p.name)

    # 2) CLIENTS/templates
    client_tpl_dir = settings.CLIENTS_DIR / "templates"
    if client_tpl_dir.exists():
        for p in client_tpl_dir.iterdir():
            if p.is_file() and p.suffix.lower() == ".docx":
                templates.add(p.name)

    return {"templates": sorted(templates)}


@router.post("/templates/upload")
async def upload_template(file: UploadFile = File(...)):
    """Upload d'un template DOCX depuis le navigateur.

    Le browser ne peut pas fournir un chemin local utilisable par le backend;
    on sauvegarde donc le fichier sur le serveur puis on renvoie son nom.
    """
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant")

    safe_name = Path(filename).name
    if Path(safe_name).suffix.lower() != ".docx":
        raise HTTPException(status_code=400, detail="Seuls les fichiers .docx sont acceptés")

    settings.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    dest = settings.TEMPLATES_DIR / safe_name
    if dest.exists():
        # Éviter d'écraser: on suffixe avec un timestamp
        from datetime import datetime

        stem = dest.stem
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = settings.TEMPLATES_DIR / f"{stem}_{ts}.docx"

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Fichier vide")
        dest.write_bytes(content)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Échec upload template: {exc}")

    return {"template_name": dest.name}


def _parse_csv_filters(value: object) -> list[str]:
    """Convertit les filtres en liste de chaînes.

    Le frontend envoie des champs texte (CSV) ; certains anciens appels peuvent
    envoyer déjà une liste. On normalise ici pour éviter des comportements
    bizarres (ex: itération caractère par caractère).
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    # Support CSV + retours à la ligne
    parts = []
    for chunk in text.replace("\n", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts


def _resolve_template_path(request: ReportCreateRequest) -> Path:
    """Résout le template à utiliser à partir de la requête + settings."""
    if request.template_path:
        p = Path(request.template_path)
        return p if p.is_absolute() else (settings.CLIENTS_DIR.parent / p)

    if request.template_name:
        # 1) uploaded_templates/<name>
        cand1 = settings.TEMPLATES_DIR / request.template_name
        if cand1.exists():
            return cand1
        # 2) CLIENTS/templates/<name>
        cand2 = settings.CLIENTS_DIR / "templates" / request.template_name
        if cand2.exists():
            return cand2

    return settings.TEMPLATE_PATH


def _resolve_clients_dir(request: ReportCreateRequest) -> Path:
    if request.clients_root:
        p = Path(request.clients_root)
        return p if p.is_absolute() else (settings.CLIENTS_DIR.parent / p)
    return settings.CLIENTS_DIR


@router.get("/clients")
async def list_clients():
    """
    Liste tous les clients disponibles.
    
    Retourne les noms de dossiers dans CLIENTS/ (sauf templates).
    """
    clients_dir = settings.CLIENTS_DIR
    if not clients_dir.exists():
        return {"clients": []}
    
    clients = []
    for item in clients_dir.iterdir():
        if item.is_dir() and item.name not in ["templates", "__pycache__"]:
            clients.append(item.name)
    
    return {"clients": sorted(clients)}


@router.post("/reports", response_model=ReportResponse)
async def create_report(request: ReportCreateRequest):
    """
    Créer un nouveau rapport (job asynchrone).
    
    Le rapport sera généré en arrière-plan par un RQ worker. 
    Utilisez GET /reports/{job_id} pour suivre la progression.
    """
    # Vérifier que le client existe
    clients_dir = _resolve_clients_dir(request)
    client_dir = clients_dir / request.client_name
    if not client_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Client '{request.client_name}' introuvable dans {clients_dir}"
        )
    
    # Vérifier si le fichier source existe (si fourni)
    source_file = None
    if request.source_file:
        source_path = Path(request.source_file)
        if not source_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Fichier source '{request.source_file}' introuvable"
            )
        source_file = str(source_path)  # Convert to string for Redis serialization
    
    # Enqueue job dans Redis Queue with all parameters
    template_path = _resolve_template_path(request)
    if not template_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Template introuvable: {template_path}"
        )

    include_filters = _parse_csv_filters(request.include_filters)
    exclude_filters = _parse_csv_filters(request.exclude_filters)

    job = queue.enqueue(
        process_report_job,
        client_name=request.client_name,
        clients_root=str(clients_dir),
        source_file=source_file,
        extract_method=request.extract_method or "auto",
        template_path=str(template_path),
        output_dir=request.output_dir,
        # Identity
        name=request.name or "",
        surname=request.surname or "",
        civility=request.civility or "Monsieur",
        avs_number=request.avs_number or "",
        # Location/Date
        location_city=request.location_city or "",
        location_date=request.location_date or "",
        auto_location_date=request.auto_location_date if request.auto_location_date is not None else True,
        # LLM
        llm_host=request.llm_host or settings.OLLAMA_HOST,
        llm_model=request.llm_model or settings.OLLAMA_MODEL,
        temperature=request.temperature if request.temperature is not None else 0.2,
        topk=request.topk if request.topk is not None else 10,
        top_p=request.top_p if request.top_p is not None else 0.9,
        # Filters
        include_filters=include_filters,
        exclude_filters=exclude_filters,
        # Options
        force_reextract=request.force_reextract or False,
        enable_soffice=request.enable_soffice or False,
        export_pdf=request.export_pdf or False,
        # RQ options
        job_timeout=settings.OLLAMA_TIMEOUT * 3,  # Triple timeout for full pipeline
        result_ttl=86400,  # Keep result for 24h
        failure_ttl=86400,  # Keep failures for 24h
    )
    
    return ReportResponse(
        job_id=job.id,
        status=JobStatus.PENDING,
        created_at=datetime.now()
    )


@router.get("/reports/{job_id}", response_model=ReportStatusResponse)
@router.get("/reports/{job_id}/status", response_model=ReportStatusResponse)
async def get_report_status(job_id: str):
    """Récupérer le statut d'un rapport depuis Redis Queue."""
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job introuvable")
    
    # Map RQ job status to our JobStatus enum
    status_map = {
        "queued": JobStatus.PENDING,
        "started": JobStatus.EXTRACTING,  # Approximation
        "finished": JobStatus.COMPLETED,
        "failed": JobStatus.FAILED,
        "deferred": JobStatus.PENDING,
        "scheduled": JobStatus.PENDING,
        "stopped": JobStatus.FAILED,
        "canceled": JobStatus.FAILED,
    }
    
    status = status_map.get(job.get_status(), JobStatus.PENDING)
    
    # Get result or error
    result = None
    error = None
    logs = []
    
    if job.is_finished:
        result = job.result
    elif job.is_failed:
        error = str(job.exc_info) if job.exc_info else "Job failed"
    
    # Récupérer les logs depuis les métadonnées
    meta = job.meta or {}
    if "logs" in meta:
        logs = meta["logs"]
    
    # Ajouter le statut actuel aux logs si présent
    if meta.get("message"):
        logs.append({
            "phase": meta.get("status", ""),
            "message": meta.get("message", ""),
            "progress": meta.get("progress"),
            "timestamp": meta.get("timestamp", "")
        })
    
    def _safe_dt(value):
        return value if isinstance(value, datetime) else None

    created_at = _safe_dt(getattr(job, "created_at", None)) or datetime.now()
    started_at = _safe_dt(getattr(job, "started_at", None))
    completed_at = _safe_dt(getattr(job, "ended_at", None))

    return ReportStatusResponse(
        job_id=str(job_id),
        status=status,
        created_at=created_at,
        started_at=started_at,
        completed_at=completed_at,
        progress=meta.get("progress"),
        result=result,
        error=error,
        logs=logs
    )


@router.get("/reports/{job_id}/stream")
async def stream_report_logs(job_id: str):
    """
    Stream des logs en temps réel (Server-Sent Events).
    
    Poll Redis pour le statut du job et envoie des mises à jour via SSE.
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job introuvable")
    
    async def event_generator():
        """Génère les événements SSE."""
        last_status = None
        last_meta_message = None
        last_field_progress_version = None
        
        while True:
            # Rafraîchir le job
            job.refresh()
            current_status = job.get_status()
            
            # Récupérer les métadonnées pour les logs détaillés
            meta = job.meta or {}
            meta_status = meta.get("status", "")
            meta_message = meta.get("message", "")
            meta_progress = meta.get("progress", None)
            meta_field_progress = meta.get("field_progress")
            meta_field_order = meta.get("field_order")
            meta_field_progress_version = meta.get("field_progress_version")
            
            # Envoyer le log si nouveau message
            if meta_message and meta_message != last_meta_message:
                yield {
                    "event": "log",
                    "data": json.dumps({
                        "phase": meta_status,
                        "message": meta_message,
                        "progress": meta_progress,
                        "timestamp": datetime.now().isoformat(),
                        "field_progress": meta_field_progress,
                        "field_order": meta_field_order,
                        "field_progress_version": meta_field_progress_version,
                    })
                }
                last_meta_message = meta_message

            # Envoyer la progression détaillée (table champs LLM) si version changée
            if meta_field_progress_version is not None and meta_field_progress_version != last_field_progress_version:
                yield {
                    "event": "progress",
                    "data": json.dumps(
                        {
                            "status": meta_status or JobStatus.EXTRACTING,
                            "progress": meta_progress,
                            "field_progress": meta_field_progress,
                            "field_order": meta_field_order,
                            "field_progress_version": meta_field_progress_version,
                            "timestamp": datetime.now().isoformat(),
                        }
                    ),
                }
                last_field_progress_version = meta_field_progress_version
            
            # Envoyer le statut si changé
            if current_status != last_status:
                status_map = {
                    "queued": JobStatus.PENDING,
                    "started": JobStatus.EXTRACTING,
                    "finished": JobStatus.COMPLETED,
                    "failed": JobStatus.FAILED,
                }
                
                yield {
                    "event": "status",
                    "data": json.dumps({
                        "status": meta_status or status_map.get(current_status, JobStatus.PENDING),
                        "progress": meta_progress,
                        "field_progress": meta_field_progress,
                        "field_order": meta_field_order,
                        "field_progress_version": meta_field_progress_version,
                    })
                }
                
                last_status = current_status
            
            # Si terminé, envoyer le résultat et arrêter
            if job.is_finished or job.is_failed:
                result_data = {
                    "status": "completed" if job.is_finished else "failed",
                    "result": job.result if job.is_finished else None,
                    "error": str(job.exc_info) if job.is_failed else None
                }
                
                yield {
                    "event": "complete",
                    "data": json.dumps(result_data)
                }
                break
            
            # Attendre avant la prochaine vérification
            await asyncio.sleep(0.5)
    
    return EventSourceResponse(event_generator())


@router.get("/reports/{job_id}/download")
async def download_report(job_id: str):
    """Télécharger le rapport généré (DOCX)."""
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job introuvable")
    
    if not job.is_finished:
        raise HTTPException(
            status_code=400,
            detail=f"Le rapport n'est pas prêt (status: {job.get_status()})"
        )
    
    result = job.result
    if not result or result.get("status") != "success":
        raise HTTPException(status_code=404, detail="Rapport non disponible")
    
    docx_path = Path(result["output_path"])
    
    if not docx_path.exists():
        raise HTTPException(status_code=404, detail="Fichier DOCX introuvable sur le disque")
    
    return FileResponse(
        path=docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=docx_path.name
    )


@router.delete("/reports/{job_id}")
async def delete_report(job_id: str):
    """Supprimer un job de Redis."""
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        job.delete()
        return {"message": "Job supprimé"}
    except Exception:
        raise HTTPException(status_code=404, detail="Job introuvable")
