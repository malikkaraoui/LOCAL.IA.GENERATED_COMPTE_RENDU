"""RQ worker for processing report generation jobs."""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from redis import Redis
from rq import Worker, Queue

# Fix for macOS fork() issue - must be set before any other imports
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

from core.logger import setup_logging
from backend.config import settings

# Setup logging for worker
setup_logging(console_level=logging.INFO, format_json=False)
logger = logging.getLogger(__name__)


class JobCancelled(RuntimeError):
    """Exception levée quand une annulation a été demandée via l'API."""


def process_report_job(
    client_name: str,
    clients_root: Optional[str] = None,
    source_file: Optional[str] = None,
    extract_method: str = "auto",
    template_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    # Identité
    name: str = "",
    surname: str = "",
    civility: str = "Monsieur",
    avs_number: str = "",
    # Template placeholders (déterministes)
    titre_document: str = "",
    # Lieu/Date
    location_city: str = "",
    location_date: str = "",
    auto_location_date: bool = True,
    # LLM
    llm_host: str = "http://localhost:11434",
    llm_model: str = "qwen3-next:latest",
    temperature: float = 0.2,
    topk: int = 10,
    top_p: float = 0.9,
    max_chars_multiplier: float = 1.0,
    # ✅ NOUVEAU: Config LLM unifiée (prioritaire si fourni)
    llm: Optional[Dict[str, Any]] = None,
    # Options
    include_filters: list = None,
    exclude_filters: list = None,
    force_reextract: bool = False,
    enable_soffice: bool = False,
    export_pdf: bool = False,
) -> Dict[str, Any]:
    """
    Process a report generation job.
    
    This function runs in an RQ worker process and executes the full
    report generation pipeline: extraction, generation, rendering.
    
    Args:
        client_name: Name of the client
        source_file: Path to source document
        extract_method: Extraction method (auto, pypdf, docx, soffice)
        name: First name
        surname: Last name
        civility: Monsieur/Madame/Autre
        avs_number: Swiss AVS number
        location_city: City for location/date
        location_date: Custom location/date string
        auto_location_date: Use current date automatically
        llm_host: Ollama API URL
        llm_model: Model name
        temperature: LLM temperature
        topk: Top-K sampling
        top_p: Top-P sampling
        include_filters: Include filters for extraction
        exclude_filters: Exclude filters for extraction
        force_reextract: Force re-extraction even if cache exists
        enable_soffice: Enable LibreOffice conversion for legacy formats
        export_pdf: Export to PDF after DOCX generation
        
    Returns:
        dict: Job result with output_path and metadata
    """
    # Get job ID from RQ context
    from rq import get_current_job
    job = get_current_job()
    job_id = job.id if job else "unknown"

    def _check_cancel_requested() -> None:
        """Vérifie si l'annulation a été demandée via job.meta.

        Note: on refresh le job pour récupérer les metas mises à jour côté API.
        """
        if not job:
            return
        try:
            job.refresh()
        except Exception:
            # Si le job a été supprimé, on ne doit pas faire tomber le worker.
            return
        if job.meta.get("cancel_requested") is True:
            raise JobCancelled("Annulation demandée par l'utilisateur")
    
    # ✅ Créer LLMConfig depuis l'objet llm si fourni
    from core.llm_router import LLMConfig
    llm_config = None
    
    if llm:
        llm_config = LLMConfig(
            provider=llm.get("provider", "ollama"),
            base_url=llm.get("base_url") or llm_host,
            model=llm.get("model") or llm_model,
            temperature=llm.get("temperature", temperature),
            max_tokens=llm.get("max_tokens", 4096),
            top_p=llm.get("top_p", top_p),
            timeout=llm.get("timeout", 900.0),
        )
        logger.info(
            f"✅ LLM Config from API: provider={llm_config.provider} model={llm_config.model}",
            extra={"job_id": job_id}
        )
    
    logger.info(f"Starting report job", extra={
        "job_id": job_id,
        "client_name": client_name,
        "source_file": source_file
    })
    
    try:
        _check_cancel_requested()
        # Verify client directory exists
        base_clients_dir = settings.CLIENTS_DIR
        if clients_root:
            p = Path(clients_root)
            base_clients_dir = p if p.is_absolute() else (settings.CLIENTS_DIR.parent / p)

        client_dir = base_clients_dir / client_name
        if not client_dir.exists():
            raise ValueError(f"Client directory not found: {client_dir}")
        
        # Prepare output directory
        if output_dir:
            out_dir = Path(output_dir)
            out_dir = out_dir if out_dir.is_absolute() else (settings.CLIENTS_DIR.parent / out_dir)
        else:
            out_dir = client_dir / "06 Rapport final"

        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Output file name
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = out_dir / f"rapport_{timestamp}.docx"

        tpl_path = settings.TEMPLATE_PATH
        if template_path:
            p = Path(template_path)
            tpl_path = p if p.is_absolute() else (settings.CLIENTS_DIR.parent / p)
        
        # Import ici (et pas au niveau module) pour faciliter le patching en tests
        # et éviter des imports lourds au démarrage du worker.
        from backend.workers.orchestrator import ReportOrchestrator, ReportGenerationParams

        # Create orchestrator parameters
        params = ReportGenerationParams(
            client_dir=client_dir,
            template_path=tpl_path,
            output_path=output_path,
            name=name,
            surname=surname,
            civility=civility,
            avs_number=avs_number,
            titre_document=titre_document,
            location_city=location_city,
            location_date=location_date,
            auto_location_date=auto_location_date,
            llm_host=llm_host,
            llm_model=llm_model,
            temperature=temperature,
            topk=topk,
            top_p=top_p,
            max_chars_multiplier=max_chars_multiplier,
            llm_config=llm_config,  # ✅ Passer la config unifiée
            extract_method=extract_method,
            source_file=source_file,
            enable_soffice=enable_soffice,
            include_filters=include_filters or [],
            exclude_filters=exclude_filters or [],
            force_reextract=force_reextract,
            export_pdf=export_pdf
        )
        
        # Progress callback for RQ meta updates
        def progress_callback(update: Dict[str, Any]):
            """Update job metadata with progress."""
            # Vérifier annulation avant de pousser de nouvelles metas.
            _check_cancel_requested()
            if not job:
                return
            try:
                job.meta.update(update)
                job.save_meta()
            except Exception:
                # Ne jamais faire tomber le worker si les metas ne peuvent pas être sauvées
                # (ex: job supprimé, redis instable, etc.).
                logger.warning("Unable to save job meta update", extra={"job_id": job_id})
        
        # Run orchestrator
        orchestrator = ReportOrchestrator(params, progress_callback)
        result = orchestrator.run()

        # Vérifier annulation juste après la fin (cas rare: annulation demandée pendant la dernière étape)
        _check_cancel_requested()
        
        logger.info(f"Job completed successfully", extra={
            "job_id": job_id,
            "output": result.get("output_path")
        })
        
        return result

    except JobCancelled as e:
        logger.info("Job cancelled", extra={"job_id": job_id})
        # Pousser un dernier état lisible côté UI.
        if job:
            try:
                job.meta.update({
                    "status": "CANCELLED",
                    "message": str(e),
                    "progress": None,
                })
                job.save_meta()
            except Exception:
                pass
        return {
            "status": "cancelled",
            "error": str(e),
            "error_type": "JobCancelled",
        }
            
    except Exception as e:
        logger.exception("Unexpected error in job", extra={
            "job_id": job_id
        })
        return {
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__
        }


def start_worker(queue_name: str = "reports,rag,training"):
    """
    Start RQ worker to process jobs.
    
    Args:
        queue_name: Name(s) of the queue(s) to listen to (CSV)
    """
    queue_names = [q.strip() for q in (queue_name or "").split(",") if q.strip()]
    if not queue_names:
        queue_names = ["reports"]

    logger.info(f"Starting RQ worker for queues: {queue_names}")
    
    redis_conn = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=False
    )
    
    queues = [Queue(name, connection=redis_conn) for name in queue_names]
    
    # Sur macOS, utiliser SimpleWorker pour éviter les problèmes de fork
    import platform
    if platform.system() == "Darwin":  # macOS
        from rq import SimpleWorker
        worker = SimpleWorker(
            queues,
            connection=redis_conn,
            default_worker_ttl=1800,  # 30 min — éviter AbandonedJobError sur longs jobs LLM
        )
        logger.info("Using SimpleWorker (no fork) for macOS compatibility — worker_ttl=1800s")
    else:
        worker = Worker(
            queues,
            connection=redis_conn,
            default_worker_ttl=1800,
        )

    worker.work(with_scheduler=True)


if __name__ == "__main__":
    start_worker()
