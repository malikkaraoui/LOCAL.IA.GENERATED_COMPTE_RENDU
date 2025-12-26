"""
Tests pour les profils de Production Gate (GO/NO-GO)
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.rhpro.normalizer import Normalizer
from src.rhpro.ruleset_loader import load_ruleset
from src.rhpro.segmenter import Segment


# Chemins de base
PROJECT_ROOT = Path(__file__).parent.parent
RULESET_PATH = PROJECT_ROOT / 'config' / 'rulesets' / 'rhpro_v1.yaml'


class TestGateProfileSelection:
    """Tests pour la sélection automatique du profil"""
    
    @pytest.fixture
    def normalizer(self):
        """Fixture pour créer un normalizer avec le ruleset"""
        ruleset = load_ruleset(str(RULESET_PATH))
        return Normalizer(ruleset)
    
    def test_choose_profile_stage_keyword(self, normalizer):
        """Doit sélectionner 'stage' si mot-clé 'stage' dans les titres"""
        # Créer des segments avec un titre contenant "stage"
        segments = [
            Segment(raw_title="Bilan de stage", normalized_title="bilan de stage", level=1)
        ]
        found_sections = [{'title': 'Bilan de stage', 'section_id': 'test'}]
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        assert profile_id == 'stage'
        assert signals['has_stage'] is True
    
    def test_choose_profile_stage_orientation_formation_stage(self, normalizer):
        """Doit sélectionner 'stage' si titre contient 'orientation formation stage'"""
        segments = [
            Segment(raw_title="Orientation formation stage", normalized_title="orientation formation stage", level=1)
        ]
        found_sections = [{'title': 'Orientation formation stage', 'section_id': 'test'}]
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        assert profile_id == 'stage'
        assert signals['has_stage'] is True
    
    def test_choose_profile_placement_suivi_keyword_suivi(self, normalizer):
        """Doit sélectionner 'placement_suivi' par défaut si pas de signaux spécifiques"""
        segments = [
            Segment(raw_title="Suivi du candidat", normalized_title="suivi du candidat", level=1)
        ]
        found_sections = [{'title': 'Suivi du candidat', 'section_id': 'test'}]
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        # Sans bilan_complet_sections ni LAI, c'est placement_suivi
        assert profile_id == 'placement_suivi'
    
    def test_choose_profile_placement_suivi_keyword_placement(self, normalizer):
        """Doit sélectionner 'placement_suivi' par défaut"""
        segments = [
            Segment(raw_title="Plan de placement", normalized_title="plan de placement", level=1)
        ]
        found_sections = [{'title': 'Plan de placement', 'section_id': 'test'}]
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        assert profile_id == 'placement_suivi'
    
    def test_choose_profile_placement_suivi_lai15(self, normalizer):
        """Doit sélectionner 'placement_suivi' si LAI 15 détecté"""
        segments = [
            Segment(raw_title="Mesures LAI 15", normalized_title="mesures lai 15", level=1)
        ]
        found_sections = [{'title': 'Mesures LAI 15', 'section_id': 'test'}]
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        assert profile_id == 'placement_suivi'
        assert signals['has_lai15'] is True
    
    def test_choose_profile_bilan_complet_with_tests(self, normalizer):
        """Doit sélectionner 'bilan_complet' si >= 2 sections bilan complet"""
        segments = []
        found_sections = [
            {'title': 'Tests', 'section_id': 'tests'},
            {'title': 'Profil emploi', 'section_id': 'profil_emploi'}
        ]
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        assert profile_id == 'bilan_complet'
        assert signals['bilan_complet_sections_count'] >= 2
    
    def test_choose_profile_case_insensitive(self, normalizer):
        """La détection doit être insensible à la casse"""
        segments = [
            Segment(raw_title="BILAN DE STAGE", normalized_title="BILAN DE STAGE", level=1)
        ]
        found_sections = [{'title': 'BILAN DE STAGE', 'section_id': 'test'}]
        
        profile_id, reasons = normalizer._choose_gate_profile(segments, found_sections)
        
        assert profile_id == 'stage'
    
    def test_choose_profile_stage_priority_over_suivi(self, normalizer):
        """'stage' doit avoir la priorité sur 'suivi_leger'"""
        # Si on a à la fois "stage" et "suivi", "stage" est détecté en premier
        segments = [
            Segment(raw_title="Stage de suivi", normalized_title="stage de suivi", level=1)
        ]
        found_sections = [{'title': 'Stage de suivi', 'section_id': 'test'}]
        
        profile_id, reasons = normalizer._choose_gate_profile(segments, found_sections)
        
        # Stage doit être détecté car il est testé en premier
        assert profile_id == 'stage'


class TestGateProfileEvaluation:
    """Tests pour l'évaluation GO/NO-GO selon le profil"""
    
    @pytest.fixture
    def normalizer(self):
        """Fixture pour créer un normalizer avec le ruleset"""
        ruleset = load_ruleset(str(RULESET_PATH))
        return Normalizer(ruleset)
    
    def test_evaluate_bilan_complet_strict(self, normalizer):
        """Profil bilan_complet: critères stricts"""
        # Cas NO-GO : coverage trop faible
        result = normalizer._evaluate_production_gate(
            missing_required=['orientation_formation'],
            required_coverage=0.85,
            unknown_titles_count=3,
            placeholders_count=2,
            profile_id='bilan_complet'
        )
        
        assert result['status'] == 'NO-GO'
        assert result['profile'] == 'bilan_complet'
        assert not result['criteria']['required_coverage_ok']
        assert result['metrics']['required_coverage_ratio'] == 0.85
    
    def test_evaluate_bilan_complet_go(self, normalizer):
        """Profil bilan_complet: cas GO"""
        result = normalizer._evaluate_production_gate(
            missing_required=[],
            required_coverage=0.95,
            unknown_titles_count=4,
            placeholders_count=0,  # max_placeholders=1 pour bilan_complet
            profile_id='bilan_complet'
        )
        
        assert result['status'] == 'GO'
        assert result['profile'] == 'bilan_complet'
        assert all(result['criteria'].values())
    
    def test_evaluate_placement_suivi_tolerant(self, normalizer):
        """Profil placement_suivi: critères plus tolérants"""
        # Cas GO : coverage à 65% est OK pour placement_suivi
        result = normalizer._evaluate_production_gate(
            missing_required=[],
            required_coverage=0.65,
            unknown_titles_count=8,
            placeholders_count=4,
            profile_id='placement_suivi'
        )
        
        assert result['status'] == 'GO'
        assert result['profile'] == 'placement_suivi'
        assert result['criteria']['required_coverage_ok']
        assert result['criteria']['unknown_titles_ok']
        assert result['criteria']['placeholders_ok']
    
    def test_evaluate_placement_suivi_no_go(self, normalizer):
        """Profil placement_suivi: cas NO-GO si trop de titres inconnus"""
        result = normalizer._evaluate_production_gate(
            missing_required=[],
            required_coverage=0.70,
            unknown_titles_count=12,  # > 10 (max pour placement_suivi)
            placeholders_count=3,
            profile_id='placement_suivi'
        )
        
        assert result['status'] == 'NO-GO'
        assert result['profile'] == 'placement_suivi'
        assert not result['criteria']['unknown_titles_ok']
    
    def test_evaluate_stage_specific(self, normalizer):
        """Profil stage: critères spécifiques"""
        # Cas GO : coverage à 72% est OK pour stage
        result = normalizer._evaluate_production_gate(
            missing_required=[],
            required_coverage=0.72,
            unknown_titles_count=7,
            placeholders_count=4,
            profile_id='stage'
        )
        
        assert result['status'] == 'GO'
        assert result['profile'] == 'stage'
        assert result['criteria']['required_coverage_ok']
    
    def test_evaluate_stage_no_go_coverage(self, normalizer):
        """Profil stage: NO-GO si coverage effective < 70%
        
        Règles du profil stage:
        - ignore_required_prefixes: [tests, vocation, profil_emploi]
        - min_required_coverage_ratio: 0.70
        
        Sections required dans le ruleset (4 total):
        - identity
        - profession_formation
        - orientation_formation
        - orientation_formation.orientation
        
        Aucune n'est ignorée par le profil stage.
        Pour avoir coverage < 70%, il faut au moins 2 missing sur 4:
        - 2 missing => (4-2)/4 = 50% < 70% => NO-GO
        """
        result = normalizer._evaluate_production_gate(
            missing_required=['identity', 'profession_formation'],  # 2/4 missing => 50% coverage
            required_coverage=0.65,  # ignoré car recalculé
            unknown_titles_count=5,
            placeholders_count=3,
            profile_id='stage'
        )
        
        assert result['status'] == 'NO-GO'
        assert result['profile'] == 'stage'
        assert result['metrics']['required_coverage_ratio_effective'] < 0.70
        assert not result['criteria']['required_coverage_ok']
    
    def test_evaluate_unknown_profile_defaults_to_placement_suivi(self, normalizer):
        """Un profil inconnu doit utiliser placement_suivi par défaut"""
        result = normalizer._evaluate_production_gate(
            missing_required=[],
            required_coverage=0.95,
            unknown_titles_count=4,
            placeholders_count=2,
            profile_id='unknown_profile'
        )
        
        # Doit utiliser les seuils de placement_suivi (puisque profile inexistant)
        assert result['status'] == 'GO'
        assert result['profile'] == 'unknown_profile'
    
    def test_evaluate_metrics_included(self, normalizer):
        """Les métriques doivent être incluses dans le résultat"""
        # Pour bilan_complet, les sections requises incluent: identity, profession_formation, orientation_formation, conclusion
        # On passe 'orientation_formation' comme manquant, qui est dans les sections requises du profil
        result = normalizer._evaluate_production_gate(
            missing_required=['orientation_formation'],
            required_coverage=0.82,
            unknown_titles_count=6,
            placeholders_count=4,
            profile_id='bilan_complet'
        )
        
        assert 'metrics' in result
        assert result['metrics']['required_coverage_ratio'] == 0.82
        assert 'required_coverage_ratio_effective' in result['metrics']
        assert result['metrics']['unknown_titles_count'] == 6
        assert result['metrics']['placeholders_count'] == 4
        assert 'missing_required_sections_count_effective' in result['metrics']


class TestGateProfileIntegration:
    """Tests d'intégration pour le système de profils"""
    
    def test_profile_override_works(self):
        """L'override manuel du profil doit fonctionner"""
        ruleset = load_ruleset(str(RULESET_PATH))
        normalizer = Normalizer(ruleset)
        
        # Créer des segments qui devraient normalement déclencher "stage"
        segments = [
            Segment(raw_title="Bilan de stage", normalized_title="bilan de stage", 
                   level=1, mapped_section_id='identity')
        ]
        
        # Forcer le profil bilan_complet
        result = normalizer.normalize(segments, gate_profile_override='bilan_complet')
        
        gate = result['report']['production_gate']
        assert gate['profile'] == 'bilan_complet'
        assert gate['signals'].get('forced') is True
    
    def test_auto_detection_without_override(self):
        """Sans override, l'auto-détection doit fonctionner"""
        ruleset = load_ruleset(str(RULESET_PATH))
        normalizer = Normalizer(ruleset)
        
        segments = [
            Segment(raw_title="Plan de placement", normalized_title="plan de placement", 
                   level=1, mapped_section_id='identity')
        ]
        
        result = normalizer.normalize(segments)
        
        gate = result['report']['production_gate']
        assert gate['profile'] == 'placement_suivi'
        assert 'signals' in gate


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
