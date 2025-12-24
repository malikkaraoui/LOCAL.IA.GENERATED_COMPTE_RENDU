"""Worker job pour l'analyse training (simulation pour l'instant)."""

import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any
from rq import get_current_job

# Fix macOS fork issue
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

from backend.api.services.training_status import set_training_status

logger = logging.getLogger(__name__)


def _generate_minimal_ruleset(batch_name: str) -> Dict[str, Any]:
    """Génère un ruleset minimal hardcodé (Step 3).
    
    Args:
        batch_name: Nom du batch d'entraînement
        
    Returns:
        Dictionnaire représentant le ruleset complet
    """
    return {
        "meta": {
            "batch_name": batch_name,
            "created_at": datetime.utcnow().isoformat(),
            "version": "0.1",
            "description": "Ruleset minimal généré automatiquement (hardcodé)"
        },
        "placeholders": [
            # Champs courts (1 ligne)
            {
                "key": "MONSIEUR_OU_MADAME",
                "rules": {
                    "length": "short",
                    "lines": 1,
                    "allowed_source": ["docs", "forms"],
                    "forbidden": ["invent_if_missing"],
                    "fallback": "NOT_FOUND"
                }
            },
            {
                "key": "NAME",
                "rules": {
                    "length": "short",
                    "lines": 1,
                    "allowed_source": ["docs", "forms"],
                    "forbidden": ["invent_if_missing"],
                    "fallback": "NOT_FOUND"
                }
            },
            {
                "key": "SURNAME",
                "rules": {
                    "length": "short",
                    "lines": 1,
                    "allowed_source": ["docs", "forms"],
                    "forbidden": ["invent_if_missing"],
                    "fallback": "NOT_FOUND"
                }
            },
            {
                "key": "NUMERO_AVS",
                "rules": {
                    "length": "short",
                    "lines": 1,
                    "allowed_source": ["docs", "forms"],
                    "forbidden": ["invent_if_missing"],
                    "fallback": "NOT_FOUND"
                }
            },
            {
                "key": "PROFESSION",
                "rules": {
                    "length": "short",
                    "lines": 1,
                    "allowed_source": ["docs", "forms"],
                    "forbidden": ["invent_if_missing"],
                    "fallback": "NOT_FOUND"
                }
            },
            {
                "key": "FORMATION",
                "rules": {
                    "length": "short",
                    "lines": 1,
                    "allowed_source": ["docs", "forms"],
                    "forbidden": ["invent_if_missing"],
                    "fallback": "NOT_FOUND"
                }
            },
            # Champs moyens (3-4 lignes)
            {
                "key": "Ressources_comportementales_Points_d'appui",
                "rules": {
                    "length": "medium",
                    "lines_min": 3,
                    "lines_max": 4,
                    "allowed_source": ["docs", "analysis"],
                    "forbidden": ["invent_if_missing"],
                    "fallback": "NOT_FOUND"
                }
            },
            {
                "key": "Ressources_comportementales_Points_de_vigilance",
                "rules": {
                    "length": "medium",
                    "lines_min": 3,
                    "lines_max": 4,
                    "allowed_source": ["docs", "analysis"],
                    "forbidden": ["invent_if_missing"],
                    "fallback": "NOT_FOUND"
                }
            },
            # Champs longs (documents)
            {
                "key": "LETTRE_MOTIVATION",
                "rules": {
                    "length": "long",
                    "type": "document_long",
                    "lines_min": 8,
                    "lines_max": 30,
                    "allowed_source": ["documents"],
                    "forbidden": ["invent_if_missing"],
                    "fallback": "NOT_FOUND"
                }
            },
            {
                "key": "CV",
                "rules": {
                    "length": "long",
                    "type": "document_long",
                    "lines_min": 8,
                    "lines_max": 30,
                    "allowed_source": ["documents"],
                    "forbidden": ["invent_if_missing"],
                    "fallback": "NOT_FOUND"
                }
            }
        ]
    }


def training_analysis_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute une analyse training (simulation avec étapes).
    
    Cette fonction est appelée par le worker RQ en arrière-plan.
    Elle simule une vraie analyse avec plusieurs étapes.
    
    Args:
        payload: Données de configuration (batch_name, source_root, etc.)
        
    Returns:
        Dictionnaire avec les résultats (pour l'instant minimal)
    """
    # Récupérer job_id depuis RQ (pattern recommandé)
    job = get_current_job()
    job_id = job.id
    
    try:
        logger.info(f"[Training {job_id}] Démarrage de l'analyse")
        
        # Étape 1: Initialisation
        set_training_status(
            job_id,
            status="running",
            message="Initialisation de l'analyse...",
            progress=5
        )
        time.sleep(2)  # Simulation
        
        # Étape 2: Préparation sandbox
        set_training_status(
            job_id,
            status="running",
            message=f"Préparation du sandbox: {payload.get('sandbox_root', 'N/A')}",
            progress=15
        )
        time.sleep(2)
        
        # Étape 3: Scan des fichiers
        batch_name = payload.get('batch_name', 'UNKNOWN')
        set_training_status(
            job_id,
            status="running",
            message=f"Scan du batch {batch_name}...",
            progress=30
        )
        time.sleep(3)
        
        # Étape 4: Analyse des dossiers
        folders = payload.get('folders', {})
        folder_count = len(folders)
        set_training_status(
            job_id,
            status="running",
            message=f"Analyse de {folder_count} dossiers...",
            progress=50
        )
        time.sleep(3)
        
        # Étape 5: Extraction des patterns
        set_training_status(
            job_id,
            status="running",
            message="Extraction des patterns de rédaction...",
            progress=70
        )
        time.sleep(3)
        
        # Étape 6: Génération du ruleset
        set_training_status(
            job_id,
            status="running",
            message="Génération du ruleset...",
            progress=90
        )
        
        # Générer le ruleset.json hardcodé (Step 3)
        sandbox_root = payload.get('sandbox_root', 'output')
        os.makedirs(sandbox_root, exist_ok=True)
        
        ruleset_path = os.path.join(sandbox_root, 'ruleset.json')
        ruleset_data = _generate_minimal_ruleset(batch_name)
        
        with open(ruleset_path, 'w', encoding='utf-8') as f:
            json.dump(ruleset_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[Training {job_id}] Ruleset généré: {ruleset_path}")
        
        # Calculer le chemin relatif pour artifact_path
        # Enlever le préfixe du workspace si présent
        relative_path = ruleset_path
        if os.path.isabs(ruleset_path):
            # Essayer de rendre relatif au workspace
            try:
                cwd = os.getcwd()
                relative_path = os.path.relpath(ruleset_path, cwd)
            except ValueError:
                # Si impossible, garder tel quel
                pass
        
        time.sleep(1)
        
        # Étape finale: Terminé avec artifact_path
        set_training_status(
            job_id,
            status="done",
            message=f"Ruleset généré: {relative_path}",
            progress=100,
            artifact_path=relative_path
        )
        
        logger.info(f"[Training {job_id}] Analyse terminée avec succès")
        
        return {
            "job_id": job_id,
            "status": "done",
            "batch_name": batch_name,
            "folders_analyzed": folder_count,
            "artifact_path": relative_path,
        }
        
    except Exception as e:
        logger.error(f"[Training {job_id}] Erreur: {e}", exc_info=True)
        set_training_status(
            job_id,
            status="error",
            message=f"Erreur lors de l'analyse: {str(e)}",
            progress=0
        )
        raise
