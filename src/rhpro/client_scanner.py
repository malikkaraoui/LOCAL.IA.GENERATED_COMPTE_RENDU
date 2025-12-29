"""
Scanner de dossiers clients RH-Pro.

Détecte et analyse la structure d'un dossier client pour identifier :
- Le fichier GOLD (rapport final de référence)
- Les sources RAG exploitables
- La compatibilité avec le pipeline

Usage:
    from src.rhpro.client_scanner import scan_client_folder
    
    result = scan_client_folder("/path/to/client/NOM Prenom")
    if result["pipeline_ready"]:
        print(f"Gold: {result['gold']['path']}")
        print(f"Sources: {len(result['rag_sources'])} fichiers")
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import re
from src.utils.file_filters import is_ignored_filename


# Sous-dossiers attendus dans la structure RH-Pro
EXPECTED_FOLDERS = {
    "01_personnel": ["01 Dossier personnel", "01", "Dossier personnel"],
    "02_cv": ["02 CV", "02", "CV"],
    "03_tests": ["03 Tests et bilans", "03", "Tests"],
    "04_stages": ["04 Stages", "04", "Stages"],
    "05_mesures": ["05 Mesures AI", "05", "Mesures"],
    "06_rapport": ["06 Rapport final", "06", "Rapport final", "Rapports"],
    "07_suivi": ["07 Suivi", "07", "Suivi"],
}

# Extensions de fichiers exploitables
DOCUMENT_EXTENSIONS = {".docx", ".pdf", ".txt", ".msg", ".doc"}
GOLD_EXTENSIONS = {".docx", ".doc"}

# Mots-clés pour détection GOLD (rapport final)
GOLD_KEYWORDS = [
    "rapport",
    "bilan",
    "orientation",
    "synthese",
    "synthèse",
    "final",
    "conclusion",
    "evaluation",
    "évaluation",
]


def normalize_folder_name(folder_name: str) -> str:
    """
    Normalise un nom de dossier pour la comparaison.
    
    Args:
        folder_name: Nom du dossier
        
    Returns:
        Nom normalisé (lowercase, sans accents)
    """
    import unicodedata
    
    # Supprimer les accents
    nfd = unicodedata.normalize('NFD', folder_name)
    text = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    
    # Lowercase et supprimer espaces multiples
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    
    return text


def find_folder(base_path: Path, folder_variants: List[str]) -> Optional[Path]:
    """
    Trouve un sous-dossier parmi plusieurs variantes possibles.
    
    Args:
        base_path: Chemin de base
        folder_variants: Liste des noms possibles
        
    Returns:
        Path du dossier trouvé ou None
    """
    if not base_path.exists() or not base_path.is_dir():
        return None
    
    # Normaliser les variantes
    normalized_variants = [normalize_folder_name(v) for v in folder_variants]
    
    # Chercher dans les enfants directs
    for child in base_path.iterdir():
        if child.is_dir():
            normalized_name = normalize_folder_name(child.name)
            if normalized_name in normalized_variants:
                return child
    
    return None


def score_gold_candidate(file_path: Path) -> float:
    """
    Calcule un score de probabilité qu'un fichier soit le GOLD.
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        Score entre 0.0 et 1.0
    """
    score = 0.0
    filename = file_path.name.lower()
    
    # Bonus si dans le bon dossier (06 Rapport final)
    parent_name = normalize_folder_name(file_path.parent.name)
    if "rapport" in parent_name or "06" in parent_name:
        score += 0.3
    
    # Bonus pour mots-clés dans le nom
    keyword_matches = sum(1 for kw in GOLD_KEYWORDS if kw in filename)
    score += min(keyword_matches * 0.15, 0.45)
    
    # Bonus pour extension prioritaire
    if file_path.suffix == ".docx":
        score += 0.15
    
    # Malus si nom générique ou template
    if any(word in filename for word in ["template", "modele", "modèle", "vierge", "copie"]):
        score -= 0.5
    
    return max(0.0, min(1.0, score))


def find_gold_document(client_folder: Path) -> Optional[Dict[str, Any]]:
    """
    Trouve le document GOLD (rapport final de référence).
    
    Stratégie :
    1. Chercher dans 06 Rapport final/
    2. Si non trouvé, scanner la racine et sous-dossiers
    3. Utiliser scoring pour choisir le meilleur candidat
    
    Args:
        client_folder: Dossier du client
        
    Returns:
        Dict avec path, score, strategy ou None
    """
    candidates = []
    
    # 1. Chercher dans 06 Rapport final
    rapport_folder = find_folder(client_folder, EXPECTED_FOLDERS["06_rapport"])
    if rapport_folder:
        for file_path in rapport_folder.rglob("*"):
            if file_path.is_file() and file_path.suffix in GOLD_EXTENSIONS and not is_ignored_filename(file_path):
                score = score_gold_candidate(file_path)
                candidates.append({
                    "path": str(file_path),
                    "score": score,
                    "strategy": "06_rapport_final",
                    "size_bytes": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                })
    
    # 2. Fallback : scanner tout le dossier client
    if not candidates:
        for file_path in client_folder.rglob("*"):
            if file_path.is_file() and file_path.suffix in GOLD_EXTENSIONS and not is_ignored_filename(file_path):
                score = score_gold_candidate(file_path)
                if score > 0.1:  # Seuil minimum
                    candidates.append({
                        "path": str(file_path),
                        "score": score,
                        "strategy": "recursive_scan",
                        "size_bytes": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    })
    
    # 3. Si toujours rien, prendre le docx le plus récent
    if not candidates:
        all_docx = [f for f in client_folder.rglob("*") 
                    if f.is_file() and f.suffix in GOLD_EXTENSIONS and not is_ignored_filename(f)]
        if all_docx:
            most_recent = max(all_docx, key=lambda f: f.stat().st_mtime)
            return {
                "path": str(most_recent),
                "score": 0.5,
                "strategy": "most_recent_fallback",
                "size_bytes": most_recent.stat().st_size,
                "modified": datetime.fromtimestamp(most_recent.stat().st_mtime).isoformat(),
            }
    
    # Retourner le meilleur candidat
    if candidates:
        best = max(candidates, key=lambda c: c["score"])
        return best
    
    return None


def find_rag_sources(client_folder: Path, index_msg: bool = False) -> List[Dict[str, Any]]:
    """
    Trouve tous les documents exploitables pour RAG.
    
    Cherche dans :
    - 01 Dossier personnel
    - 03 Tests et bilans
    - 04 Stages
    - 05 Mesures AI
    - Racine du client (avec filtre)
    
    Args:
        client_folder: Dossier du client
        index_msg: Si True, inclure les .msg dans rag_sources. Si False, les compter séparément.
        
    Returns:
        Liste de dicts avec path, category, extension, size_bytes
        
    CORRECTIF A: Support .msg avec option index_msg
    """
    sources = []
    
    # Dossiers à scanner
    scan_targets = [
        ("01_personnel", EXPECTED_FOLDERS["01_personnel"]),
        ("03_tests", EXPECTED_FOLDERS["03_tests"]),
        ("04_stages", EXPECTED_FOLDERS["04_stages"]),
        ("05_mesures", EXPECTED_FOLDERS["05_mesures"]),
    ]
    
    # Toutes les extensions sont indexées par défaut maintenant (y compris .msg)
    extensions_to_index = DOCUMENT_EXTENSIONS
    
    # Scanner les dossiers spécifiques
    for category, folder_variants in scan_targets:
        folder = find_folder(client_folder, folder_variants)
        if folder:
            for file_path in folder.rglob("*"):
                if file_path.is_file() and file_path.suffix in extensions_to_index and not is_ignored_filename(file_path):
                    sources.append({
                        "path": str(file_path),
                        "category": category,
                        "extension": file_path.suffix,
                        "size_bytes": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    })
    
    # Scanner la racine (uniquement fichiers directs, pas récursif)
    for file_path in client_folder.iterdir():
        if file_path.is_file() and file_path.suffix in extensions_to_index and not is_ignored_filename(file_path):
            # Exclure si c'est le gold déjà détecté
            sources.append({
                "path": str(file_path),
                "category": "root",
                "extension": file_path.suffix,
                "size_bytes": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            })
    
    return sources


def scan_client_folder(client_folder_path: str, index_msg: bool = False) -> Dict[str, Any]:
    """
    Analyse complète d'un dossier client.
    
    Args:
        client_folder_path: Chemin vers le dossier client
        index_msg: Si True, inclure .msg dans rag_sources. Si False (défaut), les compter dans warnings.
        
    Returns:
        Dict avec :
        - client_name: Nom du dossier
        - client_path: Chemin absolu
        - gold: Info sur le document GOLD ou None
        - rag_sources: Liste des sources RAG
        - folder_structure: Dossiers détectés
        - warnings: Liste des alertes
        - pipeline_ready: bool
        - stats: Statistiques
        - msg_files_count: Nombre de .msg détectés (si index_msg=False)
        
    CORRECTIF A: Support .msg avec option index_msg
    """
    client_folder = Path(client_folder_path).resolve()
    
    if not client_folder.exists():
        raise FileNotFoundError(f"Dossier client introuvable : {client_folder}")
    
    if not client_folder.is_dir():
        raise NotADirectoryError(f"Pas un dossier : {client_folder}")
    
    # Détecter la structure
    folder_structure = {}
    for key, variants in EXPECTED_FOLDERS.items():
        found = find_folder(client_folder, variants)
        folder_structure[key] = str(found) if found else None
    
    # Détecter GOLD
    gold = find_gold_document(client_folder)
    
    # Détecter sources RAG
    rag_sources = find_rag_sources(client_folder, index_msg=index_msg)
    
    # Compter tous les .msg détectés
    all_sources_with_msg = find_rag_sources(client_folder, index_msg=True)
    msg_files_count = sum(1 for s in all_sources_with_msg if s["extension"] == ".msg")
    
    # Exclure le gold des sources RAG si présent
    if gold:
        gold_path = gold["path"]
        rag_sources = [s for s in rag_sources if s["path"] != gold_path]
    
    # Générer warnings
    warnings = []
    
    if not gold:
        warnings.append("❌ Aucun document GOLD détecté")
    elif gold["score"] < 0.5:
        warnings.append(f"⚠️  Confiance GOLD faible ({gold['score']:.2f})")
    
    if not rag_sources:
        warnings.append("❌ Aucune source RAG trouvée")
    elif len(rag_sources) < 3:
        warnings.append(f"⚠️  Peu de sources RAG ({len(rag_sources)})")
    
    missing_folders = [key for key, path in folder_structure.items() 
                      if path is None and key in ["01_personnel", "06_rapport"]]
    if missing_folders:
        warnings.append(f"⚠️  Dossiers manquants : {', '.join(missing_folders)}")
    
    # Les .msg sont indexés par défaut maintenant
    
    # Pipeline ready ?
    pipeline_ready = (
        gold is not None and
        len(rag_sources) > 0 and
        gold["score"] >= 0.3
    )
    
    # Stats par extension
    extensions_count = {}
    for source in rag_sources:
        ext = source["extension"]
        extensions_count[ext] = extensions_count.get(ext, 0) + 1
    
    total_size = sum(s["size_bytes"] for s in rag_sources)
    if gold:
        total_size += gold["size_bytes"]
    
    return {
        "client_name": client_folder.name,
        "client_path": str(client_folder),
        "gold": gold,
        "rag_sources": rag_sources,
        "folder_structure": folder_structure,
        "warnings": warnings,
        "pipeline_ready": pipeline_ready,
        "stats": {
            "gold_found": gold is not None,
            "gold_score": gold["score"] if gold else 0.0,
            "rag_sources_count": len(rag_sources),
            "extensions": extensions_count,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "folders_detected": sum(1 for v in folder_structure.values() if v is not None),
            "folders_missing": sum(1 for v in folder_structure.values() if v is None),
            "msg_files_count": msg_files_count,  # ✅ CORRECTIF A
        },
        "scan_timestamp": datetime.now().isoformat(),
    }


def format_scan_report(scan_result: Dict[str, Any]) -> str:
    """
    Formatte un rapport de scan lisible.
    
    Args:
        scan_result: Résultat de scan_client_folder()
        
    Returns:
        Rapport formaté en texte
    """
    lines = []
    lines.append("=" * 70)
    lines.append(f"📁 SCAN CLIENT : {scan_result['client_name']}")
    lines.append("=" * 70)
    lines.append("")
    
    # Pipeline status
    status_emoji = "✅" if scan_result["pipeline_ready"] else "❌"
    lines.append(f"{status_emoji} Pipeline Ready : {scan_result['pipeline_ready']}")
    lines.append("")
    
    # GOLD
    lines.append("📄 GOLD (Rapport final) :")
    if scan_result["gold"]:
        gold = scan_result["gold"]
        lines.append(f"  ✓ Trouvé : {Path(gold['path']).name}")
        lines.append(f"    Score   : {gold['score']:.2f}")
        lines.append(f"    Strategy: {gold['strategy']}")
        lines.append(f"    Taille  : {gold['size_bytes'] / 1024:.1f} KB")
    else:
        lines.append("  ✗ Aucun document GOLD détecté")
    lines.append("")
    
    # Sources RAG
    stats = scan_result["stats"]
    lines.append(f"📚 Sources RAG : {stats['rag_sources_count']} fichier(s)")
    if scan_result["rag_sources"]:
        for ext, count in stats["extensions"].items():
            lines.append(f"  • {ext} : {count}")
        lines.append(f"  Total : {stats['total_size_mb']} MB")
    else:
        lines.append("  ✗ Aucune source RAG trouvée")
    lines.append("")
    
    # Structure
    lines.append(f"📂 Structure : {stats['folders_detected']}/{len(EXPECTED_FOLDERS)} dossiers")
    for key, path in scan_result["folder_structure"].items():
        status = "✓" if path else "✗"
        folder_name = Path(path).name if path else "Non trouvé"
        lines.append(f"  {status} {key:15s} → {folder_name}")
    lines.append("")
    
    # Warnings
    if scan_result["warnings"]:
        lines.append("⚠️  Warnings :")
        for warning in scan_result["warnings"]:
            lines.append(f"  {warning}")
        lines.append("")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)
