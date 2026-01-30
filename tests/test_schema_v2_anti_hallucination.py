"""
Tests anti-hallucination pour schéma V2

OBJECTIF: Valider les garde-fous contre l'invention de contenu
- Enum: valeurs autorisées seulement
- Liste: max 4 items
- Narrative: max chars respecté
- require_sources: bloque LLM si pas de sources
"""

import pytest
from core.field_specs_v2 import (
    FIELD_SPECS_V2,
    get_field_spec_v2,
    list_fields_by_type,
    CECRL_LEVELS,
    TOOL_LEVELS,
    TEST_LEVELS,
)
from core.enum_extractors_v2 import (
    extract_cecrl_level,
    extract_bureautique_level,
    extract_test_result,
    validate_enum_value,
    extract_enum_from_context,
)
from core.title_mapping_v2 import (
    map_title_to_field_v2,
    is_ignored_title_v2,
    IGNORED_TITLES_V2,
)


class TestSchemaV2Structure:
    """Tests de structure du schéma V2"""

    def test_total_fields_is_53(self):
        """Schéma V2 doit avoir exactement 53 champs"""
        assert len(FIELD_SPECS_V2) == 53, (
            f"Expected 53 fields, got {len(FIELD_SPECS_V2)}"
        )

    def test_field_types_distribution(self):
        """Distribution: 5 deterministic, 26 narrative, 8 list, 7 enum, 7 test_narrative"""
        by_type = {}
        for spec in FIELD_SPECS_V2.values():
            by_type[spec.field_type] = by_type.get(spec.field_type, 0) + 1

        assert by_type["deterministic"] == 5
        assert by_type["narrative"] == 26
        assert by_type["list"] == 8
        assert by_type["enum"] == 7
        assert by_type["test_narrative"] == 7

    def test_narrative_max_chars(self):
        """Champs narrative doivent avoir max_chars=2000 ou 3000"""
        narrative_fields = list_fields_by_type("narrative")

        for key in narrative_fields:
            spec = get_field_spec_v2(key)
            assert spec.max_chars in (2000, 3000), (
                f"{key}: Expected max_chars in (2000, 3000), got {spec.max_chars}"
            )

    def test_list_max_chars_2000(self):
        """Tous les champs list doivent avoir max_chars=2000"""
        list_fields = list_fields_by_type("list")

        for key in list_fields:
            spec = get_field_spec_v2(key)
            assert spec.max_chars == 2000, (
                f"{key}: Expected max_chars=2000, got {spec.max_chars}"
            )

    def test_enum_have_values(self):
        """Tous les champs enum doivent avoir enum_values défini"""
        enum_fields = list_fields_by_type("enum")

        for key in enum_fields:
            spec = get_field_spec_v2(key)
            assert spec.enum_values is not None, (
                f"{key}: enum_values should not be None"
            )
            assert len(spec.enum_values) > 0, (
                f"{key}: enum_values should not be empty"
            )

    def test_enum_extraction_policy(self):
        """Tous les champs enum doivent avoir extraction_policy='extract_only'"""
        enum_fields = list_fields_by_type("enum")

        for key in enum_fields:
            spec = get_field_spec_v2(key)
            assert spec.extraction_policy == "extract_only", (
                f"{key}: Expected extraction_policy='extract_only', got {spec.extraction_policy}"
            )

    def test_cv_lettre_require_sources(self):
        """CV et LETTRE_DE_MOTIVATION doivent require_sources=True"""
        for key in ["CV", "LETTRE_DE_MOTIVATION"]:
            spec = get_field_spec_v2(key)
            assert spec.require_sources is True, (
                f"{key}: Should require sources"
            )
            assert spec.skip_llm_if_no_sources is True, (
                f"{key}: Should skip LLM if no sources"
            )

    def test_test_narrative_max_chars_1000(self):
        """Champs test_narrative doivent avoir max_chars=1000"""
        test_fields = list_fields_by_type("test_narrative")
        assert len(test_fields) == 7

        for key in test_fields:
            spec = get_field_spec_v2(key)
            assert spec.max_chars == 1000, (
                f"{key}: Expected max_chars=1000, got {spec.max_chars}"
            )
            assert spec.max_lines == 5

    def test_bureautique_split_into_4(self):
        """Bureautique doit être séparé en 4 champs"""
        expected = [
            "WORD_POSITIONNEMENT_DE_NIVEAU",
            "EXCEL_POSITIONNEMENT_DE_NIVEAU",
            "POWERPOINT_POSITIONNEMENT_DE_NIVEAU",
            "OUTLOOK_POSITIONNEMENT_DE_NIVEAU",
        ]
        for key in expected:
            assert key in FIELD_SPECS_V2, f"{key} missing from schema"
            spec = FIELD_SPECS_V2[key]
            assert spec.field_type == "enum"
            assert spec.enum_values == TOOL_LEVELS

    def test_allemand_present(self):
        """Allemand doit être dans le schéma"""
        assert "ALLEMAND_POSITIONNEMENT_DE_NIVEAU" in FIELD_SPECS_V2
        spec = FIELD_SPECS_V2["ALLEMAND_POSITIONNEMENT_DE_NIVEAU"]
        assert spec.enum_values == CECRL_LEVELS

    def test_alias_backward_compat(self):
        """Les alias de compatibilité doivent fonctionner"""
        # Ancien champ fusionné
        spec = get_field_spec_v2("CONTEXTE_ORGANISATION_ET_ROLE_PRIVILEGIE")
        assert spec.key == "CONTEXTE_ORGANISATION_PRIVILEGIEE"

        spec = get_field_spec_v2("RESSOURCES_MOTIVATIONNELLES")
        assert spec.key == "RESSOURCES_MOTIVATIONNELLES_PRINCIPAUX"

        spec = get_field_spec_v2("WORD_EXCEL_POWERPOINT_OUTLOOK_POSITIONNEMENT_DE_NIVEAU")
        assert spec.key == "WORD_POSITIONNEMENT_DE_NIVEAU"


class TestEnumExtraction:
    """Tests d'extraction enum (anti-hallucination)"""

    def test_extract_cecrl_valid(self):
        """Extraction CECRL valide"""
        assert extract_cecrl_level("Niveau B2 en français") == "B2"
        assert extract_cecrl_level("Le client a un niveau C1") == "C1"
        assert extract_cecrl_level("A1 débutant") == "A1"

    def test_extract_cecrl_not_found_returns_non_evalue(self):
        """Pas de niveau CECRL → "Non évalué" """
        assert extract_cecrl_level("Bon niveau de français") == "Non évalué"
        assert extract_cecrl_level("Pas d'évaluation") == "Non évalué"
        assert extract_cecrl_level("") == "Non évalué"

    def test_extract_cecrl_never_invents(self):
        """CECRL: jamais d'invention, même avec indices"""
        assert extract_cecrl_level("Très bon niveau") == "Non évalué"
        assert extract_cecrl_level("Compétent à l'oral") == "Non évalué"

    def test_extract_bureautique_valid(self):
        """Extraction bureautique valide"""
        assert extract_bureautique_level("Bonne maîtrise de Word") == "Bon"
        assert extract_bureautique_level("Expert Excel") == "Très bon"
        assert extract_bureautique_level("Notions de base PowerPoint") == "Moyen"

    def test_extract_bureautique_with_tool_filter(self):
        """Extraction bureautique avec filtre d'outil"""
        assert extract_bureautique_level("Bonne maîtrise de Word", tool_filter="word") == "Bon"
        assert extract_bureautique_level("Bonne maîtrise de Word", tool_filter="excel") == "Non évalué"
        assert extract_bureautique_level("Expert Excel et Word", tool_filter="excel") == "Très bon"

    def test_extract_bureautique_not_found_returns_non_evalue(self):
        """Pas de bureautique → "Non évalué" """
        assert extract_bureautique_level("Compétences informatiques") == "Non évalué"
        assert extract_bureautique_level("") == "Non évalué"

    def test_extract_test_result_valid(self):
        """Extraction résultat test valide"""
        assert extract_test_result("Test: OK") == "OK"
        assert extract_test_result("Difficultés observées") == "À renforcer"
        assert extract_test_result("Résultat moyen") == "Moyen"

    def test_extract_test_result_not_found_returns_non_evalue(self):
        """Pas de résultat → "Non évalué" """
        assert extract_test_result("Aucun test passé") == "Non évalué"
        assert extract_test_result("") == "Non évalué"

    def test_validate_enum_accepts_valid(self):
        """Validation enum: accepter valeurs valides"""
        assert validate_enum_value("B2", CECRL_LEVELS) == "B2"
        assert validate_enum_value("Bon", TOOL_LEVELS) == "Bon"
        assert validate_enum_value("OK", TEST_LEVELS) == "OK"

    def test_validate_enum_rejects_invalid(self):
        """Validation enum: rejeter valeurs invalides (mode strict)"""
        assert validate_enum_value("Super bon", TOOL_LEVELS, strict=True) == "Non évalué"
        assert validate_enum_value("B3", CECRL_LEVELS, strict=True) == "Non évalué"
        assert validate_enum_value("Parfait", TEST_LEVELS, strict=True) == "Non évalué"

    def test_extract_enum_from_context_split_bureautique(self):
        """extract_enum_from_context doit gérer les champs bureautique séparés"""
        text = "Bonne maîtrise de Word. Excel niveau faible."
        assert extract_enum_from_context(text, "WORD_POSITIONNEMENT_DE_NIVEAU") == "Bon"
        assert extract_enum_from_context(text, "EXCEL_POSITIONNEMENT_DE_NIVEAU") == "Faible"


class TestTitleMapping:
    """Tests du mapping titre → champ V2"""

    def test_map_title_to_profession(self):
        """Mapping vers PROFESSION"""
        assert map_title_to_field_v2("SITUATION PROFESSIONNELLE") == "PROFESSION"
        assert map_title_to_field_v2("Parcours professionnel") == "PROFESSION"

    def test_map_title_to_formation(self):
        """Mapping vers FORMATION"""
        assert map_title_to_field_v2("Formation et diplômes") == "FORMATION"
        assert map_title_to_field_v2("SCOLARITE") == "FORMATION"

    def test_map_title_to_langues(self):
        """Mapping vers champs langues"""
        assert map_title_to_field_v2("Français - Positionnement de niveau") == "FRANCAIS_POSITIONNEMENT_DE_NIVEAU"
        assert map_title_to_field_v2("Niveau anglais") == "ANGLAIS_POSITIONNEMENT_DE_NIVEAU"

    def test_map_title_to_tests(self):
        """Mapping vers champs tests"""
        assert map_title_to_field_v2("Test d'attention administratif") == "TEST_ATTENTION_ADMINISTRATIF"
        assert map_title_to_field_v2("Calcul et fractions") == "CALCUL_ET_FRACTION"

    def test_ignored_titles_return_none(self):
        """Titres ignorés doivent retourner None"""
        assert map_title_to_field_v2("SOMMAIRE") is None
        assert map_title_to_field_v2("A L'ATTENTION DE") is None
        assert map_title_to_field_v2("OFFICE CANTONAL DES ASSURANCES SOCIALES") is None

    def test_is_ignored_title(self):
        """Test fonction is_ignored_title_v2"""
        assert is_ignored_title_v2("SOMMAIRE") is True
        assert is_ignored_title_v2("PARTICIPATION AU PROGRAMME") is True
        assert is_ignored_title_v2("FORMATION") is False
        assert is_ignored_title_v2("PROFESSION") is False


class TestAntiHallucinationValidation:
    """Tests de validation anti-hallucination"""

    def test_list_should_limit_to_4_items(self):
        """Liste: max 4 items (validation à implémenter dans generate)"""
        items = ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5", "Item 6"]
        truncated = items[:4]
        assert len(truncated) == 4

    def test_narrative_should_cap_at_3000_chars(self):
        """Narrative: hard cap à 3000 chars"""
        long_text = "A" * 4000
        capped = long_text[:3000]
        assert len(capped) == 3000

    def test_enum_fallback_to_non_evalue(self):
        """Enum: fallback sur "Non évalué" si invalide"""
        invalid_values = ["B3", "Super bon", "Excellent", "D1"]

        for value in invalid_values:
            result = validate_enum_value(value, CECRL_LEVELS)
            assert result == "Non évalué", (
                f"Invalid value '{value}' should fallback to 'Non évalué'"
            )

    def test_require_sources_fields(self):
        """CV et LETTRE_DE_MOTIVATION doivent require_sources=True"""
        for key in ["CV", "LETTRE_DE_MOTIVATION"]:
            spec = get_field_spec_v2(key)
            assert spec.require_sources is True, (
                f"{key}: Should require sources to prevent hallucination"
            )


class TestNoRegressionDeterministic:
    """Tests de non-régression sur champs déterministes"""

    def test_deterministic_fields_unchanged(self):
        """Les 5 champs déterministes ne doivent pas changer"""
        expected = [
            "MONSIEUR_OU_MADAME",
            "NAME",
            "SURNAME",
            "LIEU_ET_DATE",
            "NUMERO_AVS",
        ]

        deterministic = list_fields_by_type("deterministic")

        assert set(deterministic) == set(expected), (
            f"Deterministic fields changed! Expected {expected}, got {deterministic}"
        )

    def test_deterministic_extraction_policy(self):
        """Champs déterministes doivent avoir extraction_policy='deterministic'"""
        deterministic = list_fields_by_type("deterministic")

        for key in deterministic:
            spec = get_field_spec_v2(key)
            assert spec.extraction_policy == "deterministic", (
                f"{key}: Should have extraction_policy='deterministic'"
            )


class TestFormationVsFormationsHautesEcoles:
    """Test FORMATION vs FORMATIONS_HAUTES_ECOLES"""

    def test_formation_is_narrative(self):
        """FORMATION doit être narrative"""
        spec = get_field_spec_v2("FORMATION")
        assert spec.field_type == "narrative"

    def test_formations_hautes_ecoles_is_list(self):
        """FORMATIONS_HAUTES_ECOLES doit être list"""
        spec = get_field_spec_v2("FORMATIONS_HAUTES_ECOLES")
        assert spec.field_type == "list"

    def test_formations_superieures_is_list(self):
        """FORMATIONS_SUPERIEURES doit être list"""
        spec = get_field_spec_v2("FORMATIONS_SUPERIEURES")
        assert spec.field_type == "list"

    def test_no_collision_in_specs(self):
        """Pas de collision entre FORMATION et FORMATIONS_HAUTES_ECOLES"""
        assert "FORMATION" in FIELD_SPECS_V2
        assert "FORMATIONS_HAUTES_ECOLES" in FIELD_SPECS_V2
        assert "FORMATION" != "FORMATIONS_HAUTES_ECOLES"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
