"""
RH-Pro ruleset loader — charge et valide le YAML de configuration
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


class RulesetLoader:
    """Charge et expose la configuration du ruleset RH-Pro"""
    
    def __init__(self, ruleset_path: str):
        self.ruleset_path = Path(ruleset_path)
        self._data: Dict[str, Any] = {}
        self._load()
    
    def _load(self):
        """Charge le fichier YAML"""
        if not self.ruleset_path.exists():
            raise FileNotFoundError(f"Ruleset not found: {self.ruleset_path}")
        
        with open(self.ruleset_path, 'r', encoding='utf-8') as f:
            self._data = yaml.safe_load(f)
        
        # Validation basique
        required_keys = ['version', 'language', 'doc_type', 'sections']
        for key in required_keys:
            if key not in self._data:
                raise ValueError(f"Missing required key in ruleset: {key}")
    
    @property
    def version(self) -> str:
        return self._data.get('version', '')
    
    @property
    def language(self) -> str:
        return self._data.get('language', 'fr')
    
    @property
    def doc_type(self) -> str:
        return self._data.get('doc_type', '')
    
    @property
    def normalize_config(self) -> Dict[str, bool]:
        """Config de normalisation des titres"""
        return self._data.get('normalize', {})
    
    @property
    def heading_detection(self) -> Dict[str, Any]:
        """Config de détection des titres"""
        return self._data.get('heading_detection', {})
    
    @property
    def title_matching(self) -> Dict[str, Any]:
        """Config de matching des titres"""
        return self._data.get('title_matching', {})
    
    @property
    def sections(self) -> List[Dict[str, Any]]:
        """Liste des sections canoniques"""
        return self._data.get('sections', [])
    
    @property
    def content_rules(self) -> Dict[str, Any]:
        """Règles de contenu (anti-hallucination)"""
        return self._data.get('content_rules', {})
    
    @property
    def raw_data(self) -> Dict[str, Any]:
        """Données brutes du ruleset (pour accès direct)"""
        return self._data
    
    def get_section_by_id(self, section_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une section par son ID (supporte la notation pointée pour children)"""
        
        def find_in_sections(sections: List[Dict], sid: str) -> Optional[Dict]:
            for section in sections:
                if section.get('id') == sid:
                    return section
                # Recherche dans les children
                children = section.get('children', [])
                if children:
                    found = find_in_sections(children, sid)
                    if found:
                        return found
            return None
        
        return find_in_sections(self.sections, section_id)
    
    def get_all_section_ids(self) -> List[str]:
        """Retourne tous les IDs de sections (flatten)"""
        ids = []
        
        def collect_ids(sections: List[Dict]):
            for section in sections:
                ids.append(section.get('id', ''))
                children = section.get('children', [])
                if children:
                    collect_ids(children)
        
        collect_ids(self.sections)
        return [i for i in ids if i]    
    def get_required_paths(self) -> List[str]:
        """
        Retourne tous les chemins (IDs) des sections/champs marqués required=true
        
        Returns:
            Liste des IDs de sections requises (ex: ['identity', 'profession_formation', ...])
        """
        required = []
        
        def collect_required(sections: List[Dict]):
            for section in sections:
                if section.get('required', False):
                    section_id = section.get('id', '')
                    if section_id:
                        required.append(section_id)
                
                # Parcourir récursivement les children
                children = section.get('children', [])
                if children:
                    collect_required(children)
        
        collect_required(self.sections)
        return required

def load_ruleset(ruleset_path: str) -> RulesetLoader:
    """Fonction helper pour charger un ruleset"""
    return RulesetLoader(ruleset_path)
