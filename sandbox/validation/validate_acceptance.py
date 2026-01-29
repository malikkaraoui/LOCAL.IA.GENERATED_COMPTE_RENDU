#!/usr/bin/env python3
"""
Script de validation automatique des critères d'acceptation.

Usage:
    python validate_acceptance.py

Vérifie que :
- 5 clients normalisés en sandbox
- GOLD détectés ou warnings clairs
- RAG index construits
- DOCX générés
- Batch 5/5 success
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple


def validate_sandbox(batch_name: str = "BATCH_20") -> Tuple[bool, str]:
    """Valide que 5 clients sont normalisés en sandbox."""
    sandbox_path = Path(f"sandbox/{batch_name}")
    
    if not sandbox_path.exists():
        return False, f"❌ Sandbox non trouvé : {sandbox_path}"
    
    client_dirs = [d for d in sandbox_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
    
    if len(client_dirs) < 5:
        return False, f"❌ Seulement {len(client_dirs)}/5 clients normalisés"
    
    # Vérifier structure pour chaque client
    for client_dir in client_dirs[:5]:
        if not (client_dir / "sources").exists():
            return False, f"❌ Dossier sources/ manquant pour {client_dir.name}"
        
        if not (client_dir / "meta.json").exists():
            return False, f"❌ Fichier meta.json manquant pour {client_dir.name}"
    
    return True, f"✅ {len(client_dirs)} clients normalisés en sandbox"


def validate_gold_detection(batch_name: str = "BATCH_20") -> Tuple[bool, str]:
    """Valide que GOLD est détecté OU warnings clairs."""
    sandbox_path = Path(f"sandbox/{batch_name}")
    
    if not sandbox_path.exists():
        return False, "❌ Sandbox non trouvé"
    
    client_dirs = [d for d in sandbox_path.iterdir() if d.is_dir() and not d.name.startswith(".")][:5]
    
    gold_detected = 0
    warnings_present = 0
    
    from src.utils.file_filters import is_ignored_filename
    for client_dir in client_dirs:
        gold_dir = client_dir / "gold"
        meta_file = client_dir / "meta.json"
        
        # Vérifier si GOLD présent
        if gold_dir.exists():
            gold_files = [f for f in gold_dir.glob("*.docx") if not is_ignored_filename(f)]
            if gold_files:
                gold_detected += 1
                continue
        
        # Vérifier si warning présent dans meta.json
        if meta_file.exists():
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                if meta.get("warnings"):
                    warnings_present += 1
    
    total_ok = gold_detected + warnings_present
    
    if total_ok < len(client_dirs):
        return False, f"❌ GOLD détecté ou warning : {total_ok}/{len(client_dirs)}"
    
    return True, f"✅ GOLD détecté: {gold_detected}, Warnings: {warnings_present}"


def validate_rag_index() -> Tuple[bool, str]:
    """Valide que RAG index est construit."""
    output_path = Path("output")
    
    if not output_path.exists():
        return False, "❌ Dossier output non trouvé"
    
    from src.utils.file_filters import is_ignored_filename
    debug_files = [f for f in output_path.glob("*_debug.json") if not is_ignored_filename(f)]
    
    if len(debug_files) < 5:
        return False, f"❌ Seulement {len(debug_files)}/5 fichiers debug.json"
    
    index_ok = 0
    
    for debug_file in debug_files[:5]:
        with open(debug_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            if "index" in data:
                chunks_created = data["index"].get("chunks_created", 0)
                if chunks_created > 0:
                    index_ok += 1
    
    if index_ok < 5:
        return False, f"❌ RAG index construit : {index_ok}/5"
    
    return True, f"✅ RAG index construit : {index_ok}/5"


def validate_docx_generated() -> Tuple[bool, str]:
    """Valide que DOCX sont générés."""
    output_path = Path("output")
    
    if not output_path.exists():
        return False, "❌ Dossier output non trouvé"
    
    from src.utils.file_filters import is_ignored_filename
    docx_files = [f for f in output_path.glob("*_generated.docx") if not is_ignored_filename(f)]
    
    if len(docx_files) < 5:
        return False, f"❌ Seulement {len(docx_files)}/5 DOCX générés"
    
    # Vérifier taille > 0
    for docx_file in docx_files[:5]:
        if docx_file.stat().st_size == 0:
            return False, f"❌ DOCX vide : {docx_file.name}"
    
    return True, f"✅ {len(docx_files)} DOCX générés"


def validate_metrics() -> Tuple[bool, str]:
    """Valide que métriques sont présentes et cohérentes."""
    output_path = Path("output")
    
    if not output_path.exists():
        return False, "❌ Dossier output non trouvé"
    
    from src.utils.file_filters import is_ignored_filename
    metrics_files = [f for f in output_path.glob("*_metrics.json") if not is_ignored_filename(f)]
    
    if len(metrics_files) < 5:
        return False, f"❌ Seulement {len(metrics_files)}/5 metrics.json"
    
    success_count = 0
    total_quality = 0
    
    for metrics_file in metrics_files[:5]:
        with open(metrics_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Vérifier champs requis
            required_fields = [
                "required_coverage", "weighted_coverage",
                "quality_score", "avg_confidence"
            ]
            
            if not all(field in data for field in required_fields):
                return False, f"❌ Champs manquants dans {metrics_file.name}"
            
            # Vérifier cohérence
            quality_score = data["quality_score"]
            if 0 <= quality_score <= 1:
                success_count += 1
                total_quality += quality_score
    
    if success_count < 5:
        return False, f"❌ Métriques cohérentes : {success_count}/5"
    
    avg_quality = total_quality / success_count
    
    return True, f"✅ Métriques OK (qualité moyenne : {avg_quality:.2f})"


def validate_batch_success() -> Tuple[bool, str]:
    """Valide le taux de succès global du batch."""
    checks = [
        validate_sandbox(),
        validate_gold_detection(),
        validate_rag_index(),
        validate_docx_generated(),
        validate_metrics(),
    ]
    
    passed = sum(1 for ok, _ in checks if ok)
    
    if passed == 5:
        return True, f"✅ Batch 5/5 success : tous les critères passés"
    else:
        return False, f"❌ Batch {passed}/5 : certains critères ont échoué"


def main():
    """Exécute toutes les validations."""
    print("=" * 70)
    print("VALIDATION CRITÈRES D'ACCEPTATION")
    print("=" * 70)
    print()
    
    checks = [
        ("1. Normalisation sandbox", validate_sandbox),
        ("2. Détection GOLD", validate_gold_detection),
        ("3. Index RAG construit", validate_rag_index),
        ("4. DOCX générés", validate_docx_generated),
        ("5. Métriques présentes", validate_metrics),
    ]
    
    results = []
    
    for name, validator in checks:
        print(f"{name}...")
        ok, message = validator()
        results.append((name, ok, message))
        print(f"  {message}")
        print()
    
    # Validation globale
    print("=" * 70)
    print("RÉSULTAT GLOBAL")
    print("=" * 70)
    print()
    
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    
    for name, ok, message in results:
        status = "✅" if ok else "❌"
        print(f"{status} {name}")
    
    print()
    print(f"Taux de succès : {passed}/{total}")
    
    if passed == total:
        print()
        print("🎉 TOUS LES CRITÈRES D'ACCEPTATION SONT VALIDÉS")
        print("✅ Definition of Done : TERMINÉE")
        return 0
    else:
        print()
        print("⚠️  Certains critères ne sont pas validés")
        print("❌ Definition of Done : NON TERMINÉE")
        return 1


if __name__ == "__main__":
    exit(main())
