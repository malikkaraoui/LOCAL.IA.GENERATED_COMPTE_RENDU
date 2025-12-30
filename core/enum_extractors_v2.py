"""
Extracteurs pour champs enum V2 (langues, bureautique, tests)

OBJECTIF: Extraction stricte avec fallback "Non évalué"
- Langues: regex CECRL (A1-C2)
- Bureautique: mots-clés + qualificatifs
- Tests: mentions explicites OK/Moyen/À renforcer

RÈGLE: Jamais d'inférence. Si pas de preuve → "Non évalué"
"""

import re
from typing import Optional


# ============================================================================
# A) EXTRACTION NIVEAUX CECRL (Langues)
# ============================================================================

CECRL_PATTERN = re.compile(r'\b(A1|A2|B1|B2|C1|C2)\b', re.IGNORECASE)


def extract_cecrl_level(text: str) -> str:
    """
    Extrait un niveau CECRL depuis le texte.
    
    Args:
        text: Contenu à analyser
        
    Returns:
        Niveau CECRL (A1-C2) ou "Non évalué"
        
    Examples:
        >>> extract_cecrl_level("Le client a un niveau B2 en français")
        'B2'
        >>> extract_cecrl_level("Pas de niveau mentionné")
        'Non évalué'
    """
    if not text:
        return "Non évalué"
    
    match = CECRL_PATTERN.search(text)
    if match:
        return match.group(1).upper()
    
    return "Non évalué"


# ============================================================================
# B) EXTRACTION NIVEAUX BUREAUTIQUE
# ============================================================================

TOOL_KEYWORDS = {
    "word": ["word", "traitement de texte"],
    "excel": ["excel", "tableur"],
    "powerpoint": ["powerpoint", "présentation"],
    "outlook": ["outlook", "messagerie"],
}

TOOL_QUALIFIERS = {
    "très bon": ["très bon", "excellent", "expert", "maîtrise parfaite"],
    "bon": ["bon", "bonne maîtrise", "maîtrise", "compétent"],
    "moyen": ["moyen", "correct", "basique", "notions"],
    "faible": ["faible", "limité", "débutant", "peu d'expérience"],
}


def extract_bureautique_level(text: str) -> str:
    """
    Extrait un niveau de bureautique depuis le texte.
    
    Args:
        text: Contenu à analyser
        
    Returns:
        Niveau: "Faible" | "Moyen" | "Bon" | "Très bon" | "Non évalué"
        
    Examples:
        >>> extract_bureautique_level("Bonne maîtrise de Word et Excel")
        'Bon'
        >>> extract_bureautique_level("Utilisateur expert des outils Office")
        'Très bon'
        >>> extract_bureautique_level("Pas d'information")
        'Non évalué'
    """
    if not text:
        return "Non évalué"
    
    text_lower = text.lower()
    
    # Vérifier si au moins un outil est mentionné
    tool_mentioned = False
    for tool_patterns in TOOL_KEYWORDS.values():
        if any(pattern in text_lower for pattern in tool_patterns):
            tool_mentioned = True
            break
    
    if not tool_mentioned:
        return "Non évalué"
    
    # Chercher un qualificatif (priorité décroissante)
    for level, patterns in TOOL_QUALIFIERS.items():
        if any(pattern in text_lower for pattern in patterns):
            # Normaliser la sortie
            if level == "très bon":
                return "Très bon"
            return level.capitalize()
    
    # Outil mentionné mais pas de qualificatif → considérer comme "Moyen"
    # (mais c'est risqué, préférer "Non évalué")
    return "Non évalué"


# ============================================================================
# C) EXTRACTION RÉSULTATS TESTS
# ============================================================================

TEST_RESULT_PATTERNS = {
    "OK": [
        r'\bOK\b',
        r'\bréussi\b',
        r'\bvalidé\b',
        r'\bacquis\b',
        r'\bmaîtrisé\b',
    ],
    "Moyen": [
        r'\bmoyen\b',
        r'\bcorrect\b',
        r'\bpassable\b',
        r'\ben cours d\'acquisition\b',
    ],
    "À renforcer": [
        r'\bà renforcer\b',
        r'\bà améliorer\b',
        r'\binsuffisant\b',
        r'\bdifficultés\b',
        r'\bfaible\b',
        r'\bnon maîtrisé\b',
    ],
}


def extract_test_result(text: str, test_name: Optional[str] = None) -> str:
    """
    Extrait un résultat de test depuis le texte.
    
    Args:
        text: Contenu à analyser
        test_name: Nom du test (optionnel, pour contextualiser)
        
    Returns:
        Résultat: "OK" | "Moyen" | "À renforcer" | "Non évalué"
        
    Examples:
        >>> extract_test_result("Test d'attention: OK")
        'OK'
        >>> extract_test_result("Calcul: difficultés observées")
        'À renforcer'
        >>> extract_test_result("Aucun test passé")
        'Non évalué'
    """
    if not text:
        return "Non évalué"
    
    text_lower = text.lower()
    
    # Chercher patterns (ordre de priorité)
    for result, patterns in TEST_RESULT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return result
    
    return "Non évalué"


# ============================================================================
# D) EXTRACTION PAR CONTEXTE (si titre de section disponible)
# ============================================================================

def extract_enum_from_context(
    text: str,
    field_key: str,
    section_title: Optional[str] = None
) -> str:
    """
    Extraction intelligente basée sur le type de champ.
    
    Args:
        text: Contenu à analyser
        field_key: Clé du champ (ex: "FRANCAIS_POSITIONNEMENT_DE_NIVEAU")
        section_title: Titre de la section (optionnel)
        
    Returns:
        Valeur extraite ou "Non évalué"
    """
    if not text:
        return "Non évalué"
    
    # Bureautique (AVANT langues car contient aussi POSITIONNEMENT_DE_NIVEAU)
    if "BUREAUTIQUE" in field_key:
        return extract_bureautique_level(text)
    
    # Langues
    if "POSITIONNEMENT_DE_NIVEAU" in field_key:
        return extract_cecrl_level(text)
    
    # Tests
    if "TEST" in field_key or "CALCUL" in field_key or "COMPREHENSION" in field_key:
        return extract_test_result(text, field_key)
    
    return "Non évalué"


# ============================================================================
# E) VALIDATION DE VALEUR ENUM
# ============================================================================

def validate_enum_value(value: str, allowed_values: list[str], strict: bool = False) -> str:
    """
    Valide qu'une valeur est dans la liste autorisée.
    
    Args:
        value: Valeur à valider
        allowed_values: Liste des valeurs autorisées
        strict: Si True, accepte SEULEMENT les valeurs exactes (anti-hallucination)
        
    Returns:
        value si valide, sinon dernière valeur de allowed_values (fallback)
        
    Examples:
        >>> validate_enum_value("B2", ["A1", "A2", "B1", "B2", "C1", "C2", "Non évalué"])
        'B2'
        >>> validate_enum_value("Très bon niveau", ["Faible", "Moyen", "Bon", "Très bon", "Non évalué"])
        'Très bon'
        >>> validate_enum_value("Très bon niveau", ["Faible", "Moyen", "Bon", "Très bon", "Non évalué"], strict=True)
        'Non évalué'
    """
    if not value:
        return allowed_values[-1]  # Fallback (généralement "Non évalué")
    
    # Normaliser
    value_normalized = value.strip()
    
    # Vérifier si exacte
    if value_normalized in allowed_values:
        return value_normalized
    
    # Si strict: REJETER immédiatement si pas exacte
    if strict:
        return allowed_values[-1]
    
    # Mode tolérant: vérifier si contient
    for allowed in allowed_values[:-1]:  # Exclure "Non évalué" de cette recherche
        if allowed.lower() in value_normalized.lower():
            return allowed
    
    # Fallback
    return allowed_values[-1]


if __name__ == "__main__":
    # Tests rapides
    print("CECRL:", extract_cecrl_level("Le client a un niveau B2 en français"))
    print("CECRL vide:", extract_cecrl_level("Pas de niveau"))
    
    print("Bureautique:", extract_bureautique_level("Bonne maîtrise d'Excel"))
    print("Bureautique expert:", extract_bureautique_level("Expert Word et PowerPoint"))
    
    print("Test OK:", extract_test_result("Test d'attention: OK"))
    print("Test à renforcer:", extract_test_result("Difficultés en calcul"))
