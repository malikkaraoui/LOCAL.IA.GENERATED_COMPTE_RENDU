#!/usr/bin/env python3
"""
Script de test pour les nouveaux endpoints de file browser et training.

Usage:
    python test_api_filebrowser.py
"""

import sys
from pathlib import Path

# Ajouter le projet au path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.api.routes.filesystem import is_path_allowed, ALLOWED_ROOTS


def test_filesystem():
    """Test des fonctions filesystem."""
    print("=" * 70)
    print("TEST FILESYSTEM")
    print("=" * 70)
    
    # Test allowed roots
    print(f"\n📁 Racines autorisées : {len(ALLOWED_ROOTS)}")
    for root in ALLOWED_ROOTS:
        print(f"  • {root}")
    
    # Test is_path_allowed
    test_paths = [
        "/Users/malik/Documents/test",
        "/etc/passwd",
        "./sandbox",
        "/tmp/test",
    ]
    
    print("\n🔒 Tests de sécurité :")
    for path in test_paths:
        allowed = is_path_allowed(path)
        status = "✅ Autorisé" if allowed else "❌ Refusé"
        print(f"  {status} : {path}")


def test_scanner():
    """Test du scanner avec les enrichissements."""
    print("\n" + "=" * 70)
    print("TEST SCANNER ENRICHI")
    print("=" * 70)
    
    from src.rhpro.client_scanner import scan_client_folder
    import re
    
    # Tester sur un client existant
    test_client = "data/samples/client_01"
    
    if not Path(test_client).exists():
        print(f"\n⚠️  Client de test non trouvé : {test_client}")
        return
    
    print(f"\n🔍 Scan de : {test_client}")
    scan_result = scan_client_folder(test_client)
    
    # Enrichissements (simuler l'endpoint)
    
    # 1. detected_folders
    detected_folders = {
        key: {
            "found": path is not None,
            "path": path,
        }
        for key, path in scan_result["folder_structure"].items()
    }
    
    print("\n📂 Dossiers détectés :")
    for key, info in detected_folders.items():
        status = "✅" if info["found"] else "❌"
        print(f"  {status} {key:15s} : {info['path'] or 'Non trouvé'}")
    
    # 2. files_by_type
    files_by_type = {}
    for source in scan_result["rag_sources"]:
        ext = source["extension"]
        files_by_type[ext] = files_by_type.get(ext, 0) + 1
    
    print("\n📊 Fichiers par type :")
    for ext, count in files_by_type.items():
        print(f"  • {ext} : {count}")
    
    # 3. identity_candidates
    client_name = scan_result["client_name"]
    identity_candidates = {
        "nom_prenom_raw": client_name,
    }
    
    name_parts = client_name.split()
    if len(name_parts) >= 2:
        identity_candidates["nom"] = name_parts[0]
        identity_candidates["prenom"] = " ".join(name_parts[1:])
    
    print("\n👤 Identité (candidats) :")
    for key, value in identity_candidates.items():
        print(f"  • {key}: {value}")
    
    # 4. exploitable_summary
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
    
    print("\n📋 Résumé exploitable :")
    print(f"  • Pipeline ready : {exploitable_summary['can_process']}")
    print(f"  • GOLD disponible : {exploitable_summary['gold_available']}")
    print(f"  • Confiance GOLD : {exploitable_summary['gold_confidence']:.2f}")
    print(f"  • Sources RAG : {exploitable_summary['rag_sources_count']}")
    print(f"  • Types : {', '.join(exploitable_summary['rag_sources_types'])}")
    print(f"  • Taille totale : {exploitable_summary['total_data_mb']} MB")
    print(f"  • Qualité attendue : {exploitable_summary['expected_quality'].upper()}")
    
    if exploitable_summary['missing_critical']:
        print(f"  • Manquants critiques : {', '.join(exploitable_summary['missing_critical'])}")


def test_scan_batch():
    """Test du scan batch."""
    print("\n" + "=" * 70)
    print("TEST SCAN BATCH")
    print("=" * 70)
    
    from src.rhpro.client_scanner import scan_client_folder
    
    dataset_root = "data/samples"
    
    if not Path(dataset_root).exists():
        print(f"\n⚠️  Dataset non trouvé : {dataset_root}")
        return
    
    dataset_path = Path(dataset_root)
    
    # Découvrir les clients
    client_folders = [
        d for d in dataset_path.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    
    print(f"\n📁 Dataset : {dataset_root}")
    print(f"📊 {len(client_folders)} client(s) trouvé(s)")
    
    clients_data = []
    
    for client_folder in client_folders[:5]:  # Limiter à 5
        try:
            scan_result = scan_client_folder(str(client_folder))
            
            clients_data.append({
                "client_name": scan_result["client_name"],
                "pipeline_ready": scan_result["pipeline_ready"],
                "gold_score": scan_result["stats"]["gold_score"],
                "rag_sources_count": scan_result["stats"]["rag_sources_count"],
            })
        except Exception as e:
            clients_data.append({
                "client_name": client_folder.name,
                "pipeline_ready": False,
                "error": str(e),
            })
    
    # Stats
    pipeline_ready = [c for c in clients_data if c.get("pipeline_ready")]
    
    print(f"\n✅ Pipeline-ready : {len(pipeline_ready)}/{len(clients_data)}")
    
    print("\n📋 Détails :")
    for client in clients_data:
        status = "✅" if client.get("pipeline_ready") else "❌"
        name = client["client_name"]
        
        if "error" in client:
            print(f"  {status} {name} (erreur)")
        else:
            score = client.get("gold_score", 0)
            sources = client.get("rag_sources_count", 0)
            print(f"  {status} {name:20s} | GOLD: {score:.2f} | Sources: {sources}")


def main():
    """Fonction principale."""
    print("\n🧪 TESTS API FILE BROWSER & TRAINING\n")
    
    try:
        test_filesystem()
        test_scanner()
        test_scan_batch()
        
        print("\n" + "=" * 70)
        print("✅ TOUS LES TESTS TERMINÉS")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
