"""
Title Rules — Règles regex pour classifier les titres inconnus

Ce module fournit un fallback regex pour les titres qui n'ont pas été mappés
par la méthode exacte (section_title_map). Les règles sont ordonnées par 
priorité et appliquées sur les titres NORMALISÉS (uppercase, sans accents/ponctuation).

Ordre de résolution d'un titre :
1. Normalisation du titre brut via normalize_title()
2. Mapping exact via section_title_map
3. **Règles regex** (ce module) - fallback
4. Si aucune règle ne match → unknown_title
"""
import re
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


# Règles ordonnées : (pattern_regex, section_canonique, description)
# Les patterns sont appliqués sur le titre NORMALISÉ (uppercase, sans accents)
# La première règle qui match gagne
TITLE_RULES: List[Tuple[str, str, str]] = [
    # FRANÇAIS - tests de positionnement/niveau
    (
        r'^FRANCAIS\b.*\b(POSITIONNEMENT|NIVEAU)\b',
        'tests',
        'Tests de français (positionnement/niveau)'
    ),
    
    # CALCUL - tests avec niveau numérique
    (
        r'^CALCUL\b.*\bNIVEAU\s*\d',
        'tests',
        'Tests de calcul avec niveau numérique'
    ),
    
    # ANGLAIS - tests de positionnement
    (
        r'^ANGLAIS\b.*\bPOSITIONNEMENT\b',
        'tests',
        'Tests d\'anglais (positionnement)'
    ),
    
    # ALLEMAND - tests de positionnement
    (
        r'^ALLEMAND\b.*\bPOSITIONNEMENT\b',
        'tests',
        'Tests d\'allemand (positionnement)'
    ),
    
    # TRI - classement
    (
        r'^TRI\b.*\bCLASSEMENT\b',
        'tests',
        'Tests de tri/classement'
    ),
    
    # SAISIE - commandes
    (
        r'^SAISIE\b.*\bCOMMANDES\b',
        'tests',
        'Tests de saisie de commandes'
    ),
    
    # DIMENSIONS - volumes/mesures
    (
        r'^DIMENSIONS\b.*\b(VOLUMES|MESURES)\b',
        'tests',
        'Tests de dimensions/volumes/mesures'
    ),
]


# Patterns compilés (cache)
_compiled_rules: Optional[List[Tuple[re.Pattern, str, str]]] = None


def compile_title_rules() -> List[Tuple[re.Pattern, str, str]]:
    """
    Compile les regex une seule fois pour la performance.
    
    Returns:
        Liste de (pattern_compilé, section_canonique, description)
    """
    global _compiled_rules
    
    if _compiled_rules is None:
        _compiled_rules = []
        for pattern_str, section_id, description in TITLE_RULES:
            try:
                compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
                _compiled_rules.append((compiled_pattern, section_id, description))
            except re.error as e:
                logger.error(f"Erreur compilation regex '{pattern_str}': {e}")
        
        logger.info(f"Title rules compiled: {len(_compiled_rules)} rules loaded")
    
    return _compiled_rules


def match_title_rule(normalized_title: str, debug: bool = False) -> Optional[str]:
    """
    Applique les règles regex sur un titre normalisé.
    
    Args:
        normalized_title: Titre NORMALISÉ (uppercase, sans accents/ponctuation)
        debug: Si True, log les détails du matching
        
    Returns:
        Section canonique si une règle match, None sinon
    """
    if not normalized_title:
        return None
    
    rules = compile_title_rules()
    
    for pattern, section_id, description in rules:
        if pattern.search(normalized_title):
            if debug:
                logger.debug(
                    f"RULE MATCH: '{normalized_title[:50]}' → '{section_id}' "
                    f"(rule: {description})"
                )
            return section_id
    
    return None


def get_rules_summary() -> List[dict]:
    """
    Retourne un résumé des règles chargées (pour debug/doc).
    
    Returns:
        Liste de dicts avec pattern, section, description
    """
    return [
        {
            'pattern': pattern_str,
            'section': section_id,
            'description': description
        }
        for pattern_str, section_id, description in TITLE_RULES
    ]
