"""
Mapper — mapping des titres détectés vers les sections canoniques
"""
import re
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

from .segmenter import Segment
from .ruleset_loader import RulesetLoader


# Liste des patterns de titres à ignorer (titres de document générique)
IGNORE_PATTERNS = [
    r"^BILAN\s+D['']ORIENTATION",
    r"^RAPPORT\s+D['']ORIENTATION",
    r"^DOCUMENT\s+D['']ORIENTATION",
    r"^BILAN\s+PROFESSIONNEL",
]


class TitleMapper:
    """Map les titres détectés vers les sections canoniques du ruleset"""
    
    def __init__(self, ruleset: RulesetLoader):
        self.ruleset = ruleset
        self.matching_config = ruleset.title_matching
        self.method_order = self.matching_config.get('method_order', ['exact', 'contains', 'regex', 'fuzzy'])
        self.fuzzy_threshold = self.matching_config.get('fuzzy_threshold', 0.84)
    
    def map_segments(self, segments: List[Segment]) -> List[Segment]:
        """Map chaque segment à une section canonique"""
        for segment in segments:
            # Vérifier si le titre doit être ignoré
            if self._should_ignore_title(segment.normalized_title):
                segment.mapped_section_id = None
                segment.confidence = 0.0
                continue
            
            match = self._find_best_match(segment.normalized_title)
            if match:
                segment.mapped_section_id = match['section_id']
                segment.confidence = match['confidence']
        
        return segments
    
    def _should_ignore_title(self, title: str) -> bool:
        """Vérifie si un titre doit être ignoré (titre de document générique)"""
        for pattern in IGNORE_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return True
        return False
    
    def _find_best_match(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Trouve la meilleure correspondance pour un titre
        Retourne: {'section_id': str, 'confidence': float} ou None
        """
        # Tester chaque méthode dans l'ordre défini
        for method in self.method_order:
            if method == 'exact':
                result = self._match_exact(title)
            elif method == 'contains':
                result = self._match_contains(title)
            elif method == 'regex':
                result = self._match_regex(title)
            elif method == 'fuzzy':
                result = self._match_fuzzy(title)
            else:
                continue
            
            if result:
                return result
        
        return None
    
    def _match_exact(self, title: str) -> Optional[Dict[str, Any]]:
        """Matching exact (case-insensitive avec normalisation robuste)"""
        title_normalized = self._normalize_title_robust(title)
        
        for section in self._iterate_all_sections():
            anchors = section.get('anchors', {}).get('any', [])
            for anchor in anchors:
                if 'exact' in anchor:
                    anchor_normalized = self._normalize_title_robust(anchor['exact'])
                    if title_normalized == anchor_normalized:
                        return {
                            'section_id': section['id'],
                            'confidence': 1.0,
                            'method': 'exact'
                        }
        
        return None
    
    def _normalize_title_robust(self, text: str) -> str:
        """
        Normalisation robuste de titre:
        - casefold (lowercase unicode-aware)
        - retrait ponctuation
        - collapse espaces
        - retrait accents
        
        But: "Orientation, Formation & STage" == "orientation formation stage"
        """
        import unicodedata
        import re
        
        # 1. Casefold (unicode-aware lowercase)
        text = text.casefold()
        
        # 2. Retrait accents (NFD + filtrage)
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # 3. Retrait ponctuation (garder espaces et alphanum)
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # 4. Collapse espaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _match_contains(self, title: str) -> Optional[Dict[str, Any]]:
        """Matching par substring (case-insensitive)"""
        title_lower = title.lower()
        
        for section in self._iterate_all_sections():
            anchors = section.get('anchors', {}).get('any', [])
            for anchor in anchors:
                if 'contains' in anchor:
                    anchor_text = anchor['contains'].lower()
                    if anchor_text in title_lower:
                        return {
                            'section_id': section['id'],
                            'confidence': 0.9,
                            'method': 'contains'
                        }
        
        return None
    
    def _match_regex(self, title: str) -> Optional[Dict[str, Any]]:
        """Matching par regex"""
        for section in self._iterate_all_sections():
            anchors = section.get('anchors', {}).get('any', [])
            for anchor in anchors:
                if 'regex' in anchor:
                    pattern = anchor['regex']
                    if re.search(pattern, title, re.IGNORECASE):
                        return {
                            'section_id': section['id'],
                            'confidence': 0.85,
                            'method': 'regex'
                        }
        
        return None
    
    def _match_fuzzy(self, title: str) -> Optional[Dict[str, Any]]:
        """Matching fuzzy (similarité de chaînes)"""
        title_lower = title.lower()
        best_match = None
        best_ratio = 0.0
        
        for section in self._iterate_all_sections():
            anchors = section.get('anchors', {}).get('any', [])
            for anchor in anchors:
                # On teste tous les types d'anchors en fuzzy
                anchor_text = None
                if 'exact' in anchor:
                    anchor_text = anchor['exact']
                elif 'contains' in anchor:
                    anchor_text = anchor['contains']
                
                if anchor_text:
                    anchor_lower = anchor_text.lower()
                    ratio = SequenceMatcher(None, title_lower, anchor_lower).ratio()
                    
                    if ratio >= self.fuzzy_threshold and ratio > best_ratio:
                        best_ratio = ratio
                        best_match = {
                            'section_id': section['id'],
                            'confidence': ratio,
                            'method': 'fuzzy'
                        }
        
        return best_match
    
    def _iterate_all_sections(self):
        """Itère sur toutes les sections (y compris children) de façon plate"""
        def iterate_recursive(sections):
            for section in sections:
                yield section
                children = section.get('children', [])
                if children:
                    yield from iterate_recursive(children)
        
        return iterate_recursive(self.ruleset.sections)


def map_segments_to_sections(segments: List[Segment], ruleset: RulesetLoader) -> List[Segment]:
    """Helper function pour mapper les segments"""
    mapper = TitleMapper(ruleset)
    return mapper.map_segments(segments)
