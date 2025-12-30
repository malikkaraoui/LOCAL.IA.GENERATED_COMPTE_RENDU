"""
Mapping V2: Titres de sections → Champs V2

OBJECTIF: Simplifier le mapping de ~25 sections vers 39 champs
- Plus de sections canoniques multiples
- Mapping direct titre → champ
- IGNORED_TITLES pour supprimer bruit admin

USAGE:
    from core.title_mapping_v2 import map_title_to_field_v2
    field = map_title_to_field_v2("SITUATION PROFESSIONNELLE")
    # → "PROFESSION"
"""

import re
import unicodedata
from typing import Optional


# ============================================================================
# A) TITRES IGNORÉS (bruit administratif)
# ============================================================================

IGNORED_TITLES_V2 = [
    # Déjà dans dataset_training.py, consolidation ici
    "PARTICIPATION AU PROGRAMME",
    "A L'ATTENTION DE",
    "A L ATTENTION DE",
    "LIEU ET DATE",
    "OFFICE CANTONAL DES ASSURANCES SOCIALES OCAS",
    "OFFICE CANTONAL DES ASSURANCES SOCIALES",
    "OCAS",
    "ASSURANCE INVALIDITE",
    "SERVICE DE L ASSURANCE INVALIDITE",
    "REPUBLIQUE ET CANTON",
    "DEPARTEMENT DE LA SECURITE",
    "EN TETE ADMINISTRATIF",
    
    # Ajouts V2
    "SOMMAIRE",
    "TABLE DES MATIERES",
    "PAGE",
    "DATE",
    "SIGNATURE",
]


def normalize_title_v2(title: str) -> str:
    """
    Normalise un titre pour mapping.
    
    Args:
        title: Titre brut
        
    Returns:
        Titre normalisé (minuscules, sans accents, espaces → _)
    """
    if not title:
        return ""
    
    # Supprimer accents
    text = unicodedata.normalize('NFKD', title)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    
    # Minuscules, espaces → underscores
    text = text.lower().strip()
    text = re.sub(r'\s+', '_', text)
    
    # Supprimer caractères spéciaux
    text = re.sub(r'[^\w_]', '', text)
    
    return text


def is_ignored_title_v2(title: str) -> bool:
    """
    Vérifie si un titre doit être ignoré.
    
    Args:
        title: Titre à tester
        
    Returns:
        True si à ignorer
    """
    if not title:
        return True
    
    title_norm = normalize_title_v2(title)
    
    for ignored in IGNORED_TITLES_V2:
        ignored_norm = normalize_title_v2(ignored)
        if ignored_norm in title_norm or title_norm in ignored_norm:
            return True
    
    return False


# ============================================================================
# B) MAPPING TITRE → CHAMP V2
# ============================================================================

# Patterns de mapping (ordre de priorité)
TITLE_TO_FIELD_PATTERNS_V2 = [
    # NARRATIVES
    (r'.*profession.*|.*parcours.*professionnel.*|.*situation.*professionnel.*', 'PROFESSION'),
    (r'.*formation.*|.*diplome.*|.*etude.*|.*scolarite.*', 'FORMATION'),
    (r'.*discussion.*assure.*|.*entretien.*assure.*|.*echange.*assure.*', 'DISCUSSION_ASSURE'),
    (r'.*competence.*sociale.*|.*savoir.*etre.*|.*soft.*skill.*', 'COMPETENCES_SOCIALES'),
    (r'.*competence.*pro.*|.*competence.*technique.*|.*savoir.*faire.*', 'COMPETENCES_PRO'),
    (r'.*obstacle.*|.*frein.*|.*difficulte.*|.*problematique.*', 'OBSTACLES'),
    (r'.*orientation.*|.*piste.*metier.*|.*projet.*professionnel.*', 'ORIENTATION'),
    (r'.*stage.*|.*immersion.*|.*bilan.*stage.*', 'STAGE'),
    (r'.*presentation.*|.*profil.*|.*synthese.*profil.*', 'PRESENTATION'),
    (r'.*entretien.*|.*preparation.*entretien.*|.*simulation.*entretien.*', 'ENTRETIEN'),
    (r'.*conclusion.*|.*synthese.*|.*bilan.*general.*', 'CONCLUSION'),
    (r'.*lettre.*motivation.*', 'LETTRE_DE_MOTIVATION'),
    (r'.*cv.*|.*curriculum.*vitae.*', 'CV'),
    
    # LISTES
    (r'.*ressource.*comportement.*|.*point.*vigilance.*', 
     'RESSOURCES_COMPORTEMENTALES_POINTS_DE_VIGILANCE'),
    (r'.*ressource.*motivation.*|.*motivation.*', 'RESSOURCES_MOTIVATIONNELLES'),
    (r'.*relation.*marche.*emploi.*|.*rapport.*emploi.*', 'RELATION_AU_MARCHE_DE_LEMPLOI'),
    (r'.*contexte.*organisation.*|.*role.*privilegie.*', 
     'CONTEXTE_ORGANISATION_PRIVILEGIEE_ET_ROLE_PRIVILEGIE'),
    (r'.*secteur.*privilegie.*|.*secteur.*activite.*', 'SECTEURS_PRIVILEGIES'),
    (r'.*metier.*privilegie.*|.*metier.*envisageable.*|.*fonction.*privilegie.*', 
     'METIERS_PRIVILEGIES_ENVISAGEABLES'),
    
    # TESTS/ÉVALUATIONS (listes)
    (r'.*vocatio.*', 'VOCATIO'),
    (r'.*domaine.*professionnel.*exemple.*|.*domaine.*interet.*', 
     'DOMAINES_PROFESSIONNELS_EXEMPLES'),
    (r'.*riasec.*|.*correspondance.*score.*', 'RIASEC_CORRESPONDANCE_SCORE'),
    (r'.*formation.*test.*|.*test.*formation.*|.*bilan.*formation.*', 'FORMATIONS_TESTS'),
    
    # ENUM LANGUES
    (r'.*francais.*positionnement.*niveau.*|.*niveau.*francais.*', 
     'FRANCAIS_POSITIONNEMENT_DE_NIVEAU'),
    (r'.*anglais.*positionnement.*niveau.*|.*niveau.*anglais.*', 
     'ANGLAIS_POSITIONNEMENT_DE_NIVEAU'),
    (r'.*allemand.*positionnement.*niveau.*|.*niveau.*allemand.*', 
     'ALLEMAND_POSITIONNEMENT_DE_NIVEAU'),
    
    # ENUM BUREAUTIQUE
    (r'.*bureautique.*|.*word.*excel.*|.*office.*|.*informatique.*', 
     'BUREAUTIQUE_WORD_EXCEL_POWERPOINT_OUTLOOK'),
    
    # ENUM TESTS
    (r'.*test.*attention.*administratif.*', 'TEST_ATTENTION_ADMINISTRATIF'),
    (r'.*calcul.*niveau.*', 'CALCUL_NIVEAU'),
    (r'.*calcul.*fraction.*', 'CALCUL_ET_FRACTION'),
    (r'.*dimension.*volume.*mesure.*', 'DIMENSIONS_VOLUMES_ET_MESURES'),
    (r'.*test.*comptabilite.*|.*niveau.*comptabilite.*', 'TEST_NIVEAU_COMPTABILITE'),
    (r'.*test.*comprehension.*consigne.*|.*comprehension.*consigne.*', 
     'TEST_COMPREHENSION_DE_CONSIGNES'),
    (r'.*test.*saisie.*commande.*|.*saisie.*commande.*', 'TEST_SAISIE_DE_COMMANDES'),
]


def map_title_to_field_v2(title: str) -> Optional[str]:
    """
    Mappe un titre de section vers un champ V2.
    
    Args:
        title: Titre de section
        
    Returns:
        Champ V2 ou None si pas de mapping
        
    Examples:
        >>> map_title_to_field_v2("SITUATION PROFESSIONNELLE")
        'PROFESSION'
        >>> map_title_to_field_v2("Formation et diplômes")
        'FORMATION'
        >>> map_title_to_field_v2("SOMMAIRE")
        None  # Ignoré
    """
    if not title:
        return None
    
    # Vérifier si ignoré
    if is_ignored_title_v2(title):
        return None
    
    # Normaliser
    title_norm = normalize_title_v2(title)
    
    # Chercher pattern
    for pattern, field_key in TITLE_TO_FIELD_PATTERNS_V2:
        if re.match(pattern, title_norm, re.IGNORECASE):
            return field_key
    
    return None


# ============================================================================
# C) STATS & DEBUG
# ============================================================================

def get_mapping_stats() -> dict:
    """Stats du mapping V2"""
    fields_mapped = set(field for _, field in TITLE_TO_FIELD_PATTERNS_V2)
    
    return {
        "total_patterns": len(TITLE_TO_FIELD_PATTERNS_V2),
        "unique_fields_mapped": len(fields_mapped),
        "ignored_titles_count": len(IGNORED_TITLES_V2),
        "fields_mapped": sorted(fields_mapped),
    }


def test_mappings():
    """Tests rapides du mapping"""
    test_cases = [
        ("SITUATION PROFESSIONNELLE", "PROFESSION"),
        ("Formation et diplômes", "FORMATION"),
        ("Résultats de la discussion avec l'assuré", "DISCUSSION_ASSURE"),
        ("Compétences sociales", "COMPETENCES_SOCIALES"),
        ("Obstacles et freins", "OBSTACLES"),
        ("Pistes métiers", "ORIENTATION"),
        ("Bilan de stage", "STAGE"),
        ("Français - Positionnement de niveau", "FRANCAIS_POSITIONNEMENT_DE_NIVEAU"),
        ("Test d'attention administratif", "TEST_ATTENTION_ADMINISTRATIF"),
        ("SOMMAIRE", None),  # Ignoré
        ("A L'ATTENTION DE", None),  # Ignoré
    ]
    
    print("Tests de mapping:")
    for title, expected in test_cases:
        result = map_title_to_field_v2(title)
        status = "✅" if result == expected else "❌"
        print(f"{status} {title:50} → {result or '(ignoré)'}")


if __name__ == "__main__":
    import json
    
    print("=== STATS MAPPING V2 ===")
    stats = get_mapping_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    print("\n=== TESTS ===")
    test_mappings()
