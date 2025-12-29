"""
Tests pour le mode DRAFT (PATCH A-C)

Objectif: Vérifier que le profil DRAFT ne bloque jamais la génération,
même avec sections manquantes, unknown_titles élevés, etc.
"""
import pytest
from pathlib import Path

from src.rhpro.segmenter import Segment
from src.rhpro.docx_structure import Paragraph
from src.rhpro.ruleset_loader import load_ruleset
from src.rhpro.normalizer import Normalizer


class TestDraftMode:
    """Tests pour le profil DRAFT"""
    
    def test_draft_profile_exists_in_ruleset(self):
        """Test que le profil 'draft' existe dans le ruleset"""
        ruleset_path = Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml"
        ruleset = load_ruleset(str(ruleset_path))
        
        gate_config = ruleset.raw_data.get('production_gate', {})
        profiles = gate_config.get('profiles', {})
        
        assert 'draft' in profiles, "Profil 'draft' manquant dans le ruleset"
        
        draft_profile = profiles['draft']
        assert draft_profile['description'] is not None
        assert draft_profile['thresholds']['max_missing_required'] >= 999
        assert draft_profile['thresholds']['min_required_coverage_ratio'] == 0.0
    
    def test_draft_mode_never_blocks(self):
        """Test que le mode DRAFT retourne toujours status='DRAFT'"""
        ruleset_path = Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml"
        ruleset = load_ruleset(str(ruleset_path))
        
        # Créer un normalizer
        normalizer = Normalizer(ruleset)
        
        # Scénario PIRE CAS: Tout manquant
        missing_required = ["identity", "profession_formation", "orientation_formation", "conclusion"]
        required_coverage = 0.0
        unknown_titles_count = 100
        placeholders_count = 50
        
        # Appeler _evaluate_production_gate avec profile_id='draft'
        result = normalizer._evaluate_production_gate(
            missing_required=missing_required,
            required_coverage=required_coverage,
            unknown_titles_count=unknown_titles_count,
            placeholders_count=placeholders_count,
            profile_id='draft'
        )
        
        # Vérifications
        assert result['status'] == 'DRAFT', "Status devrait être 'DRAFT'"
        assert result['profile'] == 'draft'
        assert result['criteria']['required_sections_ok'] == True
        assert result['criteria']['required_coverage_ok'] == True
        assert result['criteria']['unknown_titles_ok'] == True
        assert result['criteria']['placeholders_ok'] == True
        assert 'Draft mode' in result['reasons'][0]
    
    def test_draft_vs_strict_comparison(self):
        """Test comparaison DRAFT vs STRICT sur même document pauvre"""
        ruleset_path = Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml"
        ruleset = load_ruleset(str(ruleset_path))
        normalizer = Normalizer(ruleset)
        
        # Document très pauvre
        missing_required = ["identity", "profession_formation", "orientation_formation"]
        required_coverage = 0.3
        unknown_titles_count = 20
        placeholders_count = 10
        
        # STRICT (bilan_complet)
        result_strict = normalizer._evaluate_production_gate(
            missing_required=missing_required,
            required_coverage=required_coverage,
            unknown_titles_count=unknown_titles_count,
            placeholders_count=placeholders_count,
            profile_id='bilan_complet'
        )
        
        # DRAFT
        result_draft = normalizer._evaluate_production_gate(
            missing_required=missing_required,
            required_coverage=required_coverage,
            unknown_titles_count=unknown_titles_count,
            placeholders_count=placeholders_count,
            profile_id='draft'
        )
        
        # STRICT devrait bloquer
        assert result_strict['status'] == 'NO-GO', "Bilan_complet devrait être NO-GO"
        assert len(result_strict['reasons']) > 0
        
        # DRAFT ne devrait jamais bloquer
        assert result_draft['status'] == 'DRAFT', "Draft devrait toujours être DRAFT"
        assert result_draft['criteria']['required_sections_ok'] == True
    
    def test_draft_mode_integration_with_normalizer(self):
        """Test integration complète du mode DRAFT avec normalize()"""
        ruleset_path = Path.cwd() / "config" / "rulesets" / "rhpro_v1.yaml"
        ruleset = load_ruleset(str(ruleset_path))
        normalizer = Normalizer(ruleset)
        
        # Créer un segment minimal (presque vide)
        paragraph = Paragraph(
            text="Ceci est un test",
            style_name="Normal",
            is_bold=False,
            font_size=11.0,
            is_all_caps=False,
            numbering_prefix=""
        )
        
        segment = Segment(
            raw_title="Test",
            normalized_title="test",
            level=0,
            paragraphs=[paragraph],
            mapped_section_id=None,  # Pas mappé
            confidence=0.0
        )
        
        # Normaliser avec profil DRAFT
        result = normalizer.normalize([segment], gate_profile_override='draft')
        
        report = result['report']
        gate = report['production_gate']
        
        # Vérifications
        assert gate['status'] == 'DRAFT', f"Status devrait être DRAFT, got {gate['status']}"
        assert gate['profile'] == 'draft'
        assert 'Draft mode' in gate['reasons'][0]


class TestForceDraftLogic:
    """Tests pour la logique force_draft dans l'UI"""
    
    def test_force_draft_concept(self):
        """Test conceptuel de la logique force_draft"""
        # Simuler le comportement attendu
        gate_status = "NO-GO"
        force_draft = True
        
        # Logique attendue dans l'UI
        if gate_status == "NO-GO" and force_draft:
            final_status = "DRAFT (forced)"
            allow_generation = True
        else:
            final_status = gate_status
            allow_generation = (gate_status in ("GO", "DRAFT"))
        
        assert final_status == "DRAFT (forced)"
        assert allow_generation == True
    
    def test_force_draft_false_no_change(self):
        """Test que force_draft=False ne change rien"""
        gate_status = "NO-GO"
        force_draft = False
        
        if gate_status == "NO-GO" and force_draft:
            final_status = "DRAFT (forced)"
            allow_generation = True
        else:
            final_status = gate_status
            allow_generation = (gate_status in ("GO", "DRAFT"))
        
        assert final_status == "NO-GO"
        assert allow_generation == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
