"""Job RQ: transcription audio (local) + ingestion RAG.

Ce job est conçu pour tourner dans le worker RQ existant (macOS/CPU).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from script_ai.rag.ingest_audio import ingest_audio_file

logger = logging.getLogger(__name__)


def transcribe_and_ingest_audio_job(
    file_path: str,
    source_id: str,
    extra_metadata: Optional[Dict[str, Any]] = None,
    cleanup: bool = True,
) -> Dict[str, Any]:
    """Transcrit et ingère un audio uploadé.

    Args:
        file_path: chemin vers l'audio uploadé
        source_id: identifiant (typiquement nom du client)
        extra_metadata: métadonnées additionnelles
        cleanup: si True, supprime le fichier uploadé après ingestion

    Returns:
        dict: résumé d'ingestion
    """

    from rq import get_current_job

    job = get_current_job()
    job_id = job.id if job else "unknown"

    p = Path(file_path).expanduser().resolve()
    logger.info("audio_rag job start", extra={"job_id": job_id, "file": str(p), "source_id": source_id})

    try:
        result = ingest_audio_file(str(p), source_id=source_id, extra_metadata=extra_metadata)
        logger.info("audio_rag job success", extra={"job_id": job_id, "result": result})
        return result
    finally:
        if cleanup:
            try:
                if p.exists():
                    p.unlink()
                    logger.info("audio_rag cleanup ok", extra={"job_id": job_id, "file": str(p)})
            except Exception as exc:
                logger.warning("audio_rag cleanup failed: %s", exc, extra={"job_id": job_id, "file": str(p)})
