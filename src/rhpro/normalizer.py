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
        self.provenance: Dict[str, Dict[str, Any]] = {}  # Track provenance
        self.gate_profile_override: Optional[str] = None  # Override manuel du profil
    
    def normalize(self, segments: List[Segment], gate_profile_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Construit le dict normalisé
        
        Args:
            segments: Segments à normaliser
            gate_profile_override: Si fourni, force ce profil au lieu de l'auto-détection
            
        Retourne: {'normalized': dict, 'report': dict, 'provenance': dict}
        """
        # Stocker l'override pour l'utiliser dans _generate_report
        self.gate_profile_override = gate_profile_override
        
        # Charger le template de sortie
        normalized = self._load_template()
        
        # Réinitialiser warnings et provenance
        self.inline_warnings = []
        self.provenance = {}
        
        # Optimisation 4: Déduplication des segments
        deduplicated = self._deduplicate_segments(segments)
        
        # Remplir avec les segments mappés
        for segment in deduplicated:
            if segment.mapped_section_id:
                self._fill_section(normalized, segment)
        
        # Post-traitement : extraire les sous-sections inline si nécessaire
        self._extract_inline_subsections(normalized, segments)
        
        # Générer le rapport
        report = self._generate_report(deduplicated, normalized)
        
        return {
            'normalized': normalized,
            'report': report,
            'provenance': self.provenance
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
        
        # Enregistrer la provenance
        self._record_provenance(segment)
        
        # Extraire le contenu
        content = self._extract_content(segment, section_config)
        
        # Cas spécial : identity -> extraire les champs automatiquement
        if section_id == 'identity':
            # Essayer d'extraire depuis le contenu ou depuis le titre lui-même
            text_to_analyze = content if content else segment.raw_title
            if text_to_analyze:
                identity_data = self._extract_identity_fields(text_to_analyze)
                # Merger avec le contenu existant
                if 'identity' not in normalized:
                    normalized['identity'] = {}
                for key, value in identity_data.items():
                    if value and not normalized['identity'].get(key):  # Ne remplacer que si vide
                        normalized['identity'][key] = value
            return
        
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
    
    def _extract_identity_fields(self, text: str) -> Dict[str, str]:
        """Extrait AVS, nom, prénom depuis le texte identity"""
        import re
        
        result = {"avs": "", "name": "", "surname": "", "full_name": ""}
        
        # Extraction AVS (tolérant: espaces, points, tirets)
        avs_pattern = r'756[\s\.\-]?\d{4}[\s\.\-]?\d{4}[\s\.\-]?\d{2}'
        avs_match = re.search(avs_pattern, text)
        if avs_match:
            result['avs'] = avs_match.group().replace(' ', '.').replace('-', '.')
        
        # Extraction nom complet (pattern Monsieur/Madame Prénom NOM)
        # Pattern simplifié et robuste
        name_pattern = r'(?:Monsieur|Madame|M\.|Mme)\s+(.+?)\s*[\u2013\u2014\-]\s*756'
        name_match = re.search(name_pattern, text, re.IGNORECASE)
        if name_match:
            full_name = name_match.group(1).strip()
            result['full_name'] = full_name
            
            # Tenter de séparer prénom/nom (dernier mot = nom)
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                result['surname'] = name_parts[-1]
                result['name'] = ' '.join(name_parts[:-1])
            elif len(name_parts) == 1:
                result['surname'] = name_parts[0]
        
        return result
    
    def _record_provenance(self, segment: Segment):
        """
        Enregistre la provenance d'un segment pour audit/debug
        
        Inclut:
        - source_title: titre du segment source
        - confidence: confiance du mapping
        - paragraph_range: [start, end] indices des paragraphes
        - paragraph_count: nombre de paragraphes
        - snippet: extrait court du contenu (100-200 chars)
        """
        section_id = segment.mapped_section_id
        if not section_id:
            return
        
        # Générer snippet
        snippet = ""
        if segment.paragraphs:
            full_text = " ".join(p.text for p in segment.paragraphs[:3])  # 3 premiers paras
            snippet = full_text[:200].replace('\n', ' ').strip()
            if len(full_text) > 200:
                snippet += "..."
        elif segment.raw_title:
            snippet = segment.raw_title[:200]
        
        # Enregistrer
        self.provenance[section_id] = {
            'source_title': segment.raw_title,
            'normalized_title': segment.normalized_title,
            'confidence': round(segment.confidence, 2),
            'paragraph_count': len(segment.paragraphs),
            'snippet': snippet,
            'level': segment.level
        }
    
    def _deduplicate_segments(self, segments: List[Segment]) -> List[Segment]:
        """
        Déduplique les segments mappés au même section_id
        Garde le segment avec la meilleure confidence ou le plus long contenu
        """
        from collections import defaultdict
        import re
        
        grouped = defaultdict(list)
        
        # Grouper par section_id
        for segment in segments:
            if segment.mapped_section_id:
                grouped[segment.mapped_section_id].append(segment)
        
        deduplicated = []
        
        for section_id, segs in grouped.items():
            if len(segs) == 1:
                deduplicated.append(segs[0])
            else:
                # Plusieurs segments pour la même section
                # Cas spécial pour identity : préférer celui avec AVS dans le titre
                if section_id == 'identity':
                    avs_pattern = r'756[\s\.\-]?\d{4}'
                    for seg in segs:
                        if re.search(avs_pattern, seg.raw_title):
                            deduplicated.append(seg)
                            break
                    else:
                        # Aucun avec AVS, prendre le meilleur
                        best = max(segs, key=lambda s: (s.confidence, len(s.paragraphs)))
                        deduplicated.append(best)
                else:
                    # Garder celui avec la meilleure confidence
                    best = max(segs, key=lambda s: (s.confidence, len(s.paragraphs)))
                    deduplicated.append(best)
        
        # Ajouter les segments non mappés
        for segment in segments:
            if not segment.mapped_section_id:
                deduplicated.append(segment)
        
        return deduplicated
    
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
                old_value = current[key]
                current[key] = {"_raw": old_value} if old_value else {}
            current = current[key]
        
        # Cas spécial pour les listes (ex: points_appui)
        last_key = keys[-1]
        
        # Gestion des collisions propre
        if last_key in current:
            existing = current[last_key]
            # String sur string : merger intelligemment
            if isinstance(existing, str) and isinstance(value, str):
                if value and value != existing:
                    # Garder le plus long ou concat si très différent
                    if len(value) > len(existing) * 1.5:
                        current[last_key] = value
                    elif value not in existing and existing not in value:
                        current[last_key] = existing + "\n\n" + value
                return
            # Dict sur dict : ne rien faire (déjà géré)
            elif isinstance(existing, dict) and isinstance(value, dict):
                return
        
        # Assignation normale
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
        all_weighted = []
        for section in self._iterate_all_sections():
            if section.get('required'):
                all_required.append(section['id'])
            if section.get('weighted'):
                all_weighted.append(section['id'])
        
        # Vérifier quelles sections sont effectivement présentes et remplies
        for section_id in all_required:
            if not self._is_section_filled(normalized, section_id):
                missing_required.append(section_id)
        
        # Warnings pour sections weighted manquantes (pas bloquant mais informatif)
        missing_weighted = []
        for section_id in all_weighted:
            if not self._is_section_filled(normalized, section_id):
                missing_weighted.append(section_id)
        
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
        
        # Détection des placeholders (textes à compléter)
        placeholders = self._detect_placeholders(normalized)
        
        # Warnings (inclure les inline warnings)
        warnings = self._generate_warnings(missing_required, missing_weighted)
        warnings.extend(self.inline_warnings)
        
        # Sélection du profil (auto ou override)
        if self.gate_profile_override:
            gate_profile_id = self.gate_profile_override
            signals = {'forced': True, 'profile': gate_profile_id}
        else:
            # Sélection automatique du profil
            gate_profile_id, signals = self._choose_gate_profile(segments, found_sections)
        
        # Gating production: GO / NO-GO
        production_gate = self._evaluate_production_gate(
            missing_required, 
            required_coverage_ratio, 
            len(unknown_titles),
            len(placeholders),
            profile_id=gate_profile_id
        )
        production_gate['signals'] = signals
        
        return {
            'found_sections': found_sections,
            'missing_required_sections': missing_required,
            'unknown_titles': unknown_titles,
            'coverage_ratio': round(coverage_ratio, 2),
            'required_coverage_ratio': round(required_coverage_ratio, 2),
            'weighted_coverage': round(weighted_coverage, 2),
            'warnings': warnings,
            'placeholders': placeholders,
            'production_gate': production_gate
        }
    
    def _generate_warnings(self, missing_required: List[str], missing_weighted: List[str] = None) -> List[str]:
        """Génère des warnings pour les sections manquantes"""
        warnings = []
        for section_id in missing_required:
            warnings.append(f"Required section missing: {section_id}")
        
        if missing_weighted:
            for section_id in missing_weighted:
                warnings.append(f"Weighted section missing (not blocking): {section_id}")
        
        return warnings
    
    def _detect_placeholders(self, normalized: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Détecte les placeholders / textes à compléter dans le contenu
        Retourne une liste de {'path': str, 'text': str, 'pattern': str}
        """
        import re
        
        placeholders = []
        
        # Patterns de placeholders courants
        patterns = [
            (r'\bMETTRE\b', 'METTRE'),
            (r'\bÀ COMPLÉTER\b', 'À COMPLÉTER'),
            (r'\bTODO\b', 'TODO'),
            (r'\bXXXX+\b', 'XXXX'),
            (r'\.{3,}', '...'),  # Points de suspension multiples
            (r'\[\s*\]', '[ ]'),  # Crochets vides
            (r'\b__+\b', '___'),  # Underscores multiples
        ]
        
        def scan_recursive(data, path=''):
            if isinstance(data, str) and data.strip():
                for pattern, label in patterns:
                    matches = re.finditer(pattern, data, re.IGNORECASE)
                    for match in matches:
                        # Extraire le contexte (50 chars avant/après)
                        start = max(0, match.start() - 50)
                        end = min(len(data), match.end() + 50)
                        context = data[start:end].replace('\n', ' ')
                        
                        placeholders.append({
                            'path': path,
                            'pattern': label,
                            'context': context.strip()
                        })
            elif isinstance(data, dict):
                for key, value in data.items():
                    new_path = f"{path}.{key}" if path else key
                    scan_recursive(value, new_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    new_path = f"{path}[{i}]"
                    scan_recursive(item, new_path)
        
        scan_recursive(normalized)
        return placeholders
    
    def _choose_gate_profile(self, segments: List[Segment], found_sections: List[Dict]) -> tuple:
        """
        Choisit automatiquement le profil de production gate selon les signaux détectés.
        
        Heuristique (ordre important):
        1) Si "stage" détecté => profile="stage"
        2) Sinon si >=2 sections parmi tests/vocation/profil_emploi/ressources_professionnelles => profile="bilan_complet"
        3) Sinon si "LAI 15" ou "LAI 18" détecté => profile="placement_suivi"
        4) Sinon => profile="placement_suivi" (défaut tolérant)
        
        Args:
            segments: Liste des segments
            found_sections: Sections trouvées avec leurs titres
            
        Returns:
            (profile_id, signals_dict)
        """
        # Récupérer le profil par défaut depuis le ruleset
        gate_config = self.ruleset.raw_data.get('production_gate', {})
        default_profile = gate_config.get('default_profile', 'placement_suivi')
        
        # Collecter tous les titres normalisés (en minuscules pour comparaison)
        all_titles = []
        for segment in segments:
            if segment.normalized_title:
                all_titles.append(segment.normalized_title.lower())
        for section in found_sections:
            if section.get('title'):
                all_titles.append(section['title'].lower())
        
        # Collecter les section_ids trouvés
        found_section_ids = [s.get('section_id', '') for s in found_sections if s.get('section_id')]
        
        # Dédupliquer
        all_titles = list(set(all_titles))
        
        # Initialiser les signaux
        signals = {
            'has_stage': False,
            'has_tests': False,
            'has_vocation': False,
            'has_profil_emploi': False,
            'has_ressources_professionnelles': False,
            'has_lai15': False,
            'has_lai18': False,
            'matched_titles': [],
            'bilan_complet_sections_count': 0
        }
        
        # Signal 1: Détection de "stage"
        stage_keywords = ['stage', 'bilan de stage', 'orientation formation stage']
        for title in all_titles:
            for keyword in stage_keywords:
                if keyword in title:
                    signals['has_stage'] = True
                    signals['matched_titles'].append(f"stage:{title[:50]}")
                    break
        
        # Vérifier aussi les section_ids
        for section_id in found_section_ids:
            if 'stage' in section_id.lower():
                signals['has_stage'] = True
                break
        
        if signals['has_stage']:
            return ('stage', signals)
        
        # Signal 2: Détection sections bilan complet (tests, vocation, profil_emploi, ressources_professionnelles)
        for section_id in found_section_ids:
            section_id_lower = section_id.lower()
            if section_id.startswith('tests') or 'tests' in section_id_lower:
                signals['has_tests'] = True
                signals['bilan_complet_sections_count'] += 1
            if 'vocation' in section_id_lower:
                signals['has_vocation'] = True
                signals['bilan_complet_sections_count'] += 1
            if 'profil_emploi' in section_id_lower:
                signals['has_profil_emploi'] = True
                signals['bilan_complet_sections_count'] += 1
            if 'ressources_professionnelles' in section_id_lower:
                signals['has_ressources_professionnelles'] = True
                signals['bilan_complet_sections_count'] += 1
        
        if signals['bilan_complet_sections_count'] >= 2:
            return ('bilan_complet', signals)
        
        # Signal 3: Détection LAI 15 ou LAI 18
        lai_keywords = ['lai 15', 'lai15', 'lai 18', 'lai18', 'lai-15', 'lai-18']
        for title in all_titles:
            for keyword in lai_keywords:
                if keyword in title:
                    if '15' in keyword:
                        signals['has_lai15'] = True
                    else:
                        signals['has_lai18'] = True
                    signals['matched_titles'].append(f"lai:{title[:50]}")
                    break
        
        if signals['has_lai15'] or signals['has_lai18']:
            return ('placement_suivi', signals)
        
        # Défaut: placement_suivi (tolérant)
        return (default_profile, signals)
    
    def _evaluate_production_gate(self, missing_required: List[str], 
                                   required_coverage: float,
                                   unknown_titles_count: int,
                                   placeholders_count: int,
                                   profile_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Évalue si le document est prêt pour la production (GO / NO-GO)
        Utilise les seuils du profil spécifié et applique le filtrage via ignore_required_prefixes.
        
        Args:
            missing_required: Sections requises manquantes (du ruleset global)
            required_coverage: Ratio de couverture des sections requises (global)
            unknown_titles_count: Nombre de titres non mappés
            placeholders_count: Nombre de placeholders détectés
            profile_id: ID du profil à utiliser (défaut selon config)
            
        Returns:
            Dict avec status GO/NO-GO, profil, signaux, critères, métriques et raisons
        """
        # Charger la configuration du profil
        gate_config = self.ruleset.raw_data.get('production_gate', {})
        if not profile_id:
            profile_id = gate_config.get('default_profile', 'placement_suivi')
        
        profiles = gate_config.get('profiles', {})
        profile = profiles.get(profile_id, profiles.get('placement_suivi', {}))
        
        # Récupérer les seuils du profil
        thresholds = profile.get('thresholds', {})
        max_missing_required = thresholds.get('max_missing_required', 0)
        min_coverage = thresholds.get('min_required_coverage_ratio', 0.9)
        max_unknown = thresholds.get('max_unknown_titles', 5)
        max_placeholders = thresholds.get('max_placeholders', 3)
        
        # Récupérer les préfixes à ignorer pour ce profil
        ignore_prefixes = profile.get('ignore_required_prefixes', [])
        
        # Obtenir tous les chemins required du ruleset
        all_required_paths = self.ruleset.get_required_paths()
        
        # Filtrer les required_paths selon les ignore_prefixes
        required_paths_effective = []
        for path in all_required_paths:
            should_ignore = False
            for prefix in ignore_prefixes:
                if path.startswith(prefix):
                    should_ignore = True
                    break
            if not should_ignore:
                required_paths_effective.append(path)
        
        # Filtrer missing_required selon les ignore_prefixes
        missing_required_effective = []
        for path in missing_required:
            should_ignore = False
            for prefix in ignore_prefixes:
                if path.startswith(prefix):
                    should_ignore = True
                    break
            if not should_ignore:
                missing_required_effective.append(path)
        
        # Recalculer le required_coverage_ratio_effective
        if required_paths_effective:
            required_filled = len(required_paths_effective) - len(missing_required_effective)
            required_coverage_effective = required_filled / len(required_paths_effective)
        else:
            required_coverage_effective = 1.0
        
        reasons = []
        
        # Critère 1: Sections requises (effective)
        if len(missing_required_effective) > max_missing_required:
            reasons.append(f"Missing {len(missing_required_effective)} required section(s) for profile '{profile_id}' (max: {max_missing_required}): {', '.join(missing_required_effective[:3])}")
        
        # Critère 2: Coverage requis (effective)
        if required_coverage_effective < min_coverage:
            reasons.append(f"Required coverage too low: {required_coverage_effective:.1%} < {min_coverage:.0%} (profile: {profile_id})")
        
        # Critère 3: Titres inconnus
        if unknown_titles_count > max_unknown:
            reasons.append(f"Too many unknown titles: {unknown_titles_count} > {max_unknown} (profile: {profile_id})")
        
        # Critère 4: Placeholders
        if placeholders_count > max_placeholders:
            reasons.append(f"Many placeholders found: {placeholders_count} > {max_placeholders} (profile: {profile_id})")
        
        status = 'GO' if not reasons else 'NO-GO'
        
        return {
            'status': status,
            'profile': profile_id,
            'reasons': reasons,
            'criteria': {
                'required_sections_ok': len(missing_required_effective) <= max_missing_required,
                'required_coverage_ok': required_coverage_effective >= min_coverage,
                'unknown_titles_ok': unknown_titles_count <= max_unknown,
                'placeholders_ok': placeholders_count <= max_placeholders
            },
            'metrics': {
                'required_coverage_ratio': round(required_coverage, 2),
                'required_coverage_ratio_effective': round(required_coverage_effective, 2),
                'unknown_titles_count': unknown_titles_count,
                'placeholders_count': placeholders_count,
                'missing_required_sections_count': len(missing_required),
                'missing_required_sections_count_effective': len(missing_required_effective)
            },
            'missing_required_effective': missing_required_effective
        }
    
    def _is_section_filled(self, normalized: Dict[str, Any], section_id: str) -> bool:
        """Vérifie si une section est effectivement remplie dans le dict normalisé"""
        keys = section_id.split('.')
        current = normalized
        
        for key in keys:
            if key not in current:
                return False
            current = current[key]
        
        # Cas spécial pour identity : OK si AVS ou full_name est rempli
        if section_id == 'identity' and isinstance(current, dict):
            return bool(current.get('avs') or current.get('full_name') or current.get('name'))
        
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


def normalize_segments(segments: List[Segment], ruleset: RulesetLoader, 
                      gate_profile_override: Optional[str] = None) -> Dict[str, Any]:
    """
    Helper function pour normaliser les segments
    
    Args:
        segments: Segments à normaliser
        ruleset: Ruleset chargé
        gate_profile_override: Si fourni, force ce profil pour le production gate
    """
    normalizer = Normalizer(ruleset)
    return normalizer.normalize(segments, gate_profile_override=gate_profile_override)
