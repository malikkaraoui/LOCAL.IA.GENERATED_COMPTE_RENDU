#!/usr/bin/env python3
"""
Démonstration de la couche de validation avec les 3 profils.

Cas d'usage :
1. Validation STRICT pour production RH-Pro
2. Validation STANDARD pour rapports acceptables
3. Validation DRAFT pour brouillons
4. Validation batch avec résumé
"""

import json
from pathlib import Path
from src.rhpro.validation_profiles import (
    validate_report,
    validate_batch,
    get_validation_summary,
    export_validation_report,
    ValidationProfile,
)


def demo_single_validation():
    """Démo : valider un rapport unique avec différents profils."""
    print("=" * 70)
    print("DÉMO 1 : Validation d'un rapport unique")
    print("=" * 70)
    print()
    
    # Créer un metrics.json de test
    test_metrics = {
        "required_coverage": 85,
        "weighted_coverage": 78,
        "quality_score": 0.82,
        "avg_confidence": 0.75,
        "total_fields": 21,
        "filled_fields": 18,
        "required_fields": 10,
        "required_filled": 9,
    }
    
    test_debug = {
        "index": {
            "sources_count": 5,
            "chunks_created": 42,
        },
        "extracted_fields": [
            {"field": "nom", "value": "Dupont"},
            {"field": "prenom", "value": "Jean"},
            {"field": "date_naissance", "value": "15/03/1985"},
            {"field": "situation_professionnelle", "value": "Demandeur d'emploi"},
        ],
    }
    
    # Créer fichiers temporaires
    temp_dir = Path("temp_validation_demo")
    temp_dir.mkdir(exist_ok=True)
    
    metrics_path = temp_dir / "test_metrics.json"
    debug_path = temp_dir / "test_debug.json"
    
    with open(metrics_path, 'w') as f:
        json.dump(test_metrics, f)
    
    with open(debug_path, 'w') as f:
        json.dump(test_debug, f)
    
    # Tester les 3 profils
    for profile in [ValidationProfile.STRICT, ValidationProfile.STANDARD, ValidationProfile.DRAFT]:
        print(f"\n🔍 Profil : {profile.value.upper()}")
        print("-" * 50)
        
        result = validate_report(
            metrics_path=metrics_path,
            debug_path=debug_path,
            profile=profile,
        )
        
        print(f"Status: {result.status}")
        print(f"Quality Score: {result.scores['quality_score']:.2f}")
        print(f"Required Coverage: {result.scores['required_coverage']:.2%}")
        
        if result.reasons:
            print("Reasons:")
            for reason in result.reasons:
                print(f"  ❌ {reason}")
        
        if result.actions:
            print("Actions:")
            for action in result.actions:
                print(f"  🔧 {action}")
    
    # Nettoyer
    import shutil
    shutil.rmtree(temp_dir)
    
    print("\n✅ Démo 1 terminée\n")


def demo_batch_validation():
    """Démo : valider un batch complet."""
    print("=" * 70)
    print("DÉMO 2 : Validation d'un batch")
    print("=" * 70)
    print()
    
    # Créer plusieurs rapports de test
    temp_dir = Path("temp_batch_demo")
    temp_dir.mkdir(exist_ok=True)
    
    clients = [
        {
            "name": "client_excellent",
            "metrics": {
                "required_coverage": 95,
                "weighted_coverage": 92,
                "quality_score": 0.88,
                "avg_confidence": 0.85,
            },
            "debug": {
                "index": {"sources_count": 8, "chunks_created": 64},
                "extracted_fields": [
                    {"field": "nom", "value": "Martin"},
                    {"field": "prenom", "value": "Sophie"},
                    {"field": "date_naissance", "value": "12/08/1990"},
                    {"field": "situation_professionnelle", "value": "En recherche"},
                ],
            },
        },
        {
            "name": "client_moyen",
            "metrics": {
                "required_coverage": 72,
                "weighted_coverage": 68,
                "quality_score": 0.62,
                "avg_confidence": 0.58,
            },
            "debug": {
                "index": {"sources_count": 3, "chunks_created": 18},
                "extracted_fields": [
                    {"field": "nom", "value": "Durand"},
                    {"field": "prenom", "value": "Paul"},
                    {"field": "date_naissance", "value": "Non renseigné"},
                    {"field": "situation_professionnelle", "value": "Salarié"},
                ],
            },
        },
        {
            "name": "client_faible",
            "metrics": {
                "required_coverage": 45,
                "weighted_coverage": 38,
                "quality_score": 0.42,
                "avg_confidence": 0.35,
            },
            "debug": {
                "index": {"sources_count": 1, "chunks_created": 5},
                "extracted_fields": [
                    {"field": "nom", "value": "Non renseigné"},
                    {"field": "prenom", "value": "Non renseigné"},
                ],
            },
        },
    ]
    
    # Créer fichiers
    for client in clients:
        metrics_path = temp_dir / f"{client['name']}_metrics.json"
        debug_path = temp_dir / f"{client['name']}_debug.json"
        
        with open(metrics_path, 'w') as f:
            json.dump(client["metrics"], f)
        
        with open(debug_path, 'w') as f:
            json.dump(client["debug"], f)
    
    # Valider le batch avec profil STANDARD
    print("🔍 Validation du batch (profil STANDARD)...")
    print()
    
    results = validate_batch(temp_dir, profile=ValidationProfile.STANDARD)
    
    for name, result in results.items():
        status_emoji = "✅" if result.status == "GO" else "❌" if result.status == "NO_GO" else "📝"
        print(f"{status_emoji} {name}")
        print(f"   Status: {result.status}")
        print(f"   Quality: {result.scores['quality_score']:.2f}")
        print(f"   Reasons: {', '.join(result.reasons) if result.reasons else 'Aucune'}")
        print()
    
    # Résumé
    summary = get_validation_summary(results)
    
    print("📊 RÉSUMÉ")
    print("-" * 50)
    print(f"Total: {summary['total']}")
    print(f"GO: {summary['go_count']} ({summary['go_rate']:.1%})")
    print(f"NO_GO: {summary['no_go_count']}")
    print(f"DRAFT: {summary['draft_count']}")
    print()
    print("Top reasons:")
    for reason, count in summary["top_reasons"]:
        print(f"  - {reason}: {count}x")
    
    # Export
    export_validation_report(results, temp_dir / "validation_report.json", format="json")
    export_validation_report(results, temp_dir / "validation_report.md", format="markdown")
    
    print()
    print(f"✅ Rapports exportés dans {temp_dir}/")
    
    # Nettoyer
    import shutil
    shutil.rmtree(temp_dir)
    
    print("✅ Démo 2 terminée\n")


def demo_go_no_go_scenarios():
    """Démo : scénarios GO/NO-GO typiques."""
    print("=" * 70)
    print("DÉMO 3 : Scénarios GO/NO-GO")
    print("=" * 70)
    print()
    
    scenarios = [
        {
            "name": "✅ Production Ready (STRICT GO)",
            "profile": ValidationProfile.STRICT,
            "metrics": {
                "required_coverage": 92,
                "weighted_coverage": 88,
                "quality_score": 0.85,
                "avg_confidence": 0.82,
            },
            "debug": {
                "index": {"sources_count": 6, "chunks_created": 48},
                "extracted_fields": [
                    {"field": "nom", "value": "Leclerc"},
                    {"field": "prenom", "value": "Marie"},
                    {"field": "date_naissance", "value": "22/05/1988"},
                    {"field": "situation_professionnelle", "value": "En transition"},
                ],
            },
        },
        {
            "name": "⚠️  Acceptable mais pas optimal (STANDARD GO / STRICT NO-GO)",
            "profile": ValidationProfile.STANDARD,
            "metrics": {
                "required_coverage": 78,
                "weighted_coverage": 72,
                "quality_score": 0.68,
                "avg_confidence": 0.62,
            },
            "debug": {
                "index": {"sources_count": 3, "chunks_created": 22},
                "extracted_fields": [
                    {"field": "nom", "value": "Bernard"},
                    {"field": "prenom", "value": "Luc"},
                    {"field": "date_naissance", "value": "Non renseigné"},
                    {"field": "situation_professionnelle", "value": "Étudiant"},
                ],
            },
        },
        {
            "name": "📝 Brouillon (DRAFT toujours OK)",
            "profile": ValidationProfile.DRAFT,
            "metrics": {
                "required_coverage": 35,
                "weighted_coverage": 28,
                "quality_score": 0.32,
                "avg_confidence": 0.25,
            },
            "debug": {
                "index": {"sources_count": 1, "chunks_created": 8},
                "extracted_fields": [
                    {"field": "nom", "value": "Inconnu"},
                ],
            },
        },
    ]
    
    temp_dir = Path("temp_scenarios_demo")
    temp_dir.mkdir(exist_ok=True)
    
    for i, scenario in enumerate(scenarios):
        print(f"\n{scenario['name']}")
        print("-" * 50)
        
        # Créer fichiers
        metrics_path = temp_dir / f"scenario_{i}_metrics.json"
        debug_path = temp_dir / f"scenario_{i}_debug.json"
        
        with open(metrics_path, 'w') as f:
            json.dump(scenario["metrics"], f)
        
        with open(debug_path, 'w') as f:
            json.dump(scenario["debug"], f)
        
        # Valider
        result = validate_report(
            metrics_path=metrics_path,
            debug_path=debug_path,
            profile=scenario["profile"],
        )
        
        print(f"Profile: {result.profile}")
        print(f"Status: {result.status}")
        print(f"Quality: {result.scores['quality_score']:.2f}")
        print(f"Coverage: {result.scores['required_coverage']:.2%}")
        
        if result.reasons:
            print("Reasons:")
            for reason in result.reasons[:3]:  # Top 3
                print(f"  ❌ {reason}")
        
        if result.actions:
            print("Actions:")
            for action in result.actions[:3]:  # Top 3
                print(f"  🔧 {action}")
    
    # Nettoyer
    import shutil
    shutil.rmtree(temp_dir)
    
    print("\n✅ Démo 3 terminée\n")


def demo_integration_workflow():
    """Démo : intégration dans le workflow complet."""
    print("=" * 70)
    print("DÉMO 4 : Intégration dans le workflow")
    print("=" * 70)
    print()
    
    print("📋 Workflow complet avec validation :")
    print()
    print("1. Scanner batch → detect clients")
    print("2. Normaliser → sandbox/")
    print("3. Générer RAG + DOCX → output/")
    print("4. ⭐ VALIDATION AUTOMATIQUE ⭐")
    print("   ├─ Profil STRICT : production RH-Pro")
    print("   ├─ Profil STANDARD : acceptable")
    print("   └─ Profil DRAFT : brouillon")
    print()
    print("5. UI affiche status :")
    print("   ├─ ✅ GO : rapport validé")
    print("   ├─ ❌ NO_GO : rapport généré mais non validé")
    print("   └─ 📝 DRAFT : brouillon à compléter")
    print()
    print("💡 Points clés :")
    print("  • Le DOCX est TOUJOURS généré (même en NO_GO)")
    print("  • L'UI affiche clairement le statut de validation")
    print("  • Les actions recommandées guident l'utilisateur")
    print("  • En mode DRAFT, rien ne bloque la génération")
    print()
    print("✅ Démo 4 terminée\n")


def main():
    """Lance toutes les démos."""
    print("\n")
    print("*" * 70)
    print("DÉMONSTRATION : COUCHE DE VALIDATION GO/NO-GO")
    print("*" * 70)
    print()
    
    demo_single_validation()
    demo_batch_validation()
    demo_go_no_go_scenarios()
    demo_integration_workflow()
    
    print("*" * 70)
    print("✅ TOUTES LES DÉMOS TERMINÉES")
    print("*" * 70)
    print()
    print("📚 Pour utiliser la validation :")
    print()
    print("from src.rhpro.validation_profiles import validate_report, ValidationProfile")
    print()
    print("result = validate_report(")
    print("    metrics_path=Path('output/client_metrics.json'),")
    print("    debug_path=Path('output/client_debug.json'),")
    print("    profile=ValidationProfile.STRICT,")
    print(")")
    print()
    print("if result.status == 'GO':")
    print("    print('✅ Rapport validé pour production')")
    print("elif result.status == 'NO_GO':")
    print("    print('❌ Rapport non validé :', result.reasons)")
    print("    print('🔧 Actions :', result.actions)")
    print("else:")
    print("    print('📝 Brouillon - à compléter')")
    print()


if __name__ == "__main__":
    main()
