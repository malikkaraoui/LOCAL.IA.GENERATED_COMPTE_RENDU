"""
Client Finder — Recherche tolérante de dossiers clients par nom
"""
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    """
    Normalise un texte : minuscules + suppression accents
    
    Args:
        text: Texte à normaliser
        
    Returns:
        Texte normalisé (minuscules, sans accents)
        
    Example:
        >>> normalize_text("ARIFI Élodie")
        'arifi elodie'
    """
    # Normalisation NFD (décomposition des accents)
    nfd = unicodedata.normalize('NFD', text)
    # Supprimer les accents (catégorie Mn = Mark, Nonspacing)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    # Minuscules
    return without_accents.lower()


def fuzzy_score(query: str, target: str) -> float:
    """
    Calcule un score de similarité entre query et target
    
    Args:
        query: Texte recherché
        target: Texte cible
        
    Returns:
        Score entre 0.0 et 1.0 (1.0 = match parfait)
        
    Example:
        >>> fuzzy_score("arifi", "ARIFI Elodie")
        0.85
    """
    # Normaliser les deux textes
    q_norm = normalize_text(query)
    t_norm = normalize_text(target)
    
    # Score basé sur SequenceMatcher
    base_score = SequenceMatcher(None, q_norm, t_norm).ratio()
    
    # Bonus si query est contenu dans target
    if q_norm in t_norm:
        base_score += 0.3
    
    # Bonus si query est au début de target (nom/prénom)
    if t_norm.startswith(q_norm):
        base_score += 0.2
    
    # Bonus si tous les mots de query sont dans target
    query_words = set(q_norm.split())
    target_words = set(t_norm.split())
    if query_words and query_words.issubset(target_words):
        base_score += 0.3
    
    # Limiter à 1.0
    return min(base_score, 1.0)


def find_client_folders(root_dir: str, query: str = None, min_score: float = 0.3) -> List[Dict[str, Any]]:
    """
    Trouve tous les dossiers clients dans root_dir
    Si query fourni, filtre et trie par pertinence (fuzzy matching)
    
    Args:
        root_dir: Dossier racine contenant les dossiers clients
        query: Terme de recherche optionnel (ex: "ARIFI")
        min_score: Score minimum pour inclure un résultat (défaut: 0.3)
        
    Returns:
        Liste de dicts avec:
        - path: Path absolu du dossier
        - name: Nom du dossier
        - score: Score de pertinence (si query fourni)
        - has_docx: True si contient au moins un .docx
        
    Example:
        >>> results = find_client_folders("/path/to/dataset", "ARIFI")
        >>> print(results[0]['name'])
        'ARIFI Elodie'
    """
    root = Path(root_dir)
    
    if not root.exists():
        raise FileNotFoundError(f"Root directory not found: {root_dir}")
    
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_dir}")
    
    # Lister tous les sous-dossiers directs
    all_folders = [
        d for d in root.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    ]
    
    results = []
    
    for folder in all_folders:
        # Vérifier si contient au moins un fichier (docx, pdf, txt, etc.)
        has_docx = any(folder.glob("*.docx"))
        has_pdf = any(folder.glob("*.pdf"))
        has_txt = any(folder.glob("*.txt"))
        has_audio = any(folder.glob("*.mp3")) or any(folder.glob("*.wav")) or any(folder.glob("*.m4a"))
        has_files = has_docx or has_pdf or has_txt or has_audio
        
        entry = {
            'path': folder,
            'name': folder.name,
            'has_docx': has_docx,
            'has_pdf': has_pdf,
            'has_txt': has_txt,
            'has_audio': has_audio,
            'has_files': has_files
        }
        
        # Si query fourni, calculer le score
        if query:
            score = fuzzy_score(query, folder.name)
            if score >= min_score:
                entry['score'] = score
                results.append(entry)
        else:
            entry['score'] = 1.0  # Tous les dossiers ont score max si pas de query
            results.append(entry)
    
    # Trier par score décroissant
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results


def find_client_folder(root_dir: str, query: str, exact: bool = False) -> Tuple[Path, List[Dict[str, Any]]]:
    """
    Trouve UN dossier client par nom (recherche tolérante)
    
    Args:
        root_dir: Dossier racine contenant les dossiers clients
        query: Terme de recherche (ex: "ARIFI", "arifi elodie")
        exact: Si True, nécessite un match exact (après normalisation)
        
    Returns:
        Tuple (best_match_path, all_matches)
        - best_match_path: Path du meilleur résultat (ou None si aucun)
        - all_matches: Liste complète des résultats triés par score
        
    Raises:
        FileNotFoundError: Si root_dir n'existe pas
        
    Example:
        >>> path, matches = find_client_folder("/dataset", "ARIFI")
        >>> if len(matches) > 1:
        ...     print(f"Ambigu: {len(matches)} résultats")
        >>> print(path.name)
        'ARIFI Elodie'
    """
    # Recherche avec score minimum
    min_score = 0.9 if exact else 0.3
    matches = find_client_folders(root_dir, query, min_score)
    
    if not matches:
        return None, []
    
    # Si match exact demandé, vérifier score parfait
    if exact:
        best = matches[0]
        if best['score'] >= 0.95:
            return best['path'], matches
        else:
            return None, matches
    
    # Retourner le meilleur résultat
    return matches[0]['path'], matches


def format_search_results(matches: List[Dict[str, Any]], max_results: int = 10) -> str:
    """
    Formate les résultats de recherche pour affichage console
    
    Args:
        matches: Liste des résultats de find_client_folders()
        max_results: Nombre max de résultats à afficher
        
    Returns:
        str formaté pour console
    """
    if not matches:
        return "⚠️  Aucun résultat trouvé"
    
    lines = []
    lines.append(f"🔍 {len(matches)} résultat(s) trouvé(s):")
    lines.append("")
    
    for i, match in enumerate(matches[:max_results], 1):
        score = match.get('score', 0.0)
        name = match['name']
        
        # Indicateurs de fichiers
        indicators = []
        if match.get('has_docx'):
            indicators.append('📄')
        if match.get('has_pdf'):
            indicators.append('📕')
        if match.get('has_audio'):
            indicators.append('🎤')
        
        indicators_str = ''.join(indicators) if indicators else '📁'
        
        # Affichage
        lines.append(f"{i:2d}. [{score:.2f}] {indicators_str} {name}")
    
    if len(matches) > max_results:
        lines.append(f"    ... et {len(matches) - max_results} autre(s)")
    
    return "\n".join(lines)


def discover_client_documents(client_folder: Path) -> Dict[str, List[Path]]:
    """
    Découvre tous les documents dans un dossier client
    
    Args:
        client_folder: Path du dossier client
        
    Returns:
        Dict avec clés 'docx', 'pdf', 'txt', 'audio'
        Chaque valeur est une liste de Path
        
    Example:
        >>> docs = discover_client_documents(Path("/dataset/ARIFI Elodie"))
        >>> print(f"DOCX: {len(docs['docx'])}")
        DOCX: 3
    """
    if not client_folder.exists():
        raise FileNotFoundError(f"Client folder not found: {client_folder}")
    
    documents = {
        'docx': list(client_folder.glob("*.docx")),
        'pdf': list(client_folder.glob("*.pdf")),
        'txt': list(client_folder.glob("*.txt")),
        'audio': []
    }
    
    # Audio formats
    for ext in ['mp3', 'wav', 'm4a', 'ogg', 'flac']:
        documents['audio'].extend(client_folder.glob(f"*.{ext}"))
    
    return documents
