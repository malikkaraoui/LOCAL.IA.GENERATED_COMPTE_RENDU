"""
Normalisation de dossiers clients RH-Pro en sandbox.

Copie la structure détectée dans un format standardisé "pipeline-ready"
sans toucher au dataset original.

Structure cible :
sandbox/<batch_name>/<client_slug>/
  ├── sources/          # Copies des fichiers RAG
  ├── gold/             # Copie du rapport final
  │   └── rapport_final.docx
  ├── normalized/       # (optionnel) alias pour le pipeline
  │   └── source.docx
  └── meta.json         # Métadonnées de la normalisation

Usage:
    from src.rhpro.client_normalizer import normalize_client_to_sandbox
    
    result = normalize_client_to_sandbox(
        scan_result,
        batch_name="BATCH_20",
        sandbox_root="./sandbox"
    )
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import re
import unicodedata


def slugify(text: str) -> str:
    """
    Convertit un texte en slug (filename-safe).
    
    Args:
        text: Texte à slugifier
        
    Returns:
        Slug (lowercase, sans accents, underscores)
    """
    # Normaliser et supprimer accents
    nfd = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    
    # Lowercase et remplacer espaces par underscores
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    
    return text


def ensure_dir(path: Path) -> Path:
    """
    Crée un dossier s'il n'existe pas.
    
    Args:
        path: Chemin du dossier
        
    Returns:
        Path créé
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_with_metadata(src: Path, dst: Path) -> Dict[str, Any]:
    """
    Copie un fichier avec métadonnées.
    
    Args:
        src: Fichier source
        dst: Fichier destination
        
    Returns:
        Dict avec infos de copie
    """
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    
    return {
        "original_path": str(src),
        "normalized_path": str(dst),
        "size_bytes": dst.stat().st_size,
        "copied_at": datetime.now().isoformat(),
    }


def normalize_client_to_sandbox(
    scan_result: Dict[str, Any],
    batch_name: str,
    sandbox_root: str = "./sandbox",
    create_normalized_alias: bool = True,
) -> Dict[str, Any]:
    """
    Normalise un client scanné dans la sandbox.
    
    Args:
        scan_result: Résultat de client_scanner.scan_client_folder()
        batch_name: Nom du batch (ex: "BATCH_20")
        sandbox_root: Racine de la sandbox
        create_normalized_alias: Créer normalized/source.docx ?
        
    Returns:
        Dict avec chemins créés et métadonnées
        
    Raises:
        ValueError: Si le scan n'est pas pipeline-ready
    """
    if not scan_result["pipeline_ready"]:
        raise ValueError(
            f"Client non pipeline-ready : {scan_result['client_name']}\n"
            f"Warnings : {', '.join(scan_result['warnings'])}"
        )
    
    # Créer slug pour le nom de client
    client_slug = slugify(scan_result["client_name"])
    
    # Structure cible
    sandbox_path = Path(sandbox_root).resolve()
    batch_path = sandbox_path / slugify(batch_name)
    client_path = batch_path / client_slug
    
    sources_dir = client_path / "sources"
    gold_dir = client_path / "gold"
    normalized_dir = client_path / "normalized"
    
    # Créer l'arborescence
    ensure_dir(sources_dir)
    ensure_dir(gold_dir)
    if create_normalized_alias:
        ensure_dir(normalized_dir)
    
    # Copier GOLD
    gold_info = None
    if scan_result["gold"]:
        gold_src = Path(scan_result["gold"]["path"])
        gold_dst = gold_dir / "rapport_final.docx"
        gold_info = copy_with_metadata(gold_src, gold_dst)
        
        # Créer alias normalized/source.docx
        if create_normalized_alias:
            normalized_src_dst = normalized_dir / "source.docx"
            shutil.copy2(gold_dst, normalized_src_dst)
    
    # Copier sources RAG
    sources_info = []
    for idx, source in enumerate(scan_result["rag_sources"], start=1):
        src_path = Path(source["path"])
        
        # Générer nom unique avec catégorie
        category = source["category"]
        ext = source["extension"]
        safe_name = slugify(src_path.stem)
        
        # Format : <category>_<idx>_<name><ext>
        dst_name = f"{category}_{idx:03d}_{safe_name}{ext}"
        dst_path = sources_dir / dst_name
        
        copy_info = copy_with_metadata(src_path, dst_path)
        copy_info["category"] = category
        sources_info.append(copy_info)
    
    # Générer meta.json
    meta = {
        "normalization_info": {
            "batch_name": batch_name,
            "client_slug": client_slug,
            "original_client_name": scan_result["client_name"],
            "original_client_path": scan_result["client_path"],
            "normalized_at": datetime.now().isoformat(),
            "sandbox_path": str(client_path),
        },
        "scan_result": scan_result,
        "gold": gold_info,
        "sources": sources_info,
        "file_counts": {
            "gold": 1 if gold_info else 0,
            "sources": len(sources_info),
            "total": (1 if gold_info else 0) + len(sources_info),
        },
        "pipeline_ready": True,
    }
    
    meta_path = client_path / "meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    return {
        "success": True,
        "client_slug": client_slug,
        "sandbox_path": str(client_path),
        "gold_path": str(gold_dir / "rapport_final.docx") if gold_info else None,
        "sources_path": str(sources_dir),
        "normalized_path": str(normalized_dir) if create_normalized_alias else None,
        "meta_path": str(meta_path),
        "file_counts": meta["file_counts"],
        "meta": meta,
    }


def normalize_batch_to_sandbox(
    dataset_root: str,
    client_names: list[str],
    batch_name: str,
    sandbox_root: str = "./sandbox",
    continue_on_error: bool = True,
) -> Dict[str, Any]:
    """
    Normalise plusieurs clients en batch.
    
    Args:
        dataset_root: Racine du dataset
        client_names: Liste des noms de dossiers clients
        batch_name: Nom du batch
        sandbox_root: Racine de la sandbox
        continue_on_error: Continuer si un client échoue ?
        
    Returns:
        Dict avec résultats par client + stats globales
    """
    from src.rhpro.client_scanner import scan_client_folder
    
    dataset_path = Path(dataset_root).resolve()
    results = []
    errors = []
    
    for client_name in client_names:
        client_folder = dataset_path / client_name
        
        try:
            # Scan
            scan_result = scan_client_folder(str(client_folder))
            
            # Normaliser si pipeline-ready
            if scan_result["pipeline_ready"]:
                norm_result = normalize_client_to_sandbox(
                    scan_result,
                    batch_name=batch_name,
                    sandbox_root=sandbox_root,
                )
                results.append({
                    "client_name": client_name,
                    "status": "success",
                    "pipeline_ready": True,
                    "sandbox_path": norm_result["sandbox_path"],
                })
            else:
                results.append({
                    "client_name": client_name,
                    "status": "not_ready",
                    "pipeline_ready": False,
                    "warnings": scan_result["warnings"],
                })
        
        except Exception as e:
            error_info = {
                "client_name": client_name,
                "status": "error",
                "error": str(e),
            }
            errors.append(error_info)
            
            if not continue_on_error:
                raise
    
    # Stats globales
    success_count = sum(1 for r in results if r["status"] == "success")
    not_ready_count = sum(1 for r in results if r["status"] == "not_ready")
    error_count = len(errors)
    
    return {
        "batch_name": batch_name,
        "dataset_root": str(dataset_path),
        "sandbox_root": sandbox_root,
        "results": results + errors,
        "stats": {
            "total": len(client_names),
            "success": success_count,
            "not_ready": not_ready_count,
            "errors": error_count,
            "success_rate": round(success_count / len(client_names) * 100, 1) if client_names else 0,
        },
        "normalized_at": datetime.now().isoformat(),
    }


def format_normalization_report(norm_result: Dict[str, Any]) -> str:
    """
    Formatte un rapport de normalisation batch.
    
    Args:
        norm_result: Résultat de normalize_batch_to_sandbox()
        
    Returns:
        Rapport formaté
    """
    lines = []
    lines.append("=" * 70)
    lines.append(f"📦 NORMALISATION BATCH : {norm_result['batch_name']}")
    lines.append("=" * 70)
    lines.append("")
    
    stats = norm_result["stats"]
    lines.append(f"📊 Résultats : {stats['total']} client(s)")
    lines.append(f"  ✅ Succès      : {stats['success']}")
    lines.append(f"  ⚠️  Non prêts   : {stats['not_ready']}")
    lines.append(f"  ❌ Erreurs     : {stats['errors']}")
    lines.append(f"  📈 Taux succès : {stats['success_rate']}%")
    lines.append("")
    
    # Détails par client
    lines.append("📁 Détails :")
    for result in norm_result["results"]:
        client = result["client_name"]
        status = result["status"]
        
        if status == "success":
            lines.append(f"  ✅ {client}")
            lines.append(f"     → {result['sandbox_path']}")
        elif status == "not_ready":
            lines.append(f"  ⚠️  {client} (non prêt)")
            for warning in result.get("warnings", []):
                lines.append(f"       {warning}")
        elif status == "error":
            lines.append(f"  ❌ {client} (erreur)")
            lines.append(f"       {result['error']}")
        
        lines.append("")
    
    lines.append("=" * 70)
    
    return "\n".join(lines)
