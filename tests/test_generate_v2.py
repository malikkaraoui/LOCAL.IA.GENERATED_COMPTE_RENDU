"""
Tests d'intégration pour generate.py avec Schema V2

OBJECTIF: Valider le comportement V2
- Extraction enum sans LLM
- Validation liste max 4 items
- require_sources
- build_prompt adapté V2
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Force Schema V2 pour ces tests
import core.generate as generate_module
generate_module.USE_SCHEMA_V2 = True

from core.generate import (
    extract_bullet_points,
    validate_list_v2,
    extract_enum_field_v2,
    build_prompt,
    generate_fields,
)
from core.field_specs_v2 import get_field_spec_v2, CECRL_LEVELS, TOOL_LEVELS


class TestExtractBulletPoints:
    """Tests extraction bullet points"""
    
    def test_extract_dash_bullets(self):
        """Extraction avec tirets -"""
        text = "- Item 1\n- Item 2\n- Item 3"
        assert extract_bullet_points(text) == ["Item 1", "Item 2", "Item 3"]
    
    def test_extract_bullet_symbol(self):
        """Extraction avec symbole •"""
        text = "• First\n• Second"
        assert extract_bullet_points(text) == ["First", "Second"]
    
    def test_extract_star_bullets(self):
        """Extraction avec étoiles *"""
        text = "* Alpha\n* Beta\n* Gamma"
        assert extract_bullet_points(text) == ["Alpha", "Beta", "Gamma"]
    
    def test_mixed_bullets(self):
        """Extraction avec mix"""
        text = "- Item A\n• Item B\n* Item C"
        assert len(extract_bullet_points(text)) == 3


class TestValidateListV2:
    """Tests validation liste V2"""
    
    def test_truncate_to_4_items(self):
        """Tronquer liste à 4 items"""
        text = "- A\n- B\n- C\n- D\n- E\n- F"
        result = validate_list_v2(text, max_items=4)
        items = extract_bullet_points(result)
        
        assert len(items) == 4
        assert items == ["A", "B", "C", "D"]
    
    def test_keep_3_items(self):
        """Garder 3 items (< 4)"""
        text = "- Alpha\n- Beta\n- Gamma"
        result = validate_list_v2(text, max_items=4)
        items = extract_bullet_points(result)
        
        assert len(items) == 3
    
    def test_truncate_chars(self):
        """Tronquer caractères"""
        text = "- " + "A" * 1000 + "\n- " + "B" * 1000
        result = validate_list_v2(text, max_items=10, max_chars=500)
        
        assert len(result) <= 500
    
    def test_no_bullets_passthrough(self):
        """Pas de bullets: retour texte tronqué"""
        text = "Just a plain text without bullets."
        result = validate_list_v2(text, max_items=4, max_chars=2000)
        
        assert result == text


class TestExtractEnumFieldV2:
    """Tests extraction enum V2"""
    
    def test_extract_francais_b2(self):
        """Extraction niveau français B2"""
        context = [{"text": "Le candidat a un niveau B2 en français."}]
        result = extract_enum_field_v2(context, "FRANCAIS_POSITIONNEMENT_DE_NIVEAU", CECRL_LEVELS)
        
        assert result == "B2"
    
    def test_extract_anglais_c1(self):
        """Extraction niveau anglais C1"""
        context = [{"text": "Anglais: C1 confirmé"}]
        result = extract_enum_field_v2(context, "ANGLAIS_POSITIONNEMENT_DE_NIVEAU", CECRL_LEVELS)
        
        assert result == "C1"
    
    def test_no_context_returns_non_evalue(self):
        """Sans contexte → Non évalué"""
        result = extract_enum_field_v2([], "FRANCAIS_POSITIONNEMENT_DE_NIVEAU", CECRL_LEVELS)
        
        assert result == "Non évalué"
    
    def test_no_level_found_returns_non_evalue(self):
        """Pas de niveau trouvé → Non évalué"""
        context = [{"text": "Le candidat parle bien français."}]
        result = extract_enum_field_v2(context, "FRANCAIS_POSITIONNEMENT_DE_NIVEAU", CECRL_LEVELS)
        
        assert result == "Non évalué"
    
    def test_bureautique_bon(self):
        """Extraction bureautique Bon"""
        context = [{"text": "Bonne maîtrise d'Excel et Word"}]
        result = extract_enum_field_v2(context, "BUREAUTIQUE_POSITIONNEMENT_DE_NIVEAU", TOOL_LEVELS)
        
        assert result == "Bon"
    
    def test_test_ok(self):
        """Extraction test OK"""
        from core.field_specs_v2 import TEST_LEVELS
        context = [{"text": "Test d'attention: OK"}]
        result = extract_enum_field_v2(context, "TEST_ATTENTION_ADMINISTRATIF", TEST_LEVELS)
        
        assert result == "OK"


class TestBuildPromptV2:
    """Tests build_prompt avec V2"""
    
    def test_narrative_prompt(self):
        """Prompt pour champ narrative"""
        spec = get_field_spec_v2("PROFESSION")
        context = [{"text": "Candidat travaille dans l'informatique", "source_path": "cv.pdf", "page": 1}]
        
        prompt = build_prompt(spec, "Synthèse professionnelle", context)
        
        assert "Champ : PROFESSION" in prompt
        assert "Synthèse professionnelle" in prompt
        assert "cv.pdf" in prompt
        assert "__VIDE__" in prompt  # Instruction si pas d'info
    
    def test_list_prompt_max_4_items(self):
        """Prompt pour champ liste (max 4 items)"""
        spec = get_field_spec_v2("SECTEURS_PRIVILEGIES")
        context = [{"text": "Le candidat est motivé, autonome, rigoureux", "source_path": "rapport.pdf", "page": 2}]
        
        prompt = build_prompt(spec, "Extraire les ressources", context)
        
        assert "maximum 4 items" in prompt.lower()
        assert "2 à 4 items" in prompt
    
    def test_enum_prompt(self):
        """Prompt pour champ enum"""
        spec = get_field_spec_v2("FRANCAIS_POSITIONNEMENT_DE_NIVEAU")
        context = [{"text": "Niveau B2 en français", "source_path": "eval.pdf", "page": 1}]
        
        prompt = build_prompt(spec, "Niveau de français", context)
        
        assert "A1, A2, B1, B2, C1, C2, Non évalué" in prompt
        assert "Choisis uniquement parmi" in prompt


class TestGenerateFieldsV2Integration:
    """Tests d'intégration generate_fields avec V2"""
    
    @patch('core.generate.ollama_generate')
    @patch('core.generate.build_index')
    def test_enum_field_no_llm_call(self, mock_build_index, mock_ollama):
        """Enum: pas d'appel LLM, extraction directe"""
        # Setup mocks
        mock_index = Mock()
        mock_index.topk.return_value = [(0, 0.9)]
        mock_build_index.return_value = (
            [Mock(chunk_id="c1", source_path="test.pdf", page=1, text="Niveau B2 en français")],
            mock_index
        )
        
        payload = {"sources": [{"path": "test.pdf", "text": "Niveau B2"}]}
        fields = [{"key": "FRANCAIS_POSITIONNEMENT_DE_NIVEAU", "query": "Niveau français", "instructions": "Extraire"}]
        
        result = generate_fields(
            payload,
            model="llama3",
            host="http://localhost:11434",
            topk=3,
            temperature=0.0,
            top_p=0.9,
            fields=fields,
        )
        
        # Vérifier: aucun appel LLM
        mock_ollama.assert_not_called()
        
        # Vérifier: valeur extraite
        assert "FRANCAIS_POSITIONNEMENT_DE_NIVEAU" in result
        field_result = result["FRANCAIS_POSITIONNEMENT_DE_NIVEAU"]
        assert field_result["value"] == "B2"
        assert "NO_ENUM_FOUND" not in field_result["missing_info"]
    
    @patch('core.generate.ollama_generate')
    @patch('core.generate.build_index')
    def test_list_field_max_4_items(self, mock_build_index, mock_ollama):
        """Liste: validation max 4 items"""
        # Setup mocks
        mock_index = Mock()
        mock_index.topk.return_value = [(0, 0.9)]
        mock_build_index.return_value = (
            [Mock(chunk_id="c1", source_path="test.pdf", page=1, text="Ressources")],
            mock_index
        )
        
        # LLM retourne 6 items (doit être tronqué à 4)
        llm_response = "- Motivé\n- Autonome\n- Rigoureux\n- Dynamique\n- Créatif\n- Persévérant"
        mock_result = Mock()
        mock_result.success = True
        mock_result.value = llm_response
        mock_ollama.return_value = mock_result
        
        payload = {"sources": [{"path": "test.pdf", "text": "Ressources"}]}
        fields = [{"key": "SECTEURS_PRIVILEGIES", "query": "Secteurs", "instructions": "Extraire"}]
        
        result = generate_fields(
            payload,
            model="llama3",
            host="http://localhost:11434",
            topk=3,
            temperature=0.0,
            top_p=0.9,
            fields=fields,
        )
        
        # Vérifier: 4 items max
        value = result["SECTEURS_PRIVILEGIES"]["value"]
        items = extract_bullet_points(value)
        assert len(items) == 4
        assert items == ["Motivé", "Autonome", "Rigoureux", "Dynamique"]
    
    @patch('core.generate.ollama_generate')
    @patch('core.generate.build_index')
    def test_require_sources_no_context(self, mock_build_index, mock_ollama):
        """require_sources: pas de contexte → pas de LLM"""
        # Setup mocks: aucun chunk retourné
        mock_index = Mock()
        mock_index.topk.return_value = []  # Pas de résultats
        mock_build_index.return_value = ([], mock_index)
        
        payload = {"sources": []}
        fields = [{"key": "CV", "query": "CV", "instructions": "Extraire"}]
        
        result = generate_fields(
            payload,
            model="llama3",
            host="http://localhost:11434",
            topk=3,
            temperature=0.0,
            top_p=0.9,
            fields=fields,
        )
        
        # Vérifier: aucun appel LLM (skip_llm_if_no_sources=True pour CV)
        mock_ollama.assert_not_called()
        
        # Vérifier: valeur vide
        assert result["CV"]["value"] == ""
        assert "NO_CONTEXT" in result["CV"]["missing_info"]


class TestSchemaV2FlagToggle:
    """Tests toggle USE_SCHEMA_V2"""
    
    def test_v2_flag_is_true(self):
        """Flag V2 activé pour ces tests"""
        assert generate_module.USE_SCHEMA_V2 is True
    
    def test_get_field_spec_v2_available(self):
        """get_field_spec_v2 disponible"""
        spec = get_field_spec_v2("PROFESSION")
        assert spec.key == "PROFESSION"
        assert spec.field_type == "narrative"
        assert spec.extraction_policy == "llm_with_guardrails"
    
    def test_enum_field_has_extract_only_policy(self):
        """Champ enum a extraction_policy=extract_only"""
        spec = get_field_spec_v2("FRANCAIS_POSITIONNEMENT_DE_NIVEAU")
        assert spec.field_type == "enum"
        assert spec.extraction_policy == "extract_only"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
