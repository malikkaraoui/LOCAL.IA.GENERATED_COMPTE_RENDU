#!/usr/bin/env python3
"""
Script de test pour valider la détection et normalisation de clients.

Usage:
    # Tester 5 clients
    python demo_training_pipeline.py /path/to/dataset --limit 5
    
    # Tester un client spécifique
    python demo_training_pipeline.py /path/to/dataset --client "NOM Prenom"
    
    # Mode batch complet
    python demo_training_pipeline.py /path/to/dataset --batch BATCH_5 --normalize
"""

import sys
from pathlib import Path
import argparse

# Ajouter le projet au path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.rhpro.client_scanner import scan_client_folder, format_scan_report
from src.rhpro.client_normalizer import (
    normalize_client_to_sandbox,
    normalize_batch_to_sandbox,
    format_normalization_report,
)


def main():
    parser = argparse.ArgumentParser(
        description="Test du pipeline de détection et normalisation"
    )
    parser.add_argument(
        "dataset_root",
        help="Chemin vers le dataset racine (contenant les dossiers clients)",
    )
    parser.add_argument(
        "--client",
        help="Nom d'un client spécifique à tester",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limiter le nombre de clients à tester",
    )
    parser.add_argument(
        "--batch",
        default="TEST_BATCH",
        help="Nom du batch pour la normalisation",
    )
    parser.add_argument(
        "--sandbox",
        default="./sandbox",
        help="Dossier sandbox pour la normalisation",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Normaliser les clients pipeline-ready en sandbox",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lister les clients disponibles seulement",
    )
    
    args = parser.parse_args()
    
    # Valider dataset
    dataset_path = Path(args.dataset_root).resolve()
    if not dataset_path.exists():
        print(f"❌ Dataset introuvable : {dataset_path}")
        sys.exit(1)
    
    if not dataset_path.is_dir():
        print(f"❌ Pas un dossier : {dataset_path}")
        sys.exit(1)
    
    # Lister les clients
    client_folders = [
        d for d in dataset_path.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]
    
    print(f"\n📁 Dataset : {dataset_path}")
    print(f"📊 {len(client_folders)} dossier(s) client(s) trouvé(s)\n")
    
    if args.list:
        for i, folder in enumerate(client_folders, 1):
            print(f"  {i}. {folder.name}")
        print()
        return
    
    # Mode client unique
    if args.client:
        client_path = dataset_path / args.client
        if not client_path.exists():
            print(f"❌ Client introuvable : {args.client}")
            sys.exit(1)
        
        print(f"🔍 Scan du client : {args.client}\n")
        scan_result = scan_client_folder(str(client_path))
        print(format_scan_report(scan_result))
        
        if args.normalize and scan_result["pipeline_ready"]:
            print("\n🔧 Normalisation en sandbox...\n")
            norm_result = normalize_client_to_sandbox(
                scan_result,
                batch_name=args.batch,
                sandbox_root=args.sandbox,
            )
            print(f"✅ Normalisé dans : {norm_result['sandbox_path']}")
            print(f"   GOLD : {norm_result['gold_path']}")
            print(f"   Sources : {norm_result['file_counts']['sources']} fichier(s)")
        
        return
    
    # Mode batch
    selected_clients = client_folders[:args.limit] if args.limit else client_folders
    
    print(f"🎯 Test de {len(selected_clients)} client(s)\n")
    print("=" * 70)
    
    # Scanner tous les clients
    results = []
    for i, client_folder in enumerate(selected_clients, 1):
        print(f"\n[{i}/{len(selected_clients)}] 🔍 {client_folder.name}")
        print("-" * 70)
        
        try:
            scan_result = scan_client_folder(str(client_folder))
            results.append({
                "client_name": client_folder.name,
                "scan": scan_result,
                "success": True,
            })
            
            # Afficher résumé
            status = "✅ READY" if scan_result["pipeline_ready"] else "❌ NOT READY"
            print(f"Status : {status}")
            print(f"GOLD   : {'✅' if scan_result['gold'] else '❌'} (score: {scan_result['stats']['gold_score']:.2f})")
            print(f"Sources: {scan_result['stats']['rag_sources_count']} fichier(s)")
            
            if scan_result["warnings"]:
                print("Warnings:")
                for warning in scan_result["warnings"]:
                    print(f"  {warning}")
        
        except Exception as e:
            print(f"❌ Erreur : {e}")
            results.append({
                "client_name": client_folder.name,
                "error": str(e),
                "success": False,
            })
    
    # Stats globales
    print("\n" + "=" * 70)
    print("📊 RÉSULTATS GLOBAUX")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r["success"])
    ready_count = sum(1 for r in results if r["success"] and r["scan"]["pipeline_ready"])
    error_count = sum(1 for r in results if not r["success"])
    
    print(f"Total      : {len(results)}")
    print(f"✅ Scannés : {success_count}")
    print(f"✅ Ready   : {ready_count} ({ready_count/len(results)*100:.1f}%)")
    print(f"❌ Erreurs : {error_count}")
    
    # Normalisation batch si demandé
    if args.normalize and ready_count > 0:
        print("\n" + "=" * 70)
        print("🔧 NORMALISATION BATCH")
        print("=" * 70)
        
        ready_clients = [
            r["client_name"] for r in results
            if r["success"] and r["scan"]["pipeline_ready"]
        ]
        
        print(f"\n📦 Normalisation de {len(ready_clients)} client(s)...\n")
        
        batch_result = normalize_batch_to_sandbox(
            dataset_root=str(dataset_path),
            client_names=ready_clients,
            batch_name=args.batch,
            sandbox_root=args.sandbox,
            continue_on_error=True,
        )
        
        print(format_normalization_report(batch_result))
        
        # Afficher le chemin sandbox
        sandbox_path = Path(args.sandbox).resolve() / args.batch.lower().replace(" ", "_")
        print(f"\n📁 Sandbox créée dans : {sandbox_path}")
        
        if sandbox_path.exists():
            normalized_clients = list(sandbox_path.iterdir())
            print(f"📊 {len(normalized_clients)} client(s) normalisé(s)\n")


if __name__ == "__main__":
    main()
