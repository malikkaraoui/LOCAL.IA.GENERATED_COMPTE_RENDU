"""
Client Finder — Recherche tolérante de dossiers clients par nom
"""
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
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
    Découvre tous les documents dans un dossier client (racine uniquement, legacy).
    
    ⚠️ DEPRECATED : Utiliser discover_client_documents_recursive() avec max_depth=0 pour équivalent.
    
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


def discover_client_documents_recursive(
    client_folder: Path,
    max_depth: int = 2,
    include_subfolders: bool = True,
    max_files: int = 5000,
    allowed_exts: Optional[set] = None,
    ignore_dirs: Optional[set] = None,
    follow_symlinks: bool = False
) -> Dict[str, Any]:
    """
    Découvre tous les documents dans un dossier client avec scan récursif contrôlé.
    
    Args:
        client_folder: Path du dossier client
        max_depth: Profondeur maximale de scan (0 = racine uniquement, 1 = sous-dossiers directs, etc.)
        include_subfolders: Si False, force max_depth=0
        max_files: Limite maximale de fichiers scannés (évite freeze UI)
        allowed_exts: Extensions autorisées (défaut: {'.pdf','.docx','.doc','.txt','.msg','.m4a','.mp3','.wav'})
        ignore_dirs: Dossiers à ignorer (défaut: {'.git','__MACOSX','node_modules','.venv','venv','artifacts','output'})
        follow_symlinks: Suivre les liens symboliques
        
    Returns:
        Dict avec:
        - 'files': Dict[str, List[Path]] avec clés 'docx', 'pdf', 'txt', 'audio', 'msg'
        - 'stats_by_type': Dict[str, int] avec nombre de fichiers par type
        - 'stats_by_subfolder': Dict[str, Dict[str, int]] avec stats par sous-dossier (top 10)
        - 'total_files': int
        - 'truncated': bool (si max_files atteint)
        
    Example:
        >>> result = discover_client_documents_recursive(
        ...     Path("/dataset/ARIFI Elodie"),
        ...     max_depth=2,
        ...     include_subfolders=True
        ... )
        >>> print(f"Total: {result['total_files']} fichiers")
        >>> print(f"DOCX: {len(result['files']['docx'])}")
        >>> print(f"Sous-dossiers: {list(result['stats_by_subfolder'].keys())}")
    """
    import os
    from collections import defaultdict
    
    if not client_folder.exists():
        raise FileNotFoundError(f"Client folder not found: {client_folder}")
    
    # Defaults
    if allowed_exts is None:
        allowed_exts = {'.pdf', '.docx', '.doc', '.txt', '.msg', '.m4a', '.mp3', '.wav', '.ogg', '.flac'}
    
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__MACOSX', 'node_modules', '.venv', 'venv', 'artifacts', 'output', '__pycache__'}
    
    # Force depth=0 si include_subfolders=False
    if not include_subfolders:
        max_depth = 0
    
    # Structures de résultats
    files = {
        'docx': [],
        'pdf': [],
        'txt': [],
        'audio': [],
        'msg': []
    }
    
    stats_by_type = defaultdict(int)
    stats_by_subfolder = defaultdict(lambda: defaultdict(int))
    total_files = 0
    truncated = False
    
    # Scan récursif avec os.walk
    for dirpath, dirnames, filenames in os.walk(client_folder, followlinks=follow_symlinks):
        # Calculer profondeur actuelle
        rel_path = os.path.relpath(dirpath, client_folder)
        if rel_path == '.':
            depth = 0
            subfolder_name = "Racine"
        else:
            depth = rel_path.count(os.sep) + 1
            # Nom du premier sous-dossier (ex: "01 Dossier personnel")
            subfolder_name = rel_path.split(os.sep)[0]
        
        # Arrêter la descente si profondeur max atteinte
        if depth > max_depth:
            dirnames[:] = []  # Empêche de descendre plus profond
            continue
        
        # Filtrer les sous-dossiers à ignorer
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        
        # Scanner les fichiers
        for filename in filenames:
            # Limite max_files
            if total_files >= max_files:
                truncated = True
                break
            
            # Ignorer fichiers temporaires Office (~$*.docx)
            if filename.startswith('~$'):
                continue
            
            # Ignorer .DS_Store
            if filename == '.DS_Store':
                continue
            
            # Vérifier extension
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in allowed_exts:
                continue
            
            # Ajouter le fichier
            file_path = Path(dirpath) / filename
            
            # Classer par type
            if file_ext in {'.docx', '.doc'}:
                files['docx'].append(file_path)
                file_type = 'docx'
            elif file_ext == '.pdf':
                files['pdf'].append(file_path)
                file_type = 'pdf'
            elif file_ext == '.txt':
                files['txt'].append(file_path)
                file_type = 'txt'
            elif file_ext == '.msg':
                files['msg'].append(file_path)
                file_type = 'msg'
            elif file_ext in {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}:
                files['audio'].append(file_path)
                file_type = 'audio'
            else:
                continue
            
            # Stats
            stats_by_type[file_type] += 1
            stats_by_subfolder[subfolder_name][file_type] += 1
            total_files += 1
        
        if truncated:
            break
    
    # Limiter stats_by_subfolder aux top 10 pour UI
    top_subfolders = dict(sorted(
        stats_by_subfolder.items(),
        key=lambda x: sum(x[1].values()),
        reverse=True
    )[:10])
    
    return {
        'files': files,
        'stats_by_type': dict(stats_by_type),
        'stats_by_subfolder': top_subfolders,
        'total_files': total_files,
        'truncated': truncated
    }

