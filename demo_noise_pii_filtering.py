#!/usr/bin/env python3
"""
Test rapide de démonstration des filtres NOISE/PII

Montre que les patterns NOISE et PII sont correctement filtrés.
"""
from src.rhpro.dataset_training import (
    is_noise_title,
    is_pii_title,
    normalize_heading_for_titles,
)


def demo_noise_filtering():
    """Démonstration du filtrage NOISE"""
    print("=" * 70)
    print("🔍 DÉMONSTRATION : Filtrage NOISE")
    print("=" * 70)
    print()
    
    # Patterns NOISE qui doivent être filtrés
    noise_titles = [
        "LES RESULTATS DETAILLES SONT LES SUIVANTS",
        "CI DESSOUS LES RESULTATS DETAILLES",
        "RESULTATS DE LA DISCUSSION AVEC L'ASSURE",  # apostrophe typographique
        "TESTS",
        "NOM",  # label formulaire
        "PRENOM",
        "AVS",
        "SIGNATURE",
        "I",  # chiffre romain
        "II",
        "A",  # lettre seule
    ]
    
    filtered = 0
    for title in noise_titles:
        if is_noise_title(title):
            print(f"✅ FILTRÉ : {title}")
            filtered += 1
        else:
            print(f"❌ NON FILTRÉ (ERREUR) : {title}")
    
    print()
    print(f"📊 Total : {filtered}/{len(noise_titles)} patterns NOISE filtrés")
    print()


def demo_pii_filtering():
    """Démonstration du filtrage PII"""
    print("=" * 70)
    print("🔒 DÉMONSTRATION : Filtrage PII (v2 avec ':')")
    print("=" * 70)
    print()
    
    # Patterns PII qui doivent être filtrés
    pii_titles = [
        "NOM DUPONT PRENOM JEAN",
        "PRENOM MARIE NOM MARTIN",
        "NOM : DUPONT PRENOM : JEAN",  # v2: avec ":"
        "NOM: X PRENOM: Y",  # v2: avec ":"
        "NOM- MARTIN / PRENOM- SOPHIE",  # v2: avec "-" et "/"
        "MONSIEUR DUPONT",
        "MADAME LEFEBVRE",
        "M. DUBOIS",
        "MME ROUSSEAU",
        "AVS 756.1234.5678.90",
        "DATE 15/03/2024",
        "TEL 0223456789",  # >= 6 chiffres
    ]
    
    filtered = 0
    for title in pii_titles:
        if is_pii_title(title):
            print(f"✅ FILTRÉ : {title}")
            filtered += 1
        else:
            print(f"❌ NON FILTRÉ (ERREUR) : {title}")
    
    print()
    print(f"📊 Total : {filtered}/{len(pii_titles)} patterns PII filtrés")
    print()


def demo_valid_titles():
    """Démonstration : titres valides NON filtrés"""
    print("=" * 70)
    print("✅ DÉMONSTRATION : Titres valides NON filtrés")
    print("=" * 70)
    print()
    
    # Titres légitimes qui NE doivent PAS être filtrés
    valid_titles = [
        "FORMATION",
        "COMPETENCES PROFESSIONNELLES",
        "EXPERIENCE DE TRAVAIL",
        "RESSOURCES COMPORTEMENTALES",
        "OBJECTIFS PROFESSIONNELS",
        "SITUATION ACTUELLE",
        "SYNTHESE",
        "CONCLUSION",
        "PROJET PROFESSIONNEL",
        "BILAN DE STAGE",
    ]
    
    not_filtered = 0
    for title in valid_titles:
        is_noise = is_noise_title(title)
        is_pii = is_pii_title(title)
        
        if not is_noise and not is_pii:
            print(f"✅ OK : {title}")
            not_filtered += 1
        else:
            print(f"❌ FILTRÉ (RÉGRESSION) : {title} (noise={is_noise}, pii={is_pii})")
    
    print()
    print(f"📊 Total : {not_filtered}/{len(valid_titles)} titres valides préservés")
    print()


def demo_normalization():
    """Démonstration de la normalisation (apostrophes typographiques + accents)"""
    print("=" * 70)
    print("🔧 DÉMONSTRATION : Normalisation (apostrophes + accents - v2)")
    print("=" * 70)
    print()
    
    # Variantes avec apostrophes différentes ET accents
    variants = [
        "RÉSULTATS DE LA DISCUSSION AVEC L'ASSURÉ",  # accents + apostrophe courbe droite '
        "RESULTATS DE LA DISCUSSION AVEC L'ASSURE",  # apostrophe normale '
        "résultats de la discussion avec l'assuré",  # casse différente + accents
        "  RÉSULTATS DE LA DISCUSSION AVEC L'ASSURÉ...  ",  # espaces + ponctuation + accents
    ]
    
    print("Toutes ces variantes doivent être normalisées en :")
    print('→ "RESULTATS DE LA DISCUSSION AVEC L\'ASSURE"')
    print()
    
    for variant in variants:
        normalized = normalize_heading_for_titles(variant)
        is_noise = is_noise_title(variant)
        
        print(f"Input    : {repr(variant)}")
        print(f"Normalized: {repr(normalized)}")
        print(f"Is NOISE  : {'✅ OUI' if is_noise else '❌ NON'}")
        print()
    
    # Vérification finale
    expected = "RESULTATS DE LA DISCUSSION AVEC L'ASSURE"
    all_correct = all(normalize_heading_for_titles(v) == expected for v in variants)
    all_noise = all(is_noise_title(v) for v in variants)
    
    if all_correct and all_noise:
        print("✅ SUCCÈS : Toutes les variantes sont correctement normalisées et filtrées")
    else:
        print("❌ ÉCHEC : Certaines variantes ne sont pas correctement traitées")
    print()


def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "TEST DÉMONSTRATION MICRO-FIX NOISE/PII" + " " * 15 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    demo_noise_filtering()
    demo_pii_filtering()
    demo_valid_titles()
    demo_normalization()
    
    print("=" * 70)
    print("✅ DÉMONSTRATION TERMINÉE")
    print("=" * 70)
    print()
    print("👉 Pour valider sur des données réelles, lancer :")
    print("   python validate_v4_1.py")
    print()


if __name__ == "__main__":
    main()
