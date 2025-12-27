"""
Démo : Batch Report DoD (Definition of Done)

Illustre comment générer et exploiter un batch_report.json après validation.
"""
import json
from pathlib import Path
from src.rhpro.validation_profiles import validate_batch, ValidationProfile
from src.rhpro.batch_report import (
    generate_batch_report,
    print_batch_summary,
    filter_batch_report,
    load_batch_report,
)


def print_section(title: str):
    """Affiche un titre de section."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()


def demo_batch_report_generation():
    """Démontre la génération d'un batch report."""
    print_section("1. GÉNÉRATION DU BATCH REPORT")
    
    print("📋 Étapes :")
    print("  1. Valider tous les rapports d'un batch (validate_batch)")
    print("  2. Générer batch_report.json + CSV (generate_batch_report)")
    print("  3. Analyser les résultats")
    print()
    
    print("💻 Code Python :")
    print('''
from pathlib import Path
from src.rhpro.validation_profiles import validate_batch, ValidationProfile
from src.rhpro.batch_report import generate_batch_report

# Étape 1 : Valider le batch
output_dir = Path("output")
results = validate_batch(output_dir, ValidationProfile.STRICT)

# Étape 2 : Générer le batch report
report = generate_batch_report(
    validation_results=results,
    output_dir=output_dir,
    batch_name="batch_001",
    sandbox_dir=Path("sandbox")  # Optionnel : pour détecter GOLD
)

print(f"✅ Rapport généré : {report['report_json']}")
print(f"📊 CSV généré : {report['report_csv']}")
print(f"GO: {report['summary']['go_count']}/{report['summary']['total']}")
''')
    print()


def demo_batch_report_structure():
    """Montre la structure d'un batch_report.json."""
    print_section("2. STRUCTURE DU BATCH_REPORT.JSON")
    
    example_report = {
        "batch_name": "batch_001",
        "timestamp": "2025-12-27T10:30:00",
        "summary": {
            "total": 20,
            "go_count": 14,
            "no_go_count": 4,
            "draft_count": 2,
            "go_rate": 70.0,
            "gold_detected_count": 12,
            "gold_rate": 60.0,
            "top_failure_reasons": [
                {"reason": "missing_critical_fields", "count": 3},
                {"reason": "low_required_coverage", "count": 2},
                {"reason": "insufficient_sources", "count": 1}
            ]
        },
        "clients": [
            {
                "client_name": "DUPONT_Jean",
                "status": "GO",
                "profile": "strict",
                "scores": {
                    "quality_score": 0.82,
                    "required_coverage": 0.90,
                    "weighted_coverage": 0.88,
                    "avg_confidence": 0.78
                },
                "missing_critical_fields": [],
                "gold_detected": True,
                "gold_path": "sandbox/batch_001/DUPONT_Jean/gold/bilan.docx",
                "sources_count": 5,
                "sources_by_type": {
                    ".docx": 3,
                    ".pdf": 2
                },
                "reasons": [],
                "actions": [],
                "outputs": {
                    "generated_docx": "output/DUPONT_Jean_generated.docx",
                    "debug_json": "output/DUPONT_Jean_debug.json",
                    "metrics_json": "output/DUPONT_Jean_metrics.json",
                    "validation_json": "output/DUPONT_Jean_validation.json"
                }
            },
            {
                "client_name": "MARTIN_Paul",
                "status": "NO_GO",
                "profile": "strict",
                "scores": {
                    "quality_score": 0.58,
                    "required_coverage": 0.65,
                    "weighted_coverage": 0.62,
                    "avg_confidence": 0.55
                },
                "missing_critical_fields": ["nom", "profession_or_formation"],
                "gold_detected": False,
                "gold_path": None,
                "sources_count": 1,
                "sources_by_type": {".pdf": 1},
                "reasons": [
                    "missing_critical_fields: 2 (max: 0)",
                    "missing_fields: nom, profession_or_formation",
                    "low_required_coverage: 0.65 < 0.85"
                ],
                "actions": [
                    "add_identity_sources",
                    "add_sources",
                    "confirm_identity"
                ],
                "outputs": {
                    "generated_docx": "output/MARTIN_Paul_generated.docx",
                    "debug_json": "output/MARTIN_Paul_debug.json",
                    "metrics_json": "output/MARTIN_Paul_metrics.json",
                    "validation_json": "output/MARTIN_Paul_validation.json"
                }
            }
        ]
    }
    
    print("📊 Exemple de structure :")
    print(json.dumps(example_report, indent=2, ensure_ascii=False))
    print()


def demo_batch_report_usage():
    """Montre comment utiliser le batch report."""
    print_section("3. EXPLOITER LE BATCH REPORT")
    
    print("🔍 Filtrer les résultats :")
    print()
    
    print("💻 Code Python :")
    print('''
from pathlib import Path
from src.rhpro.batch_report import load_batch_report, filter_batch_report

# Charger le rapport
report = load_batch_report(Path("output/batch_report.json"))

# Filtrer uniquement les NO_GO
no_go_clients = filter_batch_report(report, status_filter="NO_GO")
print(f"❌ {len(no_go_clients)} clients NO_GO")

for client in no_go_clients:
    print(f"  • {client['client_name']}")
    print(f"    Raisons : {', '.join(client['reasons'])}")
    print(f"    Actions : {', '.join(client['actions'])}")

# Filtrer avec GOLD
gold_clients = filter_batch_report(report, gold_only=True)
print(f"🏆 {len(gold_clients)} clients avec GOLD")

# Combiner filtres : NO_GO avec GOLD
no_go_with_gold = filter_batch_report(
    report,
    status_filter="NO_GO",
    gold_only=True
)
print(f"❌🏆 {len(no_go_with_gold)} clients NO_GO avec GOLD")
''')
    print()


def demo_ui_features():
    """Décrit les fonctionnalités UI."""
    print_section("4. FONCTIONNALITÉS UI (STREAMLIT)")
    
    print("📊 Vue Tableau Batch :")
    print("  ✅ Colonne Status : GO / NO_GO / DRAFT avec icônes")
    print("  💬 Tooltip sur status : affiche les raisons")
    print("  🔍 Filtres :")
    print("     • Par status (Tous / GO / NO_GO / DRAFT)")
    print("     • Uniquement avec GOLD")
    print("     • Recherche par nom de client")
    print("  📥 Exports :")
    print("     • Bouton 'Télécharger batch_report.json'")
    print("     • Bouton 'Télécharger CSV'")
    print()
    
    print("📋 Vue Détail Client (après sélection) :")
    print("  ❌ Bloc 'Pourquoi NO_GO / DRAFT' :")
    print("     • Liste des raisons détaillées")
    print("     • Champs critiques manquants")
    print("  🔧 Bloc 'Actions pour passer GO' :")
    print("     • Actions recommandées avec icônes")
    print("     • Suggestions contextuelles")
    print("  📚 Sources utilisées : comptage par type (.docx, .pdf)")
    print("  📂 Boutons 'Ouvrir' :")
    print("     • Ouvrir DOCX généré")
    print("     • Voir debug.json")
    print("     • Ouvrir GOLD (si détecté)")
    print()


def demo_cli_usage():
    """Montre l'utilisation CLI."""
    print_section("5. UTILISATION CLI")
    
    print("🖥️  Commande CLI :")
    print()
    print("  python -m src.rhpro.batch_report <output_dir> [profile]")
    print()
    
    print("📝 Exemples :")
    print()
    print("  # Profile STRICT (par défaut)")
    print("  python -m src.rhpro.batch_report output strict")
    print()
    print("  # Profile STANDARD")
    print("  python -m src.rhpro.batch_report output standard")
    print()
    print("  # Profile DRAFT")
    print("  python -m src.rhpro.batch_report output draft")
    print()
    
    print("✅ Sortie attendue :")
    print('''
🔍 Validating batch in: output
📋 Profile: STRICT

================================================================================
  BATCH REPORT SUMMARY
================================================================================

📊 Total Clients    : 20
✅ GO               : 14 (70.0%)
❌ NO_GO            : 4
📝 DRAFT            : 2
🏆 GOLD Detected    : 12 (60.0%)

🔍 Top Failure Reasons:
   1. missing_critical_fields (3 clients)
   2. low_required_coverage (2 clients)
   3. insufficient_sources (1 clients)

================================================================================

✅ Batch report saved:
   JSON: output/batch_report.json
   CSV:  output/batch_report.csv
''')
    print()


def demo_csv_analysis():
    """Montre comment analyser le CSV."""
    print_section("6. ANALYSE CSV DANS EXCEL/SHEETS")
    
    print("📊 Le fichier batch_report.csv contient :")
    print()
    print("  • Client")
    print("  • Status (GO / NO_GO / DRAFT)")
    print("  • Profile (strict / standard / draft)")
    print("  • Quality Score")
    print("  • Required Coverage (%)")
    print("  • Weighted Coverage (%)")
    print("  • Avg Confidence")
    print("  • Missing Critical Fields")
    print("  • Gold Detected (Oui / Non)")
    print("  • Sources Count")
    print("  • Sources Types (.docx:3, .pdf:2, ...)")
    print("  • Reasons (pipe-separated)")
    print("  • Actions (pipe-separated)")
    print("  • Generated DOCX (chemin)")
    print("  • Debug JSON (chemin)")
    print("  • Metrics JSON (chemin)")
    print()
    
    print("💡 Cas d'usage :")
    print("  • Trier par Quality Score pour identifier les meilleurs/pires")
    print("  • Filtrer status=NO_GO pour voir les échecs")
    print("  • Analyser les patterns de Missing Critical Fields")
    print("  • Comparer GO vs NO_GO sur Coverage et Confidence")
    print("  • Créer des graphiques (Score vs Coverage, etc.)")
    print()


def main():
    """Point d'entrée principal."""
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "DÉMO : BATCH REPORT DoD" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    
    demo_batch_report_generation()
    demo_batch_report_structure()
    demo_batch_report_usage()
    demo_ui_features()
    demo_cli_usage()
    demo_csv_analysis()
    
    print()
    print("=" * 80)
    print("✅ Démo terminée !")
    print()
    print("📚 Pour plus d'infos, voir :")
    print("   • src/rhpro/batch_report.py : Code source")
    print("   • pages_streamlit/batch_validation.py : Interface UI")
    print("   • python -m src.rhpro.batch_report --help : CLI")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
