"""
Module d'analyse batch pour RH-Pro Training.

Scanne un batch entier de clients et retourne une table analysable.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .client_scanner import scan_client_folder


def scan_batch_clients(
    batch_path: str,
    limit: Optional[int] = None,
    min_pipeline_score: float = 0.3
) -> Dict[str, Any]:
    """
    Scanne tous les clients d'un batch et retourne une analyse complète.
    
    Args:
        batch_path: Chemin vers le dossier batch contenant les clients
        limit: Limite optionnelle du nombre de clients à scanner
        min_pipeline_score: Score minimum pour considérer un client compatible
        
    Returns:
        Dict avec:
        - batch_name: Nom du batch
        - batch_path: Chemin du batch
        - clients: Liste des analyses clients
        - summary: Statistiques globales
        - timestamp: ISO timestamp
    """
    batch_folder = Path(batch_path).resolve()
    
    if not batch_folder.exists():
        raise FileNotFoundError(f"Batch introuvable : {batch_folder}")
    
    if not batch_folder.is_dir():
        raise NotADirectoryError(f"Pas un dossier : {batch_folder}")
    
    # Lister les sous-dossiers (clients potentiels)
    client_folders = [
        d for d in batch_folder.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    
    if limit:
        client_folders = client_folders[:limit]
    
    # Scanner chaque client
    clients_analysis = []
    stats = {
        "total": 0,
        "pipeline_ready": 0,
        "gold_detected": 0,
        "has_rag_sources": 0,
        "errors": 0,
        "warnings_total": 0,
    }
    
    for client_folder in client_folders:
        stats["total"] += 1
        
        try:
            # Scanner le client
            scan_result = scan_client_folder(str(client_folder))
            
            # Calculer score de compatibilité
            compatibility_score = calculate_compatibility_score(scan_result)
            
            # Extraire les infos essentielles pour la table
            client_info = {
                "folder_name": scan_result["client_name"],
                "folder_path": scan_result["client_path"],
                "compatibility_score": compatibility_score,
                "compatible": compatibility_score >= min_pipeline_score,
                "gold_detected": scan_result["stats"]["gold_found"],
                "gold_score": scan_result["stats"]["gold_score"],
                "rag_sources_count": scan_result["stats"]["rag_sources_count"],
                "rag_sources_by_type": scan_result["stats"]["extensions"],
                "warnings_count": len(scan_result["warnings"]),
                "pipeline_ready": scan_result["pipeline_ready"],
                "scan_result": scan_result,  # Scan complet pour analyse détaillée
            }
            
            clients_analysis.append(client_info)
            
            # Mise à jour stats
            if scan_result["pipeline_ready"]:
                stats["pipeline_ready"] += 1
            if scan_result["stats"]["gold_found"]:
                stats["gold_detected"] += 1
            if scan_result["stats"]["rag_sources_count"] > 0:
                stats["has_rag_sources"] += 1
            stats["warnings_total"] += len(scan_result["warnings"])
        
        except Exception as e:
            stats["errors"] += 1
            clients_analysis.append({
                "folder_name": client_folder.name,
                "folder_path": str(client_folder),
                "compatibility_score": 0.0,
                "compatible": False,
                "gold_detected": False,
                "gold_score": 0.0,
                "rag_sources_count": 0,
                "rag_sources_by_type": {},
                "warnings_count": 1,
                "pipeline_ready": False,
                "error": str(e),
                "scan_result": None,
            })
    
    return {
        "batch_name": batch_folder.name,
        "batch_path": str(batch_folder),
        "clients": clients_analysis,
        "summary": stats,
        "timestamp": datetime.now().isoformat(),
    }


def calculate_compatibility_score(scan_result: Dict[str, Any]) -> float:
    """
    Calcule un score de compatibilité pipeline (0.0 à 1.0).
    
    Critères:
    - GOLD détecté et score >= 0.5 : 40%
    - GOLD détecté et score >= 0.3 : 30%
    - Au moins 3 sources RAG : 30%
    - Au moins 1 source RAG : 20%
    - Structure dossiers >= 4/7 : 20%
    - Structure dossiers >= 2/7 : 10%
    
    Args:
        scan_result: Résultat de scan_client_folder()
        
    Returns:
        Score entre 0.0 et 1.0
    """
    score = 0.0
    
    # GOLD
    if scan_result["stats"]["gold_found"]:
        gold_score = scan_result["stats"]["gold_score"]
        if gold_score >= 0.5:
            score += 0.4
        elif gold_score >= 0.3:
            score += 0.3
        else:
            score += 0.1
    
    # Sources RAG
    rag_count = scan_result["stats"]["rag_sources_count"]
    if rag_count >= 3:
        score += 0.3
    elif rag_count >= 1:
        score += 0.2
    
    # Structure dossiers
    folders_detected = scan_result["stats"]["folders_detected"]
    if folders_detected >= 4:
        score += 0.2
    elif folders_detected >= 2:
        score += 0.1
    
    # Bonus si pipeline_ready
    if scan_result["pipeline_ready"]:
        score += 0.1
    
    return min(1.0, score)


def get_client_analysis_detail(scan_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Génère une analyse détaillée d'un client pour l'UI.
    
    Retourne:
    - what_found: Ce qui a été trouvé
    - what_usable: Ce qui est exploitable
    - what_missing: Ce qui manque pour être 100% pipeline
    - gold_choice: Choix du GOLD avec justification
    - rag_preview: Aperçu des chunks (optionnel)
    
    Args:
        scan_result: Résultat de scan_client_folder()
        
    Returns:
        Dict avec sections d'analyse
    """
    # Ce qui a été trouvé
    what_found = {
        "gold": None,
        "rag_sources": [],
        "folders": [],
    }
    
    if scan_result["gold"]:
        what_found["gold"] = {
            "name": Path(scan_result["gold"]["path"]).name,
            "path": scan_result["gold"]["path"],
            "score": scan_result["gold"]["score"],
            "strategy": scan_result["gold"]["strategy"],
            "size_kb": scan_result["gold"]["size_bytes"] / 1024,
        }
    
    what_found["rag_sources"] = [
        {
            "name": Path(s["path"]).name,
            "category": s["category"],
            "extension": s["extension"],
            "size_kb": s["size_bytes"] / 1024,
        }
        for s in scan_result["rag_sources"]
    ]
    
    what_found["folders"] = [
        {"key": k, "path": v, "found": v is not None}
        for k, v in scan_result["folder_structure"].items()
    ]
    
    # Ce qui est exploitable
    what_usable = {
        "gold_usable": False,
        "rag_sources_usable": [],
        "folders_usable": [],
    }
    
    if scan_result["gold"] and scan_result["gold"]["score"] >= 0.3:
        what_usable["gold_usable"] = True
    
    what_usable["rag_sources_usable"] = [
        s for s in what_found["rag_sources"]
        if s["extension"] in [".docx", ".pdf", ".txt"]
    ]
    
    what_usable["folders_usable"] = [
        f for f in what_found["folders"]
        if f["found"] and f["key"] in ["01_personnel", "03_tests", "04_stages", "05_mesures"]
    ]
    
    # Ce qui manque
    what_missing = []
    
    if not scan_result["gold"]:
        what_missing.append("❌ Document GOLD (rapport final) introuvable")
    elif scan_result["gold"]["score"] < 0.3:
        what_missing.append(f"⚠️  Confiance GOLD faible ({scan_result['gold']['score']:.2f})")
    
    if scan_result["stats"]["rag_sources_count"] == 0:
        what_missing.append("❌ Aucune source RAG exploitable")
    elif scan_result["stats"]["rag_sources_count"] < 3:
        what_missing.append(f"⚠️  Peu de sources RAG ({scan_result['stats']['rag_sources_count']})")
    
    missing_folders = [
        f["key"] for f in what_found["folders"]
        if not f["found"] and f["key"] in ["01_personnel", "06_rapport"]
    ]
    if missing_folders:
        what_missing.append(f"⚠️  Dossiers manquants : {', '.join(missing_folders)}")
    
    if not what_missing:
        what_missing.append("✅ Client 100% pipeline-ready")
    
    # Choix du GOLD
    gold_choice = None
    if scan_result["gold"]:
        gold_choice = {
            "file": Path(scan_result["gold"]["path"]).name,
            "score": scan_result["gold"]["score"],
            "reason": _get_gold_choice_reason(scan_result["gold"]),
        }
    
    return {
        "what_found": what_found,
        "what_usable": what_usable,
        "what_missing": what_missing,
        "gold_choice": gold_choice,
        "rag_preview": None,  # À implémenter plus tard avec le RAG
    }


def _get_gold_choice_reason(gold_info: Dict[str, Any]) -> str:
    """
    Génère une justification textuelle du choix du GOLD.
    
    Args:
        gold_info: Info du GOLD
        
    Returns:
        Raison textuelle
    """
    strategy = gold_info["strategy"]
    score = gold_info["score"]
    
    if strategy == "06_rapport_final":
        return f"Trouvé dans '06 Rapport final' avec score {score:.2f}"
    elif strategy == "recursive_scan":
        return f"Détecté par mots-clés (score {score:.2f})"
    elif strategy == "most_recent_fallback":
        return f"Fichier DOCX le plus récent (score {score:.2f})"
    else:
        return f"Stratégie {strategy} (score {score:.2f})"


def export_batch_analysis(batch_result: Dict[str, Any], output_path: str) -> None:
    """
    Exporte l'analyse batch en JSON.
    
    Args:
        batch_result: Résultat de scan_batch_clients()
        output_path: Chemin du fichier JSON de sortie
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(batch_result, f, indent=2, ensure_ascii=False)
