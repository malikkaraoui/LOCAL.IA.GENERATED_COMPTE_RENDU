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


class ScanBatchRequest(BaseModel):
    """Requête de scan batch pour découvrir les clients."""
    dataset_root: str
    batch_name: str = "BATCH"
    min_pipeline_score: float = 0.3


class TestClientRequest(BaseModel):
    """Requête de test (pré-vol) sur un client côté API.

    NOTE: Cette route est utilisée par l'UI React (/training) et vise à
    vérifier rapidement la préparabilité du client au pipeline.
    """

    client_name: str
    profile: str = "STANDARD"  # STRICT | STANDARD | DRAFT (tolérant)


@router.post("/scan-batch")
async def scan_batch(req: ScanBatchRequest):
    """
    Scanne un dataset pour découvrir et évaluer les clients.
    
    Args:
        req: Requête avec dataset_root et critères
        
    Returns:
        Liste des clients détectés avec scores et compatibilité
    """
    try:
        from src.rhpro.client_scanner import scan_client_folder
        
        dataset_path = Path(req.dataset_root)
        
        if not dataset_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Dataset introuvable : {req.dataset_root}"
            )
        
        if not dataset_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Pas un dossier : {req.dataset_root}"
            )
        
        # Découvrir les clients
        client_folders = [
            d for d in dataset_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        
        clients_data = []
        
        for client_folder in client_folders:
            try:
                scan_result = scan_client_folder(str(client_folder))
                
                clients_data.append({
                    "client_name": scan_result["client_name"],
                    "client_path": scan_result["client_path"],
                    "pipeline_ready": scan_result["pipeline_ready"],
                    "gold_score": scan_result["stats"]["gold_score"],
                    "rag_sources_count": scan_result["stats"]["rag_sources_count"],
                    "total_size_mb": scan_result["stats"]["total_size_mb"],
                    "warnings": scan_result["warnings"],
                })
            except Exception as e:
                clients_data.append({
                    "client_name": client_folder.name,
                    "client_path": str(client_folder),
                    "pipeline_ready": False,
                    "error": str(e),
                })
        
        # Filtrer par score si demandé
        pipeline_ready = [c for c in clients_data if c.get("pipeline_ready")]
        not_ready = [c for c in clients_data if not c.get("pipeline_ready")]
        
        return {
            "success": True,
            "dataset_root": str(dataset_path),
            "batch_name": req.batch_name,
            "clients": clients_data,
            "summary": {
                "total": len(clients_data),
                "pipeline_ready": len(pipeline_ready),
                "not_ready": len(not_ready),
                "ready_rate": round(len(pipeline_ready) / len(clients_data) * 100, 1) if clients_data else 0,
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du scan batch : {str(e)}"
        )


@router.post("/analyze-client")
async def analyze_client(req: ClientAnalyzeRequest):
    """
    Analyse un dossier client pour détecter GOLD et sources RAG.
    
    Enrichi avec :
    - detected_folders : structure détectée (01/03/04/05/06)
    - gold_candidates : tous les candidats GOLD avec scores
    - files_by_type : comptage par extension
    - identity_candidates : extraction nom/prénom/AVS si possible
    - exploitable_summary : résumé pour RAG
    
    Args:
        req: Requête avec client_folder_path
        
    Returns:
        Résultat du scan enrichi
        
    Raises:
        HTTPException 400 si le dossier n'existe pas ou est invalide
    """
    try:
        # Import local pour éviter dépendances circulaires
        from src.rhpro.client_scanner import scan_client_folder
        import re
        
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
        
        # Enrichissements
        
        # 1. detected_folders : reformater pour clarté
        detected_folders = {
            key: {
                "found": path is not None,
                "path": path,
            }
            for key, path in scan_result["folder_structure"].items()
        }
        
        # 2. files_by_type : compter par extension
        files_by_type = {}
        for source in scan_result["rag_sources"]:
            ext = source["extension"]
            files_by_type[ext] = files_by_type.get(ext, 0) + 1
        
        # 3. identity_candidates : extraire du nom de dossier
        client_name = scan_result["client_name"]
        identity_candidates = {
            "nom_prenom_raw": client_name,
        }
        
        # Tentative extraction NOM Prénom
        name_parts = client_name.split()
        if len(name_parts) >= 2:
            identity_candidates["nom"] = name_parts[0]
            identity_candidates["prenom"] = " ".join(name_parts[1:])
        
        # Recherche AVS dans les fichiers (basique)
        avs_pattern = r'\b756\.\d{4}\.\d{4}\.\d{2}\b'
        avs_found = []
        
        for source in scan_result["rag_sources"][:5]:  # Limiter à 5 fichiers
            try:
                if source["extension"] == ".txt":
                    with open(source["path"], "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(10000)  # 10KB max
                        matches = re.findall(avs_pattern, content)
                        avs_found.extend(matches)
            except:
                pass
        
        if avs_found:
            identity_candidates["avs_candidates"] = list(set(avs_found))
        
        # 4. gold_candidates : lister tous les GOLD possibles (pas juste le meilleur)
        # Note : le scanner ne retourne que le meilleur, on pourrait améliorer
        gold_candidates = []
        if scan_result["gold"]:
            gold_candidates.append({
                "path": scan_result["gold"]["path"],
                "score": scan_result["gold"]["score"],
                "strategy": scan_result["gold"]["strategy"],
                "selected": True,
            })
        
        # 5. exploitable_summary : résumé pour RAG
        exploitable_summary = {
            "can_process": scan_result["pipeline_ready"],
            "gold_available": scan_result["gold"] is not None,
            "gold_confidence": scan_result["stats"]["gold_score"],
            "rag_sources_count": scan_result["stats"]["rag_sources_count"],
            "rag_sources_types": list(files_by_type.keys()),
            "total_data_mb": scan_result["stats"]["total_size_mb"],
            "missing_critical": [
                key for key, val in detected_folders.items()
                if not val["found"] and key in ["01_personnel", "06_rapport"]
            ],
            "expected_quality": (
                "high" if scan_result["stats"]["rag_sources_count"] >= 5 and scan_result["stats"]["gold_score"] >= 0.6
                else "medium" if scan_result["stats"]["rag_sources_count"] >= 2 and scan_result["stats"]["gold_score"] >= 0.4
                else "low"
            ),
        }
        
        return {
            "success": True,
            "scan_result": scan_result,
            "detected_folders": detected_folders,
            "gold_candidates": gold_candidates,
            "files_by_type": files_by_type,
            "identity_candidates": identity_candidates,
            "exploitable_summary": exploitable_summary,
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


@router.post("/test-client")
async def test_client(req: TestClientRequest):
    """Test rapide d'un client (pré-vol) pour l'UI Training.

    Objectif : fournir un résultat stable sans lancer de génération LLM.
    Le score est une heuristique basée sur :
    - confiance GOLD (gold_score)
    - quantité de sources RAG (rag_sources_count)

    Returns:
        { success, status, score, reasons, actions, scan_summary }
    """
    try:
        from src.rhpro.client_scanner import scan_client_folder

        client_name = (req.client_name or "").strip()
        if not client_name:
            raise HTTPException(status_code=400, detail="client_name manquant")

        client_dir = settings.CLIENTS_DIR / client_name
        if not client_dir.exists() or not client_dir.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"Client '{client_name}' introuvable dans {settings.CLIENTS_DIR}",
            )

        scan_result = scan_client_folder(str(client_dir))

        warnings = list(scan_result.get("warnings") or [])
        stats = scan_result.get("stats") or {}
        gold_score = float(stats.get("gold_score") or 0.0)
        rag_sources_count = int(stats.get("rag_sources_count") or 0)
        pipeline_ready = bool(scan_result.get("pipeline_ready"))

        # Score heuristique [0..1]
        rag_component = min(1.0, rag_sources_count / 5.0) if rag_sources_count >= 0 else 0.0
        score = 0.5 * max(0.0, min(1.0, gold_score)) + 0.5 * rag_component
        score = round(score, 3)

        # Status (GO/DRAFT/NO_GO)
        profile = (req.profile or "STANDARD").strip().upper()
        if not pipeline_ready:
            status = "NO_GO"
        elif profile == "DRAFT":
            status = "DRAFT"
        else:
            # Heuristique: GO si score suffisant, sinon DRAFT.
            status = "GO" if score >= 0.7 else "DRAFT"

        # Reasons / actions
        reasons: list[str] = []
        actions: list[str] = []

        if warnings:
            reasons.extend(warnings)

        folder_structure = scan_result.get("folder_structure") or {}
        missing_required = [
            key
            for key in ("01_personnel", "06_rapport")
            if not folder_structure.get(key)
        ]

        if missing_required:
            actions.append(
                "Ajouter les dossiers requis: " + ", ".join(missing_required)
            )

        if not scan_result.get("gold"):
            actions.append(
                "Ajouter un rapport final (GOLD) dans le dossier '06 Rapport final' (DOC/DOCX)."
            )

        if rag_sources_count < 2:
            actions.append(
                "Ajouter davantage de sources exploitables (PDF/DOCX/TXT/MSG) pour améliorer le contexte RAG."
            )

        if pipeline_ready and not reasons and status != "GO":
            reasons.append("Client détecté comme pipeline-ready, mais qualité estimée moyenne.")

        return {
            "success": True,
            "client_name": scan_result.get("client_name", client_name),
            "status": status,
            "score": score,
            "reasons": reasons,
            "actions": actions,
            "scan_summary": {
                "pipeline_ready": pipeline_ready,
                "gold_score": gold_score,
                "rag_sources_count": rag_sources_count,
                "total_size_mb": stats.get("total_size_mb"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur test-client : {str(e)}")

