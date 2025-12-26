"""
Segmenter — détection des titres et construction des segments
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .docx_structure import Paragraph
from .ruleset_loader import RulesetLoader


@dataclass
class Segment:
    """Représente un segment (titre + paragraphes associés)"""
    raw_title: str
    normalized_title: str
    level: int
    paragraphs: List[Paragraph] = field(default_factory=list)
    mapped_section_id: Optional[str] = None
    confidence: float = 0.0
    
    def __repr__(self):
        return f"<Segment level={self.level} title='{self.normalized_title[:40]}' paras={len(self.paragraphs)}>"


class Segmenter:
    """Détecte les titres et construit les segments"""
    
    def __init__(self, ruleset: RulesetLoader):
        self.ruleset = ruleset
        self.heading_config = ruleset.heading_detection
        self.normalize_config = ruleset.normalize_config
    
    def segment(self, paragraphs: List[Paragraph]) -> List[Segment]:
        """Segmente les paragraphes en sections basées sur les titres détectés"""
        segments = []
        current_segment: Optional[Segment] = None
        
        for para in paragraphs:
            heading_info = self._detect_heading(para)
            
            if heading_info:
                # Nouveau titre détecté
                if current_segment:
                    segments.append(current_segment)
                
                current_segment = Segment(
                    raw_title=para.text,
                    normalized_title=self._normalize_title(para.text),
                    level=heading_info['level']
                )
            else:
                # Contenu du segment courant
                if current_segment:
                    current_segment.paragraphs.append(para)
                else:
                    # Contenu avant le premier titre (généralement à ignorer ou mettre en "preamble")
                    pass
        
        # Ajouter le dernier segment
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def _detect_heading(self, para: Paragraph) -> Optional[Dict[str, Any]]:
        """
        Détecte si un paragraphe est un titre
        Retourne: {'level': int} ou None
        
        Ordre de priorité:
        1) by_style
        2) by_regex
        3) by_heuristics
        """
        # 1) Détection par style Word
        if self.heading_config.get('by_style', {}).get('enabled'):
            result = self._detect_by_style(para)
            if result:
                return result
        
        # 2) Détection par regex
        if self.heading_config.get('by_regex', {}).get('enabled'):
            result = self._detect_by_regex(para)
            if result:
                return result
        
        # 3) Détection par heuristiques
        if self.heading_config.get('by_heuristics', {}).get('enabled'):
            result = self._detect_by_heuristics(para)
            if result:
                return result
        
        return None
    
    def _detect_by_style(self, para: Paragraph) -> Optional[Dict[str, Any]]:
        """Détection basée sur le style Word"""
        styles_config = self.heading_config.get('by_style', {}).get('styles', [])
        
        for style_def in styles_config:
            if para.style_name == style_def['name']:
                return {'level': style_def['level']}
        
        return None
    
    def _detect_by_regex(self, para: Paragraph) -> Optional[Dict[str, Any]]:
        """Détection basée sur des patterns regex"""
        patterns = self.heading_config.get('by_regex', {}).get('patterns', [])
        
        for pattern_def in patterns:
            regex = pattern_def.get('regex', '')
            if re.match(regex, para.text):
                # Déduire le level du nombre de points dans la numérotation
                if para.numbering_prefix:
                    level = para.numbering_prefix.count('.') + 1
                else:
                    level = 1
                return {'level': level}
        
        return None
    
    def _detect_by_heuristics(self, para: Paragraph) -> Optional[Dict[str, Any]]:
        """Détection par heuristiques (court + gras)"""
        config = self.heading_config.get('by_heuristics', {})
        max_length = config.get('max_length', 90)
        prefer_bold = config.get('prefer_bold', True)
        
        # Filtre anti-phrase: rejeter si c'est une phrase (termine par . ou trop de mots)
        text = para.text.strip()
        word_count = len(text.split())
        if text.endswith('.') or word_count > 15:
            return None
        
        # Conditions: texte court et éventuellement en gras
        if len(para.text) <= max_length:
            if prefer_bold and para.is_bold:
                return {'level': 2}  # Level par défaut
            elif not prefer_bold:
                return {'level': 2}
        
        return None
    
    def _normalize_title(self, text: str) -> str:
        """Normalise un titre selon la config"""
        result = text
        
        if self.normalize_config.get('trim'):
            result = result.strip()
        
        if self.normalize_config.get('collapse_whitespace'):
            result = re.sub(r'\s+', ' ', result)
        
        if self.normalize_config.get('strip_trailing_colon'):
            result = result.rstrip(':').strip()
        
        if self.normalize_config.get('uppercase'):
            result = result.upper()
        
        if self.normalize_config.get('remove_nbsp'):
            result = result.replace('\xa0', ' ')
        
        return result


def segment_paragraphs(paragraphs: List[Paragraph], ruleset: RulesetLoader) -> List[Segment]:
    """Helper function pour segmenter les paragraphes"""
    segmenter = Segmenter(ruleset)
    return segmenter.segment(paragraphs)
