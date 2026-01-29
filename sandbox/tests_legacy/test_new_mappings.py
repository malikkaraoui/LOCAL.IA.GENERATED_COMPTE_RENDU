#!/usr/bin/env python3
"""Test des nouveaux mappings et filtres is_noise_heading."""

from src.rhpro.dataset_training import (
    SEED_SECTION_TITLE_MAP,
    is_noise_heading,
    normalize_title
)

print("=" * 70)
print("TEST 1: Nouveaux mappings")
print("=" * 70)

# Titres qui doivent être mappés
test_mappings = {
    "INCERTITUDES & OBSTACLES": "contraintes_freins",
    "STAGE EN LAI 15": "situation_professionnelle",
    "DIFFICULTEES RENCONTREES": "contraintes_freins",
    "SELON L EVALUATION DE STAGE FINALE LES TACHES REALISEES ONT ETE LES SUIVANTES": "competences",
    "VOCATIO": "pistes_metiers",
    "TEST EVOLUTION": "motivations_valeurs",
    "RELATION AU MARCHE DE L EMPLOI": "objectifs",
    "PROFESSION": "situation_professionnelle",
}

for title, expected_section in test_mappings.items():
    normalized = normalize_title(title)
    mapped = SEED_SECTION_TITLE_MAP.get(normalized)
    
    if mapped == expected_section:
        print(f"✅ {title[:50]:50} → {mapped}")
    else:
        print(f"❌ {title[:50]:50} → {mapped} (attendu: {expected_section})")

print("\n" + "=" * 70)
print("TEST 2: Filtrage NOISE")
print("=" * 70)

# Titres qui doivent être filtrés comme noise
noise_titles = [
    "LES RESULTATS DETAILLES SONT LES SUIVANTS",
    "CI DESSOUS LES RESULTATS DETAILLES",
    "RESULTATS DE LA DISCUSSION AVEC L ASSURE",
    "TESTS",
]

for title in noise_titles:
    is_noise = is_noise_heading(title)
    status = "✅" if is_noise else "❌"
    print(f"{status} {title:50} → noise={is_noise}")

print("\n" + "=" * 70)
print("TEST 3: Filtrage PII")
print("=" * 70)

# Titres avec PII qui doivent être filtrés
pii_titles = [
    "NOM DUPONT PRENOM JEAN",
    "LES MOTIVATEURS PRINCIPAUX DE MONSIEUR MARTIN SONT",
    "MADAME DURAND A EXPRIME",
    "NOM ... PRENOM ...",
    "MONSIEUR X EST",
]

for title in pii_titles:
    is_noise = is_noise_heading(title)
    status = "✅" if is_noise else "❌"
    print(f"{status} {title:50} → PII filtré={is_noise}")

print("\n" + "=" * 70)
print("TEST 4: Titres légitimes (ne doivent PAS être filtrés)")
print("=" * 70)

# Titres normaux qui NE doivent PAS être filtrés
legit_titles = [
    "COMPETENCES",
    "SITUATION PROFESSIONNELLE",
    "OBJECTIFS PROFESSIONNELS",
    "FORMATION ET PARCOURS",
]

for title in legit_titles:
    is_noise = is_noise_heading(title)
    status = "✅" if not is_noise else "❌"
    print(f"{status} {title:50} → noise={is_noise} (doit être False)")

print("\n" + "=" * 70)
print("✅ TESTS TERMINÉS")
print("=" * 70)
