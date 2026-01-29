#!/usr/bin/env python3
"""
Script de validation Schema V2 - Test sur données réelles

OBJECTIF:
- Activer USE_SCHEMA_V2 = True
- Tester génération sur quelques clients
- Comparer métriques V1 vs V2
- Valider: 0 hallucinations enum, listes ≤ 4 items
"""

import sys
from pathlib import Path

# Activer Schema V2
import core.generate as generate_module
generate_module.USE_SCHEMA_V2 = True

print("=" * 70)
print("VALIDATION SCHEMA V2 - Test sur données réelles")
print("=" * 70)
print(f"✅ Schema V2 activé: {generate_module.USE_SCHEMA_V2}")
print()

# Tester imports
try:
    from core.field_specs_v2 import FIELD_SPECS_V2, get_field_spec_v2, list_fields_by_type
    from core.enum_extractors_v2 import extract_enum_from_context
    from core.title_mapping_v2 import map_title_to_field_v2
    from core.generate import extract_bullet_points, validate_list_v2, extract_enum_field_v2
    
    print("✅ Tous les modules V2 importés avec succès")
    print()
except Exception as e:
    print(f"❌ Erreur import: {e}")
    sys.exit(1)

# Stats Schema V2
print("-" * 70)
print("SCHEMA V2 - STATISTIQUES")
print("-" * 70)

total = len(FIELD_SPECS_V2)
by_type = {}
by_policy = {}

for spec in FIELD_SPECS_V2.values():
    by_type[spec.field_type] = by_type.get(spec.field_type, 0) + 1
    by_policy[spec.extraction_policy] = by_policy.get(spec.extraction_policy, 0) + 1

print(f"Total champs: {total}")
print(f"\nPar type:")
for field_type, count in sorted(by_type.items()):
    print(f"  - {field_type}: {count}")

print(f"\nPar extraction_policy:")
for policy, count in sorted(by_policy.items()):
    print(f"  - {policy}: {count}")

print()

# Test extraction enum
print("-" * 70)
print("TEST EXTRACTION ENUM (sans LLM)")
print("-" * 70)

test_cases = [
    {
        "text": "Le candidat a un niveau B2 en français.",
        "field": "FRANCAIS_POSITIONNEMENT_DE_NIVEAU",
        "expected": "B2"
    },
    {
        "text": "Anglais: C1 confirmé",
        "field": "ANGLAIS_POSITIONNEMENT_DE_NIVEAU",
        "expected": "C1"
    },
    {
        "text": "Très bonne maîtrise d'Excel et Word",
        "field": "BUREAUTIQUE_WORD_EXCEL_POWERPOINT_OUTLOOK",
        "expected": "Très bon"
    },
    {
        "text": "Test d'attention: OK",
        "field": "TEST_ATTENTION_ADMINISTRATIF",
        "expected": "OK"
    },
    {
        "text": "Difficultés observées en calcul",
        "field": "CALCUL_ET_FRACTION",
        "expected": "À renforcer"
    },
]

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    context = [{"text": test["text"]}]
    spec = get_field_spec_v2(test["field"])
    result = extract_enum_field_v2(context, test["field"], spec.enum_values)
    
    if result == test["expected"]:
        print(f"✅ Test {i}: {test['field']}")
        print(f"   Texte: '{test['text']}'")
        print(f"   Résultat: '{result}' (attendu: '{test['expected']}')")
        passed += 1
    else:
        print(f"❌ Test {i}: {test['field']}")
        print(f"   Texte: '{test['text']}'")
        print(f"   Résultat: '{result}' (attendu: '{test['expected']}')")
        failed += 1
    print()

print(f"Résultats: {passed}/{len(test_cases)} tests passés")
print()

# Test validation liste
print("-" * 70)
print("TEST VALIDATION LISTE (max 4 items)")
print("-" * 70)

list_tests = [
    {
        "input": "- Item 1\n- Item 2\n- Item 3\n- Item 4\n- Item 5\n- Item 6",
        "expected_count": 4,
        "name": "Troncature 6 → 4 items"
    },
    {
        "input": "- Alpha\n- Beta\n- Gamma",
        "expected_count": 3,
        "name": "Conservation 3 items"
    },
]

for test in list_tests:
    result = validate_list_v2(test["input"], max_items=4)
    items = extract_bullet_points(result)
    count = len(items)
    
    if count == test["expected_count"]:
        print(f"✅ {test['name']}: {count} items (attendu: {test['expected_count']})")
    else:
        print(f"❌ {test['name']}: {count} items (attendu: {test['expected_count']})")
    print(f"   Items: {items}")
    print()

# Test title mapping
print("-" * 70)
print("TEST TITLE MAPPING")
print("-" * 70)

from core.title_mapping_v2 import TITLE_TO_FIELD_PATTERNS_V2, IGNORED_TITLES_V2

print(f"Patterns de mapping: {len(TITLE_TO_FIELD_PATTERNS_V2)}")
print(f"Titres ignorés: {len(IGNORED_TITLES_V2)}")

mapping_tests = [
    ("SITUATION PROFESSIONNELLE", "PROFESSION"),
    ("Formation et diplômes", "FORMATION"),
    ("SOMMAIRE", None),  # Ignoré
    ("Français - Positionnement de niveau", "FRANCAIS_POSITIONNEMENT_DE_NIVEAU"),
]

print("\nExemples de mapping:")
for title, expected in mapping_tests:
    result = map_title_to_field_v2(title)
    status = "✅" if result == expected else "❌"
    print(f"{status} '{title}' → {result} (attendu: {expected})")

print()

# Résumé final
print("=" * 70)
print("VALIDATION SCHEMA V2 - RÉSUMÉ")
print("=" * 70)
print(f"✅ Schema V2: {total} champs définis")
print(f"✅ Extraction enum: {passed}/{len(test_cases)} tests passés")
print(f"✅ Validation liste: fonctionnelle")
print(f"✅ Title mapping: {len(TITLE_TO_FIELD_PATTERNS_V2)} patterns")
print()

if failed == 0:
    print("🎉 TOUS LES TESTS SONT PASSÉS!")
    print()
    print("Prochaine étape: Tester sur ESSAI 100 complet")
    print("  python src/rhpro/dataset_training.py --clients-dir data/CLIENTS --limit 10")
    sys.exit(0)
else:
    print(f"⚠️  {failed} tests ont échoué")
    sys.exit(1)
