#!/usr/bin/env python3
"""
Demo Batch Parser — CLI pour parser plusieurs dossiers clients en mode batch

Usage:
    python demo_batch.py data/samples --output out/batch
    python demo_batch.py data/samples --output out/batch --profile stage
    python demo_batch.py data/samples --write-in-source
"""
import argparse
import sys
from pathlib import Path

# Ajouter src/ au path pour les imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rhpro.batch_runner import run_batch, discover_sources


def main():
    parser = argparse.ArgumentParser(
        description="Parser plusieurs dossiers clients RH-Pro en batch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_batch.py data/samples
  python demo_batch.py data/samples --output out/batch
  python demo_batch.py data/samples --output out/batch --profile stage
  python demo_batch.py data/samples --write-in-source
        """
    )
    
    parser.add_argument(
        "root_dir",
        help="Dossier racine contenant les dossiers clients (ex: data/samples)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="out/batch",
        help="Dossier de sortie pour les rapports agrégés (défaut: out/batch)"
    )
    
    parser.add_argument(
        "--ruleset", "-r",
        default="config/rulesets/rhpro_v1.yaml",
        help="Chemin vers le ruleset YAML (défaut: config/rulesets/rhpro_v1.yaml)"
    )
    
    parser.add_argument(
        "--profile", "-p",
        choices=["bilan_complet", "placement_suivi", "stage"],
        help="Forcer un profil de production gate (sinon auto-détection)"
    )
    
    parser.add_argument(
        "--write-in-source",
        action="store_true",
        help="Écrire source_normalized.json dans chaque dossier client"
    )
    
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Lister uniquement les dossiers découverts sans les parser"
    )
    
    args = parser.parse_args()
    
    # Validation
    root_path = Path(args.root_dir)
    if not root_path.exists():
        print(f"❌ Erreur: dossier racine introuvable: {args.root_dir}")
        sys.exit(1)
    
    ruleset_path = Path(args.ruleset)
    if not ruleset_path.exists():
        print(f"❌ Erreur: ruleset introuvable: {args.ruleset}")
        sys.exit(1)
    
    # Découverte
    print(f"🔍 Découverte des dossiers clients dans: {args.root_dir}")
    try:
        discovered = discover_sources(args.root_dir)
    except Exception as e:
        print(f"❌ Erreur lors de la découverte: {e}")
        sys.exit(1)
    
    if not discovered:
        print("⚠️  Aucun dossier contenant 'source.docx' trouvé.")
        sys.exit(0)
    
    print(f"✓ {len(discovered)} dossier(s) découvert(s):")
    for folder in discovered:
        print(f"  - {folder.name}")
    
    if args.list_only:
        sys.exit(0)
    
    # Exécution du batch
    print(f"\n🚀 Lancement du batch parsing...")
    print(f"   Ruleset: {args.ruleset}")
    if args.profile:
        print(f"   Profil forcé: {args.profile}")
    print(f"   Output: {args.output}")
    print()
    
    try:
        batch_result = run_batch(
            root_dir=args.root_dir,
            ruleset_path=args.ruleset,
            output_dir=args.output,
            write_normalized_in_source=args.write_in_source,
            gate_profile_override=args.profile
        )
    except Exception as e:
        print(f"❌ Erreur fatale lors du batch: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Affichage du résumé
    summary = batch_result["summary"]
    print("=" * 60)
    print("📊 RÉSUMÉ DU BATCH")
    print("=" * 60)
    print(f"Total traité       : {summary['total_processed']}")
    print(f"Succès             : {summary['successful']}")
    print(f"Erreurs            : {summary['errors']}")
    print(f"Production Gate GO : {summary['gate_go']}")
    print(f"Production Gate NO : {summary['gate_no_go']}")
    print(f"Coverage moyen     : {summary['avg_coverage']:.1%}")
    print()
    
    # Détails par client
    for result in batch_result["results"]:
        client = result["client_name"]
        status = result["status"]
        
        if status == "success":
            profile = result.get("profile", "?")
            gate_status = result.get("gate_status", "?")
            coverage = result.get("required_coverage_ratio", 0.0)
            
            # Emoji selon le gate status
            emoji = "✅" if gate_status == "GO" else "⚠️" if gate_status == "NO-GO" else "❓"
            
            print(f"{emoji} {client:20s} | {profile:20s} | {gate_status:7s} | {coverage:5.1%}")
        else:
            error_type = result.get("error_type", "Unknown")
            print(f"❌ {client:20s} | ERROR: {error_type}")
    
    print()
    
    # Erreurs détaillées
    if summary["error_details"]:
        print("=" * 60)
        print("❌ ERREURS DÉTAILLÉES")
        print("=" * 60)
        for err in summary["error_details"]:
            print(f"• {err['client']}: {err['error']}")
        print()
    
    # Fichiers générés
    output_path = Path(args.output)
    print("=" * 60)
    print("📁 FICHIERS GÉNÉRÉS")
    print("=" * 60)
    print(f"• Rapport JSON  : {output_path / 'batch_report.json'}")
    print(f"• Rapport MD    : {output_path / 'batch_report.md'}")
    print(f"• Rapport CSV   : {output_path / 'batch_report.csv'}")
    for result in batch_result["results"]:
        if result["status"] == "success":
            client = result["client_name"]
            print(f"• {client:20s} : {output_path / client / 'normalized.json'}")
    print()
    
    print("✅ Batch terminé avec succès!")
    
    # Exit code selon les erreurs
    sys.exit(0 if summary["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
