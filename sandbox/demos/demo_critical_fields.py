"""
Démo : Validation des champs critiques RH-Pro

Démontre les nouvelles règles de validation stricte :
1. Champs critiques : nom, prenom, AVS, profession/formation
2. Sources : sources_used >= 1
3. Evidence structurée : evidence.identity.nom[], etc.
4. Règle : no-evidence = no-claim
"""
import json
from pathlib import Path
from src.rhpro.validation_profiles import (
    validate_report,
    ValidationProfile,
    CRITICAL_FIELDS,
    CRITICAL_FIELDS_FLAT,
)

def print_section(title: str):
    """Affiche un titre de section."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()

def demo_critical_fields_definition():
    """Affiche la définition des champs critiques."""
    print_section("1. DÉFINITION DES CHAMPS CRITIQUES RH-PRO")
    
    print("📋 Champs critiques structurés :")
    print()
    for category, fields in CRITICAL_FIELDS.items():
        print(f"  {category.upper()}:")
        for field in fields:
            print(f"    - {field}")
    print()
    
    print("📌 Liste plate (pour compatibilité) :")
    print(f"  {CRITICAL_FIELDS_FLAT}")
    print()
    
    print("🎯 Règles de validation :")
    print("  ✓ Identité : nom + prenom OBLIGATOIRES")
    print("  ✓ AVS : si présent → extraire, sinon 'Non renseigné / à confirmer'")
    print("  ✓ Profession/Formation : AU MOINS l'un des deux doit être renseigné")
    print("  ✓ Sources : sources_used >= 1 (sinon c'est du vide)")
    print("  ✓ Evidence : no-evidence = no-claim")

def demo_mock_validation_scenarios():
    """Démontre différents scénarios de validation."""
    print_section("2. SCÉNARIOS DE VALIDATION")
    
    scenarios = [
        {
            "name": "✅ Rapport VALIDE",
            "metrics": {
                "required_coverage": 85,
                "weighted_coverage": 88,
                "quality_score": 0.80,
                "avg_confidence": 0.75,
            },
            "debug": {
                "fields": {
                    "nom": {
                        "value": "DUPONT",
                        "evidence": [{"source": "CV.pdf", "text": "Jean DUPONT"}],
                    },
                    "prenom": {
                        "value": "Jean",
                        "evidence": [{"source": "CV.pdf", "text": "Jean DUPONT"}],
                    },
                    "numero_avs": {
                        "value": "Non renseigné / à confirmer",
                        "evidence": [],
                    },
                    "situation_professionnelle": {
                        "value": "Conseiller en orientation",
                        "evidence": [{"source": "Entretien.docx", "text": "Conseiller depuis 2020"}],
                    },
                },
                "index": {
                    "sources_count": 3,
                },
            },
            "expected": "GO",
        },
        {
            "name": "❌ Identité manquante",
            "metrics": {
                "required_coverage": 50,
                "weighted_coverage": 55,
                "quality_score": 0.60,
                "avg_confidence": 0.50,
            },
            "debug": {
                "fields": {
                    "nom": {
                        "value": "Non renseigné",
                        "evidence": [],
                    },
                    "prenom": {
                        "value": "Non renseigné",
                        "evidence": [],
                    },
                },
                "index": {
                    "sources_count": 1,
                },
            },
            "expected": "NO_GO",
        },
        {
            "name": "❌ Profession ET Formation manquantes",
            "metrics": {
                "required_coverage": 70,
                "weighted_coverage": 72,
                "quality_score": 0.68,
                "avg_confidence": 0.65,
            },
            "debug": {
                "fields": {
                    "nom": {
                        "value": "MARTIN",
                        "evidence": [{"source": "ID.pdf", "text": "MARTIN Paul"}],
                    },
                    "prenom": {
                        "value": "Paul",
                        "evidence": [{"source": "ID.pdf", "text": "MARTIN Paul"}],
                    },
                    "situation_professionnelle": {
                        "value": "Non renseigné",
                        "evidence": [],
                    },
                    "niveau_formation": {
                        "value": "Non renseigné",
                        "evidence": [],
                    },
                },
                "index": {
                    "sources_count": 2,
                },
            },
            "expected": "NO_GO",
        },
        {
            "name": "❌ Aucune source (vide)",
            "metrics": {
                "required_coverage": 20,
                "weighted_coverage": 25,
                "quality_score": 0.10,
                "avg_confidence": 0.05,
            },
            "debug": {
                "fields": {},
                "index": {
                    "sources_count": 0,
                },
            },
            "expected": "NO_GO",
        },
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"Scénario {i}: {scenario['name']}")
        print(f"  Expected: {scenario['expected']}")
        print(f"  Sources: {scenario['debug']['index']['sources_count']}")
        
        # Afficher les champs
        if scenario['debug'].get('fields'):
            print("  Champs:")
            for field, data in scenario['debug']['fields'].items():
                value = data.get('value', 'N/A')
                has_evidence = len(data.get('evidence', [])) > 0
                evidence_icon = "📄" if has_evidence else "❌"
                print(f"    {evidence_icon} {field}: {value}")
        print()

def demo_evidence_structure():
    """Démontre la structure evidence dans debug.json."""
    print_section("3. STRUCTURE EVIDENCE DANS DEBUG.JSON")
    
    print("🔍 Règle : no-evidence = no-claim")
    print("   Chaque valeur extraite DOIT avoir des preuves traçables.")
    print()
    
    example_evidence = {
        "evidence": {
            "identity": {
                "nom": [
                    {
                        "source": "CV_2024.pdf",
                        "text": "Jean DUPONT - Conseiller en orientation",
                        "score": 0.92
                    }
                ],
                "prenom": [
                    {
                        "source": "CV_2024.pdf",
                        "text": "Jean DUPONT",
                        "score": 0.92
                    }
                ],
                "numero_avs": []  # Pas de preuve = valeur non fiable
            },
            "professional": {
                "situation_professionnelle": [
                    {
                        "source": "Entretien_RH.docx",
                        "text": "Actuellement en poste en tant que Conseiller en orientation depuis 2020",
                        "score": 0.88
                    }
                ],
                "niveau_formation": []  # Doit être marqué "Non renseigné"
            },
            "contact": {
                "email": [
                    {
                        "source": "CV_2024.pdf",
                        "text": "Contact : jean.dupont@example.com",
                        "score": 0.95
                    }
                ]
            }
        }
    }
    
    print("📊 Exemple de structure evidence :")
    print(json.dumps(example_evidence, indent=2, ensure_ascii=False))
    print()
    
    print("✅ Interprétation :")
    print("  • nom + prenom : Preuves présentes → Valeurs fiables")
    print("  • numero_avs : Aucune preuve → Non renseigné (acceptable si explicite)")
    print("  • situation_professionnelle : Preuve présente → Valeur fiable")
    print("  • niveau_formation : Aucune preuve → Doit être 'Non renseigné'")
    print("  • email : Preuve présente → Valeur fiable")

def demo_validation_thresholds():
    """Affiche les seuils de validation par profil."""
    print_section("4. SEUILS DE VALIDATION PAR PROFIL")
    
    from src.rhpro.validation_profiles import PROFILE_THRESHOLDS
    
    for profile, thresholds in PROFILE_THRESHOLDS.items():
        print(f"📊 Profil: {profile.value.upper()}")
        for key, value in thresholds.items():
            print(f"  • {key}: {value}")
        print()

def demo_usage_example():
    """Montre un exemple d'utilisation pratique."""
    print_section("5. EXEMPLE D'UTILISATION")
    
    code = '''from pathlib import Path
from src.rhpro.validation_profiles import validate_report, ValidationProfile

# Valider avec profil STRICT
result = validate_report(
    metrics_path=Path("output/client_metrics.json"),
    debug_path=Path("output/client_debug.json"),
    profile=ValidationProfile.STRICT
)

print(f"Status: {result.status}")  # GO / NO_GO / DRAFT
print(f"Reasons: {result.reasons}")
print(f"Actions: {result.actions}")

# Vérifier champs critiques
if "missing_critical_fields" in str(result.reasons):
    print("⚠️ Champs critiques manquants !")
    
# Vérifier les preuves dans debug.json
with open("output/client_debug.json") as f:
    debug = json.load(f)
    evidence = debug.get("evidence", {})
    
    # Vérifier identité
    if not evidence.get("identity", {}).get("nom"):
        print("❌ Pas de preuve pour le nom !")
'''
    
    print("💻 Code Python :")
    print(code)

def main():
    """Point d'entrée principal."""
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "DÉMO : CHAMPS CRITIQUES RH-PRO" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")
    
    demo_critical_fields_definition()
    demo_mock_validation_scenarios()
    demo_evidence_structure()
    demo_validation_thresholds()
    demo_usage_example()
    
    print()
    print("=" * 80)
    print("✅ Démo terminée !")
    print()
    print("📚 Pour plus d'infos, voir : docs/CRITICAL_FIELDS_RHPRO.md")
    print("=" * 80)
    print()

if __name__ == "__main__":
    main()
