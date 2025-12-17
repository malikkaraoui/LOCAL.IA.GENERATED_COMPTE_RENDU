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
    # Lieu/Date
    location_city: str = "",
    location_date: str = "",
    auto_location_date: bool = True,
    # LLM
    llm_host: str = "http://localhost:11434",
    llm_model: str = "mistral:latest",
    temperature: float = 0.2,
    topk: int = 10,
    top_p: float = 0.9,
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
    
    logger.info(f"Starting report job", extra={
        "job_id": job_id,
        "client_name": client_name,
        "source_file": source_file
    })
    
    try:
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
            location_city=location_city,
            location_date=location_date,
            auto_location_date=auto_location_date,
            llm_host=llm_host,
            llm_model=llm_model,
            temperature=temperature,
            topk=topk,
            top_p=top_p,
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
            if job:
                job.meta.update(update)
                job.save_meta()
        
        # Run orchestrator
        orchestrator = ReportOrchestrator(params, progress_callback)
        result = orchestrator.run()
        
        logger.info(f"Job completed successfully", extra={
            "job_id": job_id,
            "output": result.get("output_path")
        })
        
        return result
            
    except Exception as e:
        logger.exception("Unexpected error in job", extra={
            "job_id": job_id
        })
        return {
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__
        }


def start_worker(queue_name: str = "reports"):
    """
    Start RQ worker to process jobs.
    
    Args:
        queue_name: Name of the queue to listen to
    """
    logger.info(f"Starting RQ worker for queue: {queue_name}")
    
    redis_conn = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=False
    )
    
    queue = Queue(queue_name, connection=redis_conn)
    
    # Sur macOS, utiliser SimpleWorker pour éviter les problèmes de fork
    import platform
    if platform.system() == "Darwin":  # macOS
        from rq import SimpleWorker
        worker = SimpleWorker([queue], connection=redis_conn)
        logger.info("Using SimpleWorker (no fork) for macOS compatibility")
    else:
        worker = Worker([queue], connection=redis_conn)
    
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    start_worker()
