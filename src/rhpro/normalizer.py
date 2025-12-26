"""
Normalizer — construit le dictionnaire normalisé de sortie
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from .segmenter import Segment
from .ruleset_loader import RulesetLoader
from .inline_extractor import InlineExtractor


class Normalizer:
    """Construit le dictionnaire normalisé à partir des segments mappés"""
    
    def __init__(self, ruleset: RulesetLoader):
        self.ruleset = ruleset
        self.content_rules = ruleset.content_rules
        self.never_invent = self.content_rules.get('never_invent_for', [])
        self.inline_extractor = InlineExtractor()
        self.inline_warnings: List[str] = []
    
    def normalize(self, segments: List[Segment]) -> Dict[str, Any]:
        """
        Construit le dict normalisé
        Retourne: {'normalized': dict, 'report': dict}
        """
        # Charger le template de sortie
        normalized = self._load_template()
        
        # Réinitialiser warnings
        self.inline_warnings = []
        
        # Remplir avec les segments mappés
        for segment in segments:
            if segment.mapped_section_id:
                self._fill_section(normalized, segment)
        
        # Post-traitement : extraire les sous-sections inline si nécessaire
        self._extract_inline_subsections(normalized, segments)
        
        # Générer le rapport
        report = self._generate_report(segments, normalized)
        
        return {
            'normalized': normalized,
            'report': report
        }
    
    def _load_template(self) -> Dict[str, Any]:
        """Charge le template JSON vide"""
        # Chemin relatif au projet
        template_path = Path(__file__).parent.parent.parent / 'schemas' / 'normalized.rhpro_v1.json'
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Fallback: template minimal
        return {
            "identity": {"name": "", "surname": "", "avs": ""},
            "participation_programme": "",
            "profession_formation": {"profession": "", "formation": ""},
            "tests": {},
            "discussion_assure": "",
            "competences": {"sociales": "", "professionnelles": ""},
            "incertitudes_obstacles": "",
            "orientation_formation": {"orientation": "", "stage": ""},
            "dossier_presentation": {},
            "conclusion": ""
        }
    
    def _fill_section(self, normalized: Dict[str, Any], segment: Segment):
        """Remplit une section du dict normalisé avec le contenu du segment"""
        section_id = segment.mapped_section_id
        section_config = self.ruleset.get_section_by_id(section_id)
        
        if not section_config:
            return
        
        # Extraire le contenu
        content = self._extract_content(segment, section_config)
        
        # Placer dans la structure
        self._set_nested_value(normalized, section_id, content)
    
    def _extract_content(self, segment: Segment, section_config: Dict[str, Any]) -> Any:
        """Extrait le contenu d'un segment selon la stratégie définie"""
        fill_strategy = section_config.get('fill_strategy', 'copy')
        
        # Vérifier si on ne doit jamais inventer
        if section_config['id'] in self.never_invent:
            if not segment.paragraphs:
                return ""
        
        # Stratégies de remplissage
        if fill_strategy == 'copy':
            return self._copy_raw(segment)
        elif fill_strategy == 'source_only':
            return self._copy_raw(segment)
        elif fill_strategy.startswith('summarize'):
            # Pour v1, on ne résume pas, on marque juste
            raw = self._copy_raw(segment)
            return raw if raw else ""
        else:
            return self._copy_raw(segment)
    
    def _copy_raw(self, segment: Segment) -> str:
        """Copie le texte brut des paragraphes"""
        if not segment.paragraphs:
            return ""
        
        lines = [p.text for p in segment.paragraphs]
        return "\n".join(lines)
    
    def _set_nested_value(self, data: Dict, path: str, value: Any):
        """Définit une valeur dans une structure imbriquée via chemin pointé"""
        keys = path.split('.')
        current = data
        
        for i, key in enumerate(keys[:-1]):
            if key not in current:
                current[key] = {}
            # Si current[key] est une string, on doit la convertir en dict
            # Cela arrive quand on a d'abord rempli la section parent, puis on essaie d'ajouter des enfants
            elif isinstance(current[key], str):
                current[key] = {}
            current = current[key]
        
        # Cas spécial pour les listes (ex: points_appui)
        last_key = keys[-1]
        if isinstance(value, str) and value:
            current[last_key] = value
        elif isinstance(value, list):
            current[last_key] = value
        elif isinstance(value, dict):
            current[last_key] = value
    
    def _extract_inline_subsections(self, normalized: Dict[str, Any], segments: List[Segment]):
        """
        Post-traitement: extrait les sous-sections inline depuis les sections parents
        quand les sous-sections n'ont pas été mappées séparément
        """
        # Sections parents qui peuvent contenir des sous-sections
        parent_sections = ['profession_formation', 'orientation_formation', 'competences']
        
        for parent_id in parent_sections:
            if parent_id not in normalized:
                continue
            
            parent_content = normalized[parent_id]
            
            # Si le parent est déjà un dict avec des valeurs, on ne touche pas
            if isinstance(parent_content, dict):
                # Vérifier si toutes les sous-sections sont déjà remplies
                all_filled = all(
                    v for v in parent_content.values() 
                    if isinstance(v, str) or isinstance(v, list)
                )
                if all_filled:
                    continue
            
            # Si le parent est une string, tenter l'extraction inline
            if isinstance(parent_content, str) and parent_content:
                subsections = self.inline_extractor.extract_subsections(parent_id, parent_content)
                
                if subsections:
                    # Remplacer le string par un dict
                    normalized[parent_id] = subsections
                else:
                    # Extraction a échoué
                    expected = self.inline_extractor.get_expected_subsections(parent_id)
                    if expected:
                        # Créer un dict vide avec les clés attendues
                        normalized[parent_id] = {key: "" for key in expected}
                        self.inline_warnings.append(
                            f"Inline split failed for {parent_id} (expected: {', '.join(expected)})"
                        )
    
    def _generate_report(self, segments: List[Segment], normalized: Dict[str, Any]) -> Dict[str, Any]:
        """Génère un rapport de couverture"""
        found_sections = []
        unknown_titles = []
        missing_required = []
        
        # Segments trouvés
        for segment in segments:
            if segment.mapped_section_id:
                found_sections.append({
                    'section_id': segment.mapped_section_id,
                    'title': segment.normalized_title,
                    'confidence': segment.confidence
                })
            else:
                unknown_titles.append(segment.normalized_title)
        
        # Sections requises manquantes
        all_required = []
        for section in self._iterate_all_sections():
            if section.get('required'):
                all_required.append(section['id'])
        
        # Vérifier quelles sections sont effectivement présentes et remplies
        for section_id in all_required:
            if not self._is_section_filled(normalized, section_id):
                missing_required.append(section_id)
        
        # Calcul de couvertures
        total_sections = len(list(self._iterate_all_sections()))
        coverage_ratio = len(found_sections) / total_sections if total_sections > 0 else 0.0
        
        # Coverage des sections requises uniquement
        required_coverage_ratio = 0.0
        if all_required:
            required_filled = len(all_required) - len(missing_required)
            required_coverage_ratio = required_filled / len(all_required)
        
        # Weighted coverage (parents clés comptent plus)
        weighted_coverage = self._calculate_weighted_coverage(normalized)
        
        # Warnings (inclure les inline warnings)
        warnings = self._generate_warnings(missing_required)
        warnings.extend(self.inline_warnings)
        
        return {
            'found_sections': found_sections,
            'missing_required_sections': missing_required,
            'unknown_titles': unknown_titles,
            'coverage_ratio': round(coverage_ratio, 2),
            'required_coverage_ratio': round(required_coverage_ratio, 2),
            'weighted_coverage': round(weighted_coverage, 2),
            'warnings': warnings
        }
    
    def _generate_warnings(self, missing_required: List[str]) -> List[str]:
        """Génère des warnings pour les sections manquantes"""
        warnings = []
        for section_id in missing_required:
            warnings.append(f"Required section missing: {section_id}")
        return warnings
    
    def _is_section_filled(self, normalized: Dict[str, Any], section_id: str) -> bool:
        """Vérifie si une section est effectivement remplie dans le dict normalisé"""
        keys = section_id.split('.')
        current = normalized
        
        for key in keys:
            if key not in current:
                return False
            current = current[key]
        
        # Vérifier si la valeur est non vide
        if isinstance(current, str):
            return bool(current.strip())
        elif isinstance(current, dict):
            # Pour un dict, vérifier s'il contient au moins une valeur non vide
            return any(
                (isinstance(v, str) and v.strip()) or
                (isinstance(v, list) and v) or
                (isinstance(v, dict) and v)
                for v in current.values()
            )
        elif isinstance(current, list):
            return bool(current)
        
        return False
    
    def _calculate_weighted_coverage(self, normalized: Dict[str, Any]) -> float:
        """
        Calcule une couverture pondérée où les sections clés comptent plus
        
        Poids:
        - identity: 2x
        - profession_formation: 3x
        - orientation_formation: 3x
        - tests: 2x
        - autres: 1x
        """
        weights = {
            'identity': 2.0,
            'profession_formation': 3.0,
            'orientation_formation': 3.0,
            'tests': 2.0,
            'competences': 1.5,
            'conclusion': 1.5
        }
        
        total_weight = 0.0
        filled_weight = 0.0
        
        for section_id in normalized.keys():
            weight = weights.get(section_id, 1.0)
            total_weight += weight
            
            if self._is_section_filled(normalized, section_id):
                filled_weight += weight
        
        return filled_weight / total_weight if total_weight > 0 else 0.0
    
    def _iterate_all_sections(self):
        """Itère sur toutes les sections"""
        def iterate_recursive(sections):
            for section in sections:
                yield section
                children = section.get('children', [])
                if children:
                    yield from iterate_recursive(children)
        
        return iterate_recursive(self.ruleset.sections)


def normalize_segments(segments: List[Segment], ruleset: RulesetLoader) -> Dict[str, Any]:
    """Helper function pour normaliser les segments"""
    normalizer = Normalizer(ruleset)
    return normalizer.normalize(segments)
