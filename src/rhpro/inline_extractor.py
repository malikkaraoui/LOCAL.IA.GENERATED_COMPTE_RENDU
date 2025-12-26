"""
Inline Extractor — split les sections parents en sous-sections
Quand un parent contient plusieurs sous-sections mais qu'elles n'ont pas été mappées séparément
"""
import re
from typing import Dict, Any, Optional, List


class InlineExtractor:
    """Extrait les sous-sections depuis le texte d'une section parent"""
    
    # Patterns pour extraire les sous-sections
    PATTERNS = {
        'profession_formation': {
            'profession': r'(?ims)\bProfession\b\s*(?:\n|:)\s*(.+?)(?=\n\s*\bFormation\b\s*(?:\n|:)|\Z)',
            'formation': r'(?ims)\bFormation\b\s*(?:\n|:)\s*(.+?)(?=\n\s*\b[A-ZÀ-ÖØ-Þ].{2,}|\Z)'
        },
        'orientation_formation': {
            'orientation': r'(?ims)\bOrientation\b\s*(?:\n|:)\s*(.+?)(?=\n\s*\bStage\b\s*(?:\n|:)|\Z)',
            'stage': r'(?ims)\bStage\b\s*(?:\n|:)\s*(.+?)\Z'
        },
        'competences': {
            'sociales': r'(?ims)\bSociales\b\s*(?:\n|:)\s*(.+?)(?=\n\s*\bProfessionnelles\b\s*(?:\n|:)|\Z)',
            'professionnelles': r'(?ims)\bProfessionnelles\b\s*(?:\n|:)\s*(.+?)\Z'
        }
    }
    
    def extract_subsections(self, section_id: str, content: str) -> Optional[Dict[str, str]]:
        """
        Tente d'extraire les sous-sections depuis le contenu d'une section parent
        
        Args:
            section_id: ID de la section parent (ex: "profession_formation")
            content: Contenu texte complet de la section
        
        Returns:
            Dict avec les sous-sections extraites ou None si échec
        """
        if not content or section_id not in self.PATTERNS:
            return None
        
        patterns = self.PATTERNS[section_id]
        result = {}
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                extracted = match.group(1).strip()
                # Nettoyer les sauts de lignes multiples
                extracted = re.sub(r'\n\s*\n', '\n', extracted)
                result[key] = extracted
            else:
                result[key] = ""
        
        # Retourner None si aucune sous-section n'a été extraite
        if not any(result.values()):
            return None
        
        return result
    
    def can_extract(self, section_id: str) -> bool:
        """Vérifie si on peut extraire des sous-sections pour cette section"""
        return section_id in self.PATTERNS
    
    def get_expected_subsections(self, section_id: str) -> List[str]:
        """Retourne la liste des sous-sections attendues pour une section"""
        if section_id in self.PATTERNS:
            return list(self.PATTERNS[section_id].keys())
        return []


def extract_inline_subsections(section_id: str, content: str) -> Optional[Dict[str, str]]:
    """Helper function pour extraire les sous-sections"""
    extractor = InlineExtractor()
    return extractor.extract_subsections(section_id, content)
