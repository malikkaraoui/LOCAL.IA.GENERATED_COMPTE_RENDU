"""
Parse Bilan — Point d'entrée principal pour parser un DOCX RH-Pro
"""
from pathlib import Path
from typing import Dict, Any

from .ruleset_loader import load_ruleset
from .docx_structure import extract_paragraphs_from_docx
from .segmenter import segment_paragraphs
from .mapper import map_segments_to_sections
from .normalizer import normalize_segments


def parse_bilan_docx_to_normalized(docx_path: str, ruleset_path: str) -> Dict[str, Any]:
    """
    Parse un document DOCX RH-Pro et retourne un dictionnaire normalisé
    
    Args:
        docx_path: Chemin vers le fichier DOCX
        ruleset_path: Chemin vers le ruleset YAML
    
    Returns:
        dict avec clés:
        - 'normalized': dict normalisé selon le schéma
        - 'report': dict avec coverage, warnings, etc.
    
    Example:
        >>> result = parse_bilan_docx_to_normalized(
        ...     'bilan.docx',
        ...     'config/rulesets/rhpro_v1.yaml'
        ... )
        >>> print(result['report']['coverage_ratio'])
        0.85
    """
    # Validation des fichiers
    docx_path_obj = Path(docx_path)
    ruleset_path_obj = Path(ruleset_path)
    
    if not docx_path_obj.exists():
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")
    
    if not ruleset_path_obj.exists():
        raise FileNotFoundError(f"Ruleset file not found: {ruleset_path}")
    
    # Pipeline de traitement
    
    # 1. Charger le ruleset
    ruleset = load_ruleset(str(ruleset_path_obj))
    
    # 2. Extraire les paragraphes du DOCX
    paragraphs = extract_paragraphs_from_docx(str(docx_path_obj))
    
    if not paragraphs:
        return {
            'normalized': {},
            'report': {
                'found_sections': [],
                'missing_required_sections': [],
                'unknown_titles': [],
                'coverage_ratio': 0.0,
                'warnings': ['No paragraphs extracted from DOCX']
            }
        }
    
    # 3. Segmenter (détecter les titres)
    segments = segment_paragraphs(paragraphs, ruleset)
    
    # 4. Mapper les titres aux sections canoniques
    segments = map_segments_to_sections(segments, ruleset)
    
    # 5. Normaliser (construire le dict final)
    result = normalize_segments(segments, ruleset)
    
    return result


def parse_bilan_from_paths(
    docx_path: str,
    ruleset_path: str = None
) -> Dict[str, Any]:
    """
    Variante avec ruleset par défaut
    
    Args:
        docx_path: Chemin vers le fichier DOCX
        ruleset_path: Chemin vers le ruleset (optionnel, utilise rhpro_v1.yaml par défaut)
    
    Returns:
        dict avec 'normalized' et 'report'
    """
    if ruleset_path is None:
        # Déterminer le chemin du ruleset par défaut
        project_root = Path(__file__).parent.parent.parent
        ruleset_path = str(project_root / 'config' / 'rulesets' / 'rhpro_v1.yaml')
    
    return parse_bilan_docx_to_normalized(docx_path, ruleset_path)
