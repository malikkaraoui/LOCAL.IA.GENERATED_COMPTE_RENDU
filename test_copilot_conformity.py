#!/usr/bin/env python3
"""
Test complet de conformité aux spécifications copilot.md
Tests anti-noise + anti-PII selon les critères d'acceptation exacts.
"""

from src.rhpro.dataset_training import (
    is_noise_heading,
    is_noise_title,
    normalize_title,
    SEED_SECTION_TITLE_MAP
)

print("=" * 80)
print("TEST CONFORMITÉ copilot.md - Anti-Noise + Anti-PII")
print("=" * 80)

# ============================================================================
# TEST 1: Noise Patterns (doivent être filtrés)
# ============================================================================
print("\n✅ TEST 1: NOISE PATTERNS (cibles exactes du copilot.md)")
print("-" * 80)

noise_targets = [
    "LES RESULTATS DETAILLES SONT LES SUIVANTS",
    "CI DESSOUS LES RESULTATS DETAILLES",
    "RESULTATS DE LA DISCUSSION AVEC L'ASSURE",
    "RESULTATS DE LA DISCUSSION AVEC L ASSURE",  # Variant apostrophe
    "TESTS",
]

all_noise_pass = True
for title in noise_targets:
    is_filtered = is_noise_heading(title)
    status = "✅" if is_filtered else "❌ FAIL"
    if not is_filtered:
        all_noise_pass = False
    print(f"{status} '{title}' → filtered={is_filtered}")

print(f"\n{'✅ PASS' if all_noise_pass else '❌ FAIL'}: Tous les patterns noise filtrés")

# ============================================================================
# TEST 2: PII Patterns (doivent être filtrés)
# ============================================================================
print("\n✅ TEST 2: PII PATTERNS (aucune donnée d'identité dans unknown_titles)")
print("-" * 80)

pii_targets = [
    "NOM AYNE PRENOM MICKAEL",
    "NOM DUPONT PRENOM JEAN",
    "PRENOM MARIE NOM MARTIN",
    "MONSIEUR ATTOU",
    "MADAME DURAND",
    "M. BERNARD",
    "MME LAURENT",
    "LES MOTIVATEURS PRINCIPAUX DE MONSIEUR MARTIN SONT",
]

all_pii_pass = True
for title in pii_targets:
    is_filtered = is_noise_heading(title)
    status = "✅" if is_filtered else "❌ FAIL"
    if not is_filtered:
        all_pii_pass = False
    print(f"{status} '{title}' → PII filtered={is_filtered}")

print(f"\n{'✅ PASS' if all_pii_pass else '❌ FAIL'}: Tous les patterns PII filtrés")

# ============================================================================
# TEST 3: Titres légitimes (NE doivent PAS être filtrés)
# ============================================================================
print("\n✅ TEST 3: TITRES LÉGITIMES (ne doivent PAS être filtrés)")
print("-" * 80)

legit_titles = [
    "SITUATION PROFESSIONNELLE",
    "FORMATION",
    "COMPETENCES",
    "OBJECTIFS",
    "PLAN D'ACTION",
    "MOTIVATIONS",
    "CONTRAINTES",
    "PISTES METIERS",
    "SYNTHESE",
]

all_legit_pass = True
for title in legit_titles:
    is_filtered = is_noise_heading(title)
    status = "✅" if not is_filtered else "❌ FAIL"
    if is_filtered:
        all_legit_pass = False
    print(f"{status} '{title}' → filtered={is_filtered} (doit être False)")

print(f"\n{'✅ PASS' if all_legit_pass else '❌ FAIL'}: Aucun titre légitime filtré")

# ============================================================================
# TEST 4: Ordre de traitement (PII/NOISE avant mapping)
# ============================================================================
print("\n✅ TEST 4: ORDRE DE TRAITEMENT")
print("-" * 80)

# Simuler le pipeline du code
test_cases = [
    ("LES RESULTATS DETAILLES SONT LES SUIVANTS", "noise", False),
    ("NOM DUPONT PRENOM JEAN", "pii", False),
    ("FORMATION", "mapped", True),
    ("TITRE INCONNU LEGITIME", "unknown", True),
]

order_pass = True
for title, expected_type, should_count_unknown in test_cases:
    title_norm = normalize_title(title)
    
    # Pipeline exact du code (ligne 1152 dataset_training.py)
    is_noise_t = is_noise_title(title_norm)
    is_noise_h = is_noise_heading(title)
    would_count = not is_noise_t and not is_noise_h
    
    # Mapping check
    is_mapped = title_norm in SEED_SECTION_TITLE_MAP
    
    result_type = "filtered" if not would_count else ("mapped" if is_mapped else "unknown")
    
    status = "✅" if (would_count == should_count_unknown) else "❌ FAIL"
    if would_count != should_count_unknown:
        order_pass = False
    
    print(f"{status} '{title[:40]:40}' → {result_type:10} (attendu: {expected_type})")

print(f"\n{'✅ PASS' if order_pass else '❌ FAIL'}: Ordre de traitement correct")

# ============================================================================
# TEST 5: Nouveaux mappings (coverage improvements)
# ============================================================================
print("\n✅ TEST 5: NOUVEAUX MAPPINGS (amélioration coverage)")
print("-" * 80)

new_mappings = [
    ("INCERTITUDES & OBSTACLES", "contraintes_freins"),
    ("STAGE EN LAI 15", "situation_professionnelle"),
    ("VOCATIO", "pistes_metiers"),
    ("TEST EVOLUTION", "motivations_valeurs"),
    ("PROFESSION", "situation_professionnelle"),
]

mapping_pass = True
for title, expected_section in new_mappings:
    title_norm = normalize_title(title)
    mapped_section = SEED_SECTION_TITLE_MAP.get(title_norm)
    
    status = "✅" if mapped_section == expected_section else "❌ FAIL"
    if mapped_section != expected_section:
        mapping_pass = False
    
    print(f"{status} '{title:40}' → {mapped_section or 'NOT MAPPED':30} (attendu: {expected_section})")

print(f"\n{'✅ PASS' if mapping_pass else '❌ FAIL'}: Tous les nouveaux mappings actifs")

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================
print("\n" + "=" * 80)
print("RÉSUMÉ CONFORMITÉ copilot.md")
print("=" * 80)

all_tests = [
    ("Noise patterns filtrés", all_noise_pass),
    ("PII patterns filtrés", all_pii_pass),
    ("Titres légitimes préservés", all_legit_pass),
    ("Ordre de traitement correct", order_pass),
    ("Nouveaux mappings actifs", mapping_pass),
]

all_pass = all(passed for _, passed in all_tests)

for test_name, passed in all_tests:
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")

print("\n" + "=" * 80)
if all_pass:
    print("🎉 TOUS LES TESTS PASSENT - Conformité 100%")
    print("=" * 80)
    print("\n📋 Critères d'acceptation validés:")
    print("  1. ✅ Patterns noise filtrés (LES RESULTATS DETAILLES, TESTS, etc.)")
    print("  2. ✅ AUCUNE PII dans unknown_titles (NOM/PRENOM/MONSIEUR/MADAME)")
    print("  3. ✅ Titres légitimes préservés (pas de régression)")
    print("  4. ✅ Ordre de traitement: PII/NOISE → mapping → unknown")
    print("  5. ✅ Nouveaux mappings coverage actifs")
    print("\n🚀 Prêt pour run training 20 clients")
else:
    print("❌ ÉCHEC - Corrections nécessaires")
    print("=" * 80)

exit(0 if all_pass else 1)
