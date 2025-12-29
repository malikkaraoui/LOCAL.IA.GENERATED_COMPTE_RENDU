"""
Extracteur de niveaux pour les sections "POSITIONNEMENT DE NIVEAU".

Ces sections doivent retourner UNE VALEUR (niveau CECRL ou score) extraite directement
des documents source, JAMAIS générée par le LLM.
"""

import re
from typing import Optional


# Patterns de détection des niveaux
PATTERN_CECRL = re.compile(r'\b(A1|A2|B1|B2|C1|C2)\b', re.IGNORECASE)
PATTERN_PERCENT = re.compile(r'(\d{1,3})\s?%')
PATTERN_FRACTION = re.compile(r'(\d{1,2})\s*/\s*(\d{1,2})')
PATTERN_NOTE_SUR = re.compile(r'(\d{1,2}(?:[.,]\d{1,2})?)\s*/\s*(\d{1,2})')


def extract_positionnement_level(text: str) -> str:
    """
    Extrait un niveau de positionnement depuis un texte.
    
    Priorité de détection :
    1. Niveau CECRL (A1, A2, B1, B2, C1, C2)
    2. Score pourcentage (ex: 85%)
    3. Score fraction (ex: 12/20)
    4. Si rien trouvé : "Non renseigné"
    
    Args:
        text: Texte source à analyser
        
    Returns:
        Niveau ou score extrait, ou "Non renseigné"
        
    Examples:
        >>> extract_positionnement_level("Niveau: C2")
        'C2'
        >>> extract_positionnement_level("Score: 12/20")
        '12/20'
        >>> extract_positionnement_level("Résultat: 85%")
        '85%'
        >>> extract_positionnement_level("Pas de niveau mentionné")
        'Non renseigné'
    """
    if not text or not text.strip():
        return "Non renseigné"
    
    # 1. Chercher niveau CECRL (priorité haute)
    match_cecrl = PATTERN_CECRL.search(text)
    if match_cecrl:
        return match_cecrl.group(1).upper()
    
    # 2. Chercher pourcentage (ex: 85%, 90 %) - AVANT fraction pour éviter confusion
    match_percent = PATTERN_PERCENT.search(text)
    if match_percent:
        value = match_percent.group(1)
        # Valider que c'est un pourcentage plausible (0-100)
        try:
            int_value = int(value)
            if 0 <= int_value <= 100:
                return f"{value}%"
        except ValueError:
            pass
    
    # 3. Chercher score fraction (ex: 12/20, 15 / 20)
    match_fraction = PATTERN_FRACTION.search(text)
    if match_fraction:
        numerator = match_fraction.group(1)
        denominator = match_fraction.group(2)
        return f"{numerator}/{denominator}"
    
    # 4. Aucun niveau détecté
    return "Non renseigné"


def is_positionnement_title(normalized_title: str) -> bool:
    """
    Détermine si un titre normalisé correspond à une section de positionnement.
    
    Les titres suivants déclenchent l'extraction directe :
    - Tout titre contenant "POSITIONNEMENT" + "NIVEAU"
    - Exemples : "FRANCAIS - POSITIONNEMENT DE NIVEAU", "ANGLAIS POSITIONNEMENT"
    
    Args:
        normalized_title: Titre normalisé (uppercase, sans accents, tirets remplacés par espaces)
        
    Returns:
        True si c'est une section de positionnement
        
    Examples:
        >>> is_positionnement_title("FRANCAIS POSITIONNEMENT DE NIVEAU")
        True
        >>> is_positionnement_title("ANGLAIS POSITIONNEMENT")
        True
        >>> is_positionnement_title("FRANCAIS NIVEAU 2")
        False
        >>> is_positionnement_title("TESTS METIERS")
        False
    """
    # Normaliser davantage : remplacer tirets (-, –, —) par espaces
    title_clean = normalized_title.replace("-", " ").replace("–", " ").replace("—", " ")
    title_clean = " ".join(title_clean.split())  # Supprimer espaces multiples
    
    # Doit contenir "POSITIONNEMENT" ET ("NIVEAU" OU rien d'autre après)
    has_positionnement = "POSITIONNEMENT" in title_clean
    has_niveau = "NIVEAU" in title_clean
    
    # Accepter "POSITIONNEMENT" seul ou "POSITIONNEMENT DE NIVEAU"
    if has_positionnement and (has_niveau or title_clean.endswith("POSITIONNEMENT")):
        return True
    
    return False


def extract_positionnement_from_segments(segments: list[dict]) -> dict[str, str]:
    """
    Extrait les niveaux de positionnement depuis une liste de segments.
    
    Args:
        segments: Liste de dicts avec keys 'normalized_title' et 'lines'
        
    Returns:
        Dict mapping langue/outil → niveau extrait
        Exemple: {"francais": "C2", "anglais": "B1", "word": "12/20"}
    """
    positionnement_levels = {}
    
    for segment in segments:
        title = segment.get("normalized_title", "")
        
        if not is_positionnement_title(title):
            continue
        
        # Identifier la langue/outil
        key = None
        if "FRANCAIS" in title or "FRANÇAIS" in title:
            key = "francais"
        elif "ANGLAIS" in title:
            key = "anglais"
        elif "ALLEMAND" in title:
            key = "allemand"
        elif "WORD" in title:
            key = "word"
        elif "EXCEL" in title:
            key = "excel"
        elif "POWERPOINT" in title:
            key = "powerpoint"
        elif "OUTLOOK" in title:
            key = "outlook"
        else:
            # Cas générique : utiliser le titre normalisé comme clé
            key = title.lower().replace(" ", "_")
        
        if not key:
            continue
        
        # Extraire le contenu (joindre toutes les lignes)
        lines = segment.get("lines", [])
        content = "\n".join(lines)
        
        # Extraire le niveau
        level = extract_positionnement_level(content)
        positionnement_levels[key] = level
    
    return positionnement_levels
