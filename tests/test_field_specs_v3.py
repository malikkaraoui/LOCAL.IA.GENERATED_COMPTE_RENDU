# tests/test_field_specs_v3.py
from core.field_specs_v3 import FieldSpecV3, get_field_spec_v3, get_specs_for_report_type, FIELD_SPECS_V3


class TestFieldSpecV3:
    def test_profession_spec_exists(self):
        spec = get_field_spec_v3("PROFESSION")
        assert spec is not None
        assert isinstance(spec, FieldSpecV3)

    def test_profession_has_required_elements(self):
        spec = get_field_spec_v3("PROFESSION")
        assert len(spec.required_elements) >= 4
        assert "statut" in spec.required_elements
        assert "raison_arret" in spec.required_elements

    def test_profession_is_immutable(self):
        spec = get_field_spec_v3("PROFESSION")
        assert spec.immutable is True

    def test_profession_sources(self):
        spec = get_field_spec_v3("PROFESSION")
        assert "journal" in spec.sources
        assert "cv" in spec.sources
        assert "msg" in spec.sources

    def test_profession_limits(self):
        spec = get_field_spec_v3("PROFESSION")
        assert spec.max_chars == 3000
        assert spec.min_lines == 15
        assert spec.max_lines == 30

    def test_all_7_rapport_initial_specs_exist(self):
        keys = [
            "PROFESSION", "FORMATION", "INCERTITUDE_ET_OBSTACLE",
            "ORIENTATION", "FORMATION_DURANT_MESURE", "STAGE", "CONCLUSION",
        ]
        for key in keys:
            spec = get_field_spec_v3(key)
            assert spec is not None, f"Missing spec for {key}"
            assert spec.required_elements, f"{key} has no required_elements"
            assert spec.element_keywords, f"{key} has no element_keywords"

    def test_get_specs_for_report_type(self):
        specs = get_specs_for_report_type("rapport_initial")
        assert len(specs) == 7
        assert specs[0].key == "PROFESSION"
        assert specs[-1].key == "CONCLUSION"

    def test_get_specs_for_unknown_type_returns_empty(self):
        specs = get_specs_for_report_type("inexistant")
        assert specs == []

    def test_conclusion_short_limits(self):
        spec = get_field_spec_v3("CONCLUSION")
        assert spec.min_lines == 3
        assert spec.max_lines == 5

    def test_each_spec_has_element_keywords_for_all_required(self):
        for key, spec in FIELD_SPECS_V3.items():
            for elem in spec.required_elements:
                assert elem in spec.element_keywords, (
                    f"{key}: required_element '{elem}' missing from element_keywords"
                )
                assert len(spec.element_keywords[elem]) > 0, (
                    f"{key}: element_keywords['{elem}'] is empty"
                )

    def test_unknown_spec_returns_none(self):
        assert get_field_spec_v3("INEXISTANT") is None
