"""
PATCH 1 — Identity Extractor Global

Extrait l'identité (AVS, nom, prénom) depuis TOUTES les sources du dossier client,
pas seulement depuis la section "identity" du DOCX structurant.

But: Stopper les NO-GO causés par identity vide alors que les données existent
dans des lignes classées comme "unknown_titles".
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging

LOGGER = logging.getLogger(__name__)


def extract_identity_from_text(text: str) -> Dict[str, str]:
    """
    Extrait AVS, nom, prénom depuis un texte quelconque.
    
    Args:
        text: Texte à analyser (peut être une ligne, un paragraphe, ou un document complet)
        
    Returns:
        Dict avec clés: avs, name, surname, full_name (vides si non trouvé)
        
    Examples:
        >>> extract_identity_from_text("Monsieur Jean DUPONT – 756.1234.5678.90")
        {'avs': '756.1234.5678.90', 'name': 'Jean', 'surname': 'DUPONT', 'full_name': 'Jean DUPONT'}
        
        >>> extract_identity_from_text("AVS: 756 1234 5678 90")
        {'avs': '756.1234.5678.90', 'name': '', 'surname': '', 'full_name': ''}
    """
    result = {"avs": "", "name": "", "surname": "", "full_name": ""}
    
    # 1. Extraction AVS (tolérant: espaces, points, tirets)
    # Pattern: 756 suivi de 10 chiffres (avec séparateurs optionnels)
    avs_pattern = r'756[\s\.\-]?\d{4}[\s\.\-]?\d{4}[\s\.\-]?\d{2}'
    avs_match = re.search(avs_pattern, text)
    if avs_match:
        # Normaliser avec points
        avs_raw = avs_match.group()
        avs_digits = re.sub(r'[\s\.\-]', '', avs_raw)
        result['avs'] = f"{avs_digits[:3]}.{avs_digits[3:7]}.{avs_digits[7:11]}.{avs_digits[11:]}"
    
    # 2. Extraction nom complet (plusieurs patterns)
    
    # Pattern 1: "Monsieur/Madame Prénom NOM – AVS"
    name_pattern1 = r'(?:Monsieur|Madame|M\.|Mme)\s+([A-ZÀ-ÖØ-Ýa-zà-öø-ÿ\s\-]+?)(?:\s*[\u2013\u2014\-]\s*756|$)'
    match1 = re.search(name_pattern1, text, re.IGNORECASE)
    
    # Pattern 2: "Nom: XXX" ou "Prénom: XXX"
    nom_pattern = r'Nom\s*:\s*([A-ZÀ-ÖØ-Ý][A-ZÀ-ÖØ-Ýa-zà-öø-ÿ\s\-]+)'
    prenom_pattern = r'Pr[ée]nom\s*:\s*([A-ZÀ-ÖØ-Ý][A-ZÀ-ÖØ-Ýa-zà-öø-ÿ\s\-]+)'
    
    nom_match = re.search(nom_pattern, text, re.IGNORECASE)
    prenom_match = re.search(prenom_pattern, text, re.IGNORECASE)
    
    # Pattern 3: Ligne type "NOM Prénom" ou "Prénom NOM" (avec AVS proche)
    # Seulement si AVS trouvé à proximité
    if result['avs']:
        # Extraire texte avant AVS
        avs_pos = text.find(result['avs'].replace('.', ''))
        if avs_pos == -1:
            # Essayer avec format original
            if avs_match:
                avs_pos = text.find(avs_match.group())
        
        if avs_pos > 0:
            text_before_avs = text[:avs_pos].strip()
            # Prendre les derniers mots avant AVS
            words = text_before_avs.split()[-5:]  # Max 5 mots
            if len(words) >= 2:
                # Filtrer les mots de civilité
                filtered_words = [w for w in words if w.lower() not in ['monsieur', 'madame', 'm.', 'mme', '-', '–', '—']]
                if len(filtered_words) >= 2:
                    result['full_name'] = ' '.join(filtered_words).strip()
    
    # Utiliser Pattern 1 si disponible (prioritaire)
    if match1:
        full_name = match1.group(1).strip()
        result['full_name'] = full_name
    
    # Utiliser Pattern 2 si disponible
    if nom_match or prenom_match:
        nom_val = nom_match.group(1).strip() if nom_match else ""
        prenom_val = prenom_match.group(1).strip() if prenom_match else ""
        
        result['surname'] = nom_val
        result['name'] = prenom_val
        if nom_val or prenom_val:
            result['full_name'] = f"{prenom_val} {nom_val}".strip()
    
    # Si full_name trouvé mais pas surname/name, tenter de séparer
    if result['full_name'] and not (result['surname'] or result['name']):
        name_parts = result['full_name'].split()
        if len(name_parts) >= 2:
            # Convention: dernier mot = nom de famille (souvent en majuscules)
            result['surname'] = name_parts[-1]
            result['name'] = ' '.join(name_parts[:-1])
        elif len(name_parts) == 1:
            result['surname'] = name_parts[0]
    
    return result


def contains_avs(text: str) -> bool:
    """
    Vérifie rapidement si un texte contient un numéro AVS.
    
    Args:
        text: Texte à vérifier
        
    Returns:
        True si AVS détecté
        
    Example:
        >>> contains_avs("Ligne avec 756.1234.5678.90")
        True
        >>> contains_avs("Ligne sans AVS")
        False
    """
    avs_pattern = r'756[\s\.\-]?\d{4}[\s\.\-]?\d{4}[\s\.\-]?\d{2}'
    return bool(re.search(avs_pattern, text))


def extract_identity_from_corpus(
    texts: List[str],
    max_lines_per_text: int = 50
) -> Dict[str, str]:
    """
    Extrait l'identité depuis un corpus de textes (sources multiples).
    
    Stratégie:
    1. Scanner les N premières lignes de chaque texte
    2. Chercher AVS + nom/prénom
    3. Retourner le premier match complet (ou meilleur match partiel)
    
    Args:
        texts: Liste de textes à analyser (ex: contenu de tous les docs du client)
        max_lines_per_text: Nombre max de lignes à analyser par texte
        
    Returns:
        Dict avec clés: avs, name, surname, full_name
        
    Example:
        >>> texts = [
        ...     "Document 1 sans identité...",
        ...     "Monsieur Jean DUPONT – 756.1234.5678.90\\nSituation: ..."
        ... ]
        >>> extract_identity_from_corpus(texts)
        {'avs': '756.1234.5678.90', 'name': 'Jean', 'surname': 'DUPONT', ...}
    """
    best_result = {"avs": "", "name": "", "surname": "", "full_name": ""}
    best_score = 0
    
    for text in texts:
        if not text:
            continue
        
        # Analyser les N premières lignes
        lines = text.split('\n')[:max_lines_per_text]
        text_snippet = '\n'.join(lines)
        
        # Extraire identité
        result = extract_identity_from_text(text_snippet)
        
        # Scorer le résultat (plus de champs remplis = meilleur)
        score = 0
        if result['avs']:
            score += 10  # AVS très important
        if result['surname']:
            score += 5
        if result['name']:
            score += 5
        if result['full_name']:
            score += 3
        
        # Garder le meilleur résultat
        if score > best_score:
            best_score = score
            best_result = result
            
            # Si on a AVS + nom + prénom, c'est parfait
            if score >= 20:
                LOGGER.info(f"Identity complète trouvée (score={score}): AVS={result['avs']}, nom={result['surname']}, prénom={result['name']}")
                break
    
    return best_result


def extract_identity_from_files(
    file_paths: List[Union[str, Path]],
    max_lines_per_file: int = 50
) -> Dict[str, str]:
    """
    Extrait l'identité depuis une liste de fichiers.
    
    Lit les N premières lignes de chaque fichier et cherche l'identité.
    
    Args:
        file_paths: Liste de strings ou Path vers fichiers à analyser
        max_lines_per_file: Nombre max de lignes à lire par fichier
        
    Returns:
        Dict avec clés: avs, name, surname, full_name
        
    Note:
        Supporte: .txt, .docx (via python-docx)
        Ignore: fichiers binaires non supportés
    """
    texts = []
    
    for file_path in file_paths:
        # Convertir en Path si c'est une string
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        if not file_path.exists():
            continue
        
        try:
            # Fichiers texte
            if file_path.suffix.lower() in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = [f.readline() for _ in range(max_lines_per_file)]
                    texts.append(''.join(lines))
            
            # Fichiers DOCX
            elif file_path.suffix.lower() in ['.docx', '.doc']:
                try:
                    from docx import Document
                    doc = Document(str(file_path))
                    paragraphs = [p.text for p in doc.paragraphs[:max_lines_per_file]]
                    texts.append('\n'.join(paragraphs))
                except Exception as e:
                    LOGGER.warning(f"Impossible de lire DOCX {file_path.name}: {e}")
            
            # PDF (optionnel, nécessite pdfplumber ou pymupdf)
            elif file_path.suffix.lower() == '.pdf':
                try:
                    import pdfplumber
                    with pdfplumber.open(str(file_path)) as pdf:
                        # Première page uniquement
                        if pdf.pages:
                            text = pdf.pages[0].extract_text() or ""
                            texts.append(text)
                except ImportError:
                    LOGGER.debug("pdfplumber non disponible, skip PDF")
                except Exception as e:
                    LOGGER.warning(f"Erreur lecture PDF {file_path.name}: {e}")
        
        except Exception as e:
            LOGGER.warning(f"Erreur lecture fichier {file_path.name}: {e}")
            continue
    
    return extract_identity_from_corpus(texts, max_lines_per_text=max_lines_per_file)


def merge_identity_results(
    existing: Dict[str, str],
    new: Dict[str, str],
    overwrite: bool = False
) -> Dict[str, str]:
    """
    Merge deux résultats d'extraction identity.
    
    Règle: Ne pas écraser les champs existants sauf si overwrite=True
    
    Args:
        existing: Identity existante
        new: Nouvelle identity extraite
        overwrite: Si True, écraser même si existant non vide
        
    Returns:
        Identity mergée
        
    Example:
        >>> existing = {'avs': '', 'name': 'Jean', 'surname': 'DUPONT', 'full_name': ''}
        >>> new = {'avs': '756.1234.5678.90', 'name': '', 'surname': '', 'full_name': 'Jean DUPONT'}
        >>> merge_identity_results(existing, new)
        {'avs': '756.1234.5678.90', 'name': 'Jean', 'surname': 'DUPONT', 'full_name': 'Jean DUPONT'}
    """
    result = existing.copy()
    
    for key in ['avs', 'name', 'surname', 'full_name']:
        if key in new:
            # Écraser si overwrite OU si champ vide
            if overwrite or not result.get(key):
                if new[key]:  # Ne pas écraser avec une valeur vide
                    result[key] = new[key]
    
    return result


def is_identity_line(text: str) -> bool:
    """
    Détecte si une ligne de texte contient des données d'identité.
    
    Utilisé pour PATCH 2 (heading policy): éviter de classer les lignes
    identity comme "unknown_titles".
    
    Args:
        text: Ligne de texte à analyser
        
    Returns:
        True si la ligne contient AVS ou patterns identity
        
    Example:
        >>> is_identity_line("Monsieur Jean DUPONT – 756.1234.5678.90")
        True
        >>> is_identity_line("Objectifs professionnels")
        False
    """
    # Contient AVS ?
    if contains_avs(text):
        return True
    
    # Contient pattern "Nom:" ou "Prénom:" ?
    if re.search(r'(Nom|Pr[ée]nom)\s*:', text, re.IGNORECASE):
        return True
    
    # Contient civilité + nom potentiel ?
    if re.search(r'(Monsieur|Madame|M\.|Mme)\s+[A-ZÀ-ÖØ-Ý]', text, re.IGNORECASE):
        return True
    
    return False


def extract_identity_from_folder_name(folder_name: str) -> Dict[str, str]:
    """
    Extrait l'identité depuis le nom du dossier client.
    
    QUICK WIN: Fallback pour récupérer name/surname quand aucune autre source disponible.
    
    Patterns supportés:
    - "SCHMIDT Mélanie" → surname: SCHMIDT, name: Mélanie
    - "CAMPOS DA COSTA Paula" → surname: CAMPOS DA COSTA, name: Paula
    - "Jean DUPONT" → name: Jean, surname: DUPONT
    - "Dupont-Martin Sophie" → surname: Dupont-Martin, name: Sophie
    
    Convention: 
    - Mots en MAJUSCULES = nom de famille (peut être multi-mots)
    - Premier mot en casse mixte après majuscules = prénom
    - Si pas de majuscules claires, dernier mot = nom
    
    Args:
        folder_name: Nom du dossier client (ex: "SCHMIDT Mélanie")
        
    Returns:
        Dict avec clés: avs (vide), name, surname, full_name
        
    Examples:
        >>> extract_identity_from_folder_name("SCHMIDT Mélanie")
        {'avs': '', 'name': 'Mélanie', 'surname': 'SCHMIDT', 'full_name': 'SCHMIDT Mélanie'}
        
        >>> extract_identity_from_folder_name("CAMPOS DA COSTA Paula")
        {'avs': '', 'name': 'Paula', 'surname': 'CAMPOS DA COSTA', 'full_name': 'CAMPOS DA COSTA Paula'}
    """
    result = {"avs": "", "name": "", "surname": "", "full_name": ""}
    
    # Nettoyer le nom du dossier
    # Retirer préfixes numériques (ex: "001_SCHMIDT Mélanie")
    folder_clean = re.sub(r'^\d+[_\-\s]*', '', folder_name).strip()
    
    # Retirer extensions et caractères spéciaux
    folder_clean = re.sub(r'\.(docx?|pdf|txt)$', '', folder_clean, flags=re.IGNORECASE)
    folder_clean = folder_clean.replace('_', ' ').replace('-', ' ')
    
    if not folder_clean:
        return result
    
    result['full_name'] = folder_clean
    
    # Séparer en mots
    words = folder_clean.split()
    
    if len(words) == 0:
        return result
    
    # Pattern 1: Identifier les mots en MAJUSCULES (nom de famille)
    uppercase_words = []
    other_words = []
    
    for word in words:
        # Un mot est considéré comme "majuscule" si au moins 50% des lettres sont en maj
        if word and sum(1 for c in word if c.isupper()) >= len(word) * 0.5:
            uppercase_words.append(word)
        else:
            other_words.append(word)
    
    # Cas 1: Mots en MAJUSCULES trouvés → nom de famille
    if uppercase_words:
        result['surname'] = ' '.join(uppercase_words)
        
        # Prénom = reste des mots (après les majuscules dans l'ordre original)
        # Reconstruire l'ordre
        surname_start_idx = words.index(uppercase_words[0])
        surname_end_idx = words.index(uppercase_words[-1])
        
        # Prénoms = mots après le nom
        if surname_end_idx + 1 < len(words):
            result['name'] = ' '.join(words[surname_end_idx + 1:])
        # Ou prénoms avant (moins courant)
        elif surname_start_idx > 0:
            result['name'] = ' '.join(words[:surname_start_idx])
    
    # Cas 2: Pas de majuscules claires → convention dernier mot = nom
    elif len(words) >= 2:
        result['surname'] = words[-1]
        result['name'] = ' '.join(words[:-1])
    
    # Cas 3: Un seul mot → nom de famille uniquement
    elif len(words) == 1:
        result['surname'] = words[0]
    
    return result
