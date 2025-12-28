#!/usr/bin/env python3
"""
Tests anti-régression pour micro-fix NOISE/PII (copilot.md).

Vérifie :
1. Patterns NOISE ne remontent jamais dans unknown_titles
2. Patterns PII ne remontent jamais dans unknown_titles
3. Apostrophes typographiques matchent correctement
4. Zéro impact sur extraction/mapping existants
"""

import sys
from pathlib import Path

# Ajouter src/ au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rhpro.dataset_training import (
    normalize_heading_for_titles,
    is_noise_title,
    is_pii_title,
    match_title_to_canonical,
)


# ============================================================================
# TEST 1 : NOISE patterns ne remontent pas
# ============================================================================

def test_noise_patterns():
    """Test 1 - Patterns NOISE filtrés (copilot.md section 0)"""
    print("\n" + "="*70)
    print("TEST 1 : NOISE PATTERNS - Filtrage complet")
    print("="*70)
    
    noise_inputs = [
        "LES RESULTATS DETAILLES SONT LES SUIVANTS",
        "CI DESSOUS LES RESULTATS DETAILLES",
        "RESULTATS DE LA DISCUSSION AVEC L'ASSURE",  # apostrophe normale
        "RESULTATS DE LA DISCUSSION AVEC L'ASSURE",  # apostrophe typographique
        "TESTS",
        "tests",  # minuscule
        "Tests.",  # avec ponctuation
    ]
    
    failures = []
    for title in noise_inputs:
        normalized = normalize_heading_for_titles(title)
        is_noise = is_noise_title(normalized)
        
        if not is_noise:
            failures.append(f"❌ NOISE non détecté: '{title}' -> '{normalized}'")
            print(f"❌ NOISE non détecté: '{title}' -> '{normalized}'")
        else:
            print(f"✅ NOISE détecté: '{title}' -> '{normalized}'")
    
    if failures:
        print(f"\n❌ TEST 1 ÉCHOUÉ ({len(failures)} erreurs)")
        return False
    else:
        print(f"\n✅ TEST 1 RÉUSSI - {len(noise_inputs)} patterns NOISE filtrés")
        return True


# ============================================================================
# TEST 2 : PII patterns ne remontent jamais
# ============================================================================

def test_pii_patterns():
    """Test 2 - Patterns PII filtrés (copilot.md section 0)"""
    print("\n" + "="*70)
    print("TEST 2 : PII PATTERNS - Zéro tolérance")
    print("="*70)
    
    pii_inputs = [
        "NOM AYNE PRENOM MICKAEL",
        "NOM DUPONT PRENOM JEAN",
        "PRENOM MARIE NOM BERNARD",
        "MONSIEUR MARTIN",
        "MADAME LEFEBVRE",
        "M. DUBOIS",
        "MME ROUSSEAU",
        "MR PETIT",
        "756.1234.5678.90",  # AVS suisse
        "12/03/1985",  # Date
        "NOM: MARTIN PRENOM: ALICE",  # Avec séparateurs
    ]
    
    failures = []
    for title in pii_inputs:
        normalized = normalize_heading_for_titles(title)
        is_pii = is_pii_title(normalized)
        
        if not is_pii:
            failures.append(f"❌ PII non détecté: '{title}' -> '{normalized}'")
            print(f"❌ PII non détecté: '{title}' -> '{normalized}'")
        else:
            print(f"✅ PII détecté: '{title}' (NON STOCKÉ)")
    
    if failures:
        print(f"\n❌ TEST 2 ÉCHOUÉ ({len(failures)} erreurs)")
        return False
    else:
        print(f"\n✅ TEST 2 RÉUSSI - {len(pii_inputs)} patterns PII filtrés (zéro tolérance)")
        return True


# ============================================================================
# TEST 3 : Apostrophes typographiques
# ============================================================================

def test_apostrophe_normalization():
    """Test 3 - Normalisation apostrophes (copilot.md section 4)"""
    print("\n" + "="*70)
    print("TEST 3 : APOSTROPHES TYPOGRAPHIQUES - Normalisation")
    print("="*70)
    
    test_cases = [
        ("RESULTATS DE LA DISCUSSION AVEC L'ASSURE", "RESULTATS DE LA DISCUSSION AVEC L'ASSURE"),
        ("L'ENTREPRISE", "L'ENTREPRISE"),
        ("L`ASSURE", "L'ASSURE"),  # backtick -> apostrophe
        ("d'appui", "D'APPUI"),  # minuscule -> majuscule
    ]
    
    failures = []
    for input_text, expected in test_cases:
        normalized = normalize_heading_for_titles(input_text)
        
        if normalized != expected:
            failures.append(f"❌ '{input_text}' -> '{normalized}' (attendu: '{expected}')")
            print(f"❌ '{input_text}' -> '{normalized}' (attendu: '{expected}')")
        else:
            print(f"✅ '{input_text}' -> '{normalized}'")
    
    # Vérifier que apostrophes normalisées permettent match NOISE
    noise_with_apostrophe = "RESULTATS DE LA DISCUSSION AVEC L'ASSURE"
    normalized = normalize_heading_for_titles(noise_with_apostrophe)
    is_noise = is_noise_title(normalized)
    
    if not is_noise:
        failures.append(f"❌ NOISE avec apostrophe non détecté: '{noise_with_apostrophe}'")
        print(f"❌ NOISE avec apostrophe non détecté: '{noise_with_apostrophe}'")
    else:
        print(f"✅ NOISE avec apostrophe détecté: '{noise_with_apostrophe}'")
    
    if failures:
        print(f"\n❌ TEST 3 ÉCHOUÉ ({len(failures)} erreurs)")
        return False
    else:
        print(f"\n✅ TEST 3 RÉUSSI - Apostrophes normalisées correctement")
        return True


# ============================================================================
# TEST 4 : Zéro impact extraction/mapping
# ============================================================================

def test_zero_impact_on_mapping():
    """Test 4 - Mapping existant inchangé (copilot.md section 6)"""
    print("\n" + "="*70)
    print("TEST 4 : ZÉRO IMPACT EXTRACTION/MAPPING - Préservation")
    print("="*70)
    
    # Titres légitimes qui doivent être mappés (avec canonicals corrects du code)
    # None = titre légitime non mappé actuellement (pas une régression)
    legitimate_titles = [
        ("SITUATION PROFESSIONNELLE", "situation_professionnelle"),
        ("FORMATION", "formation"),
        ("COMPETENCES", "competences"),
        ("OBJECTIFS", "objectifs"),
        ("PISTES METIERS", "pistes_metiers"),
        ("CONTRAINTES ET FREINS", "contraintes_freins"),
        ("MOTIVATIONS", "motivations_valeurs"),
        ("RESSOURCES", None),  # Légitime mais pas mappé actuellement
        ("CONCLUSION", "synthese_conclusion"),
    ]
    
    failures = []
    for title, expected_canonical in legitimate_titles:
        # Vérifier que ce n'est PAS du NOISE ni PII
        normalized = normalize_heading_for_titles(title)
        is_noise = is_noise_title(normalized)
        is_pii = is_pii_title(normalized)
        
        if is_noise:
            failures.append(f"❌ Faux positif NOISE: '{title}' détecté comme noise")
            print(f"❌ Faux positif NOISE: '{title}' détecté comme noise")
            continue
        
        if is_pii:
            failures.append(f"❌ Faux positif PII: '{title}' détecté comme PII")
            print(f"❌ Faux positif PII: '{title}' détecté comme PII")
            continue
        
        # Vérifier mapping
        canonical = match_title_to_canonical(title)
        if canonical != expected_canonical:
            failures.append(f"❌ Mapping incorrect: '{title}' -> '{canonical}' (attendu: '{expected_canonical}')")
            print(f"❌ Mapping incorrect: '{title}' -> '{canonical}' (attendu: '{expected_canonical}')")
        else:
            print(f"✅ Mapping préservé: '{title}' -> '{canonical}'")
    
    if failures:
        print(f"\n❌ TEST 4 ÉCHOUÉ ({len(failures)} erreurs)")
        return False
    else:
        print(f"\n✅ TEST 4 RÉUSSI - {len(legitimate_titles)} mappings préservés (zéro régression)")
        return True


# ============================================================================
# TEST 5 : Edge cases
# ============================================================================

def test_edge_cases():
    """Test 5 - Cas limites"""
    print("\n" + "="*70)
    print("TEST 5 : EDGE CASES - Cas limites")
    print("="*70)
    
    test_cases = [
        # (input, should_be_noise, should_be_pii, description)
        ("", True, False, "Chaîne vide"),
        ("   ", True, False, "Espaces uniquement"),
        ("A", True, False, "1 caractère"),
        ("AB", True, False, "2 caractères"),
        ("ABC", True, False, "3 caractères (trop court)"),
        ("ABCD", False, False, "4 caractères (limite OK)"),
        ("12345", True, False, "Uniquement chiffres"),
        ("....", True, False, "Uniquement ponctuation"),
        ("NOM", True, False, "Libellé formulaire seul"),
        ("PRENOM", True, False, "Libellé formulaire seul"),
        ("RESULTATS", False, False, "Titre légitime partiel"),
        ("DISCUSSION", False, False, "Titre légitime partiel"),
    ]
    
    failures = []
    for input_text, expect_noise, expect_pii, description in test_cases:
        normalized = normalize_heading_for_titles(input_text)
        is_noise = is_noise_title(normalized)
        is_pii = is_pii_title(normalized)
        
        if is_noise != expect_noise:
            failures.append(f"❌ {description}: noise={is_noise} (attendu: {expect_noise})")
            print(f"❌ {description}: '{input_text}' -> noise={is_noise} (attendu: {expect_noise})")
        elif is_pii != expect_pii:
            failures.append(f"❌ {description}: pii={is_pii} (attendu: {expect_pii})")
            print(f"❌ {description}: '{input_text}' -> pii={is_pii} (attendu: {expect_pii})")
        else:
            print(f"✅ {description}: '{input_text}' -> noise={is_noise}, pii={is_pii}")
    
    if failures:
        print(f"\n❌ TEST 5 ÉCHOUÉ ({len(failures)} erreurs)")
        return False
    else:
        print(f"\n✅ TEST 5 RÉUSSI - {len(test_cases)} edge cases validés")
        return True


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "🔬"*35)
    print("TESTS MICRO-FIX NOISE/PII (copilot.md)")
    print("🔬"*35)
    
    results = []
    
    # Exécuter tous les tests
    results.append(("Test 1: NOISE patterns", test_noise_patterns()))
    results.append(("Test 2: PII patterns", test_pii_patterns()))
    results.append(("Test 3: Apostrophes", test_apostrophe_normalization()))
    results.append(("Test 4: Zéro impact mapping", test_zero_impact_on_mapping()))
    results.append(("Test 5: Edge cases", test_edge_cases()))
    
    # Résumé
    print("\n" + "="*70)
    print("RÉSUMÉ DES TESTS")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("="*70)
    
    if passed == total:
        print(f"🎉 TOUS LES TESTS PASSENT ({passed}/{total})")
        print("\nCritères d'acceptation copilot.md validés:")
        print("1. ✅ Patterns NOISE filtrés (4 targets)")
        print("2. ✅ Patterns PII filtrés (11+ targets)")
        print("3. ✅ Apostrophes typographiques normalisées")
        print("4. ✅ Zéro régression sur mappings existants")
        print("5. ✅ Edge cases gérés correctement")
        print("\n🚀 Prêt pour commit et rerun training")
        return 0
    else:
        print(f"❌ {total - passed}/{total} tests échoués")
        print("\n⚠️ CORRECTIFS NÉCESSAIRES")
        return 1


if __name__ == "__main__":
    sys.exit(main())
