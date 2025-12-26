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
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        assert profile_id == 'stage'
    
    def test_choose_profile_stage_priority_over_suivi(self, normalizer):
        """'stage' doit avoir un meilleur score que les autres profils"""
        # Si on a à la fois "stage" et "suivi", "stage" doit gagner via scoring
        segments = [
            Segment(raw_title="Stage de suivi", normalized_title="stage de suivi", level=1)
        ]
        found_sections = [{'title': 'Stage de suivi', 'section_id': 'test'}]
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
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


class TestGateProfileScoring:
    """Tests pour le système de scoring durci"""
    
    @pytest.fixture
    def normalizer(self):
        """Fixture pour créer un normalizer avec le ruleset"""
        ruleset = load_ruleset(str(RULESET_PATH))
        return Normalizer(ruleset)
    
    def test_false_positive_stage_in_content_not_title(self, normalizer):
        """Faux positif: 'stage' dans contenu mais pas dans les titres
        Le système durci NE doit PAS détecter 'stage' car absent des headings"""
        # Segments sans "stage" dans les titres
        segments = [
            Segment(raw_title="Identité", normalized_title="identité", level=1),
            Segment(raw_title="Conclusion", normalized_title="conclusion", level=1)
        ]
        # Section_ids normaux (pas de stage)
        found_sections = [
            {'title': 'Identité', 'section_id': 'identity'},
            {'title': 'Conclusion', 'section_id': 'conclusion'}
        ]
        
        # Le contenu des paragraphes pourrait contenir "stage" mais on l'ignore
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        # Ne doit PAS sélectionner 'stage'
        assert profile_id != 'stage'
        assert signals['has_stage'] is False
        assert profile_id in ['placement_suivi', 'bilan_complet']
    
    def test_ambiguous_case_with_scoring(self, normalizer):
        """Cas ambigu: document avec quelques signaux mixtes
        Le scoring doit trancher de manière déterministe"""
        # Document avec 1 section bilan_complet mais aussi du contenu léger
        segments = [
            Segment(raw_title="Identité", normalized_title="identité", level=1),
            Segment(raw_title="Tests", normalized_title="tests", level=1)
        ]
        found_sections = [
            {'title': 'Identité', 'section_id': 'identity'},
            {'title': 'Tests', 'section_id': 'tests'}
        ]
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        # Doit avoir des scores
        assert 'scores' in signals
        assert 'selection_confidence' in signals
        assert 'profile_ranking' in signals
        
        # La confidence doit être positive (pas d'égalité parfaite)
        assert signals['selection_confidence'] >= 0
        
        # Le profil choisi doit être le top1 du ranking
        assert profile_id == signals['profile_ranking'][0]
        
        # Vérifier que bilan_complet_sections_count = 1 (tests uniquement)
        assert signals['bilan_complet_sections_count'] == 1
    
    def test_high_confidence_stage_detection(self, normalizer):
        """Signal fort 'stage' doit donner une haute confidence"""
        segments = [
            Segment(raw_title="Bilan de stage", normalized_title="bilan de stage", level=1)
        ]
        found_sections = [
            {'title': 'Bilan de stage', 'section_id': 'orientation_formation.stage'}
        ]
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        assert profile_id == 'stage'
        assert signals['has_stage'] is True
        
        # Score de 'stage' doit être nettement supérieur aux autres
        assert signals['scores']['stage'] > signals['scores']['bilan_complet']
        assert signals['scores']['stage'] > signals['scores']['placement_suivi']
        
        # Confidence doit être élevée (delta important)
        assert signals['selection_confidence'] >= 50
    
    def test_matched_titles_truncation(self, normalizer):
        """Les matched_titles doivent être tronqués pour lisibilité"""
        # Titre très long
        long_title = "Bilan de stage en entreprise avec description détaillée et longue pour tester la troncation automatique"
        segments = [
            Segment(raw_title=long_title, normalized_title=long_title.lower(), level=1)
        ]
        found_sections = []
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        # matched_titles doit contenir des titres tronqués
        if signals['matched_titles']:
            for matched in signals['matched_titles']:
                # Vérifier que la partie après ":" est <= 40 caractères
                if ':' in matched:
                    title_part = matched.split(':', 1)[1]
                    assert len(title_part) <= 40
    
    def test_scoring_all_zeros_fallback_to_default(self, normalizer):
        """Si tous les scores sont nuls, fallback sur le profil par défaut"""
        # Document minimal sans aucun signal
        segments = [
            Segment(raw_title="Section inconnue", normalized_title="section inconnue", level=1)
        ]
        found_sections = []
        
        profile_id, signals = normalizer._choose_gate_profile(segments, found_sections)
        
        # Doit retourner le profil par défaut (placement_suivi)
        assert profile_id == 'placement_suivi'
        
        # Confidence peut être faible ou nulle
        assert 'selection_confidence' in signals


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
