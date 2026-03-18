# tests/test_report_types.py
from core.report_types import REPORT_TYPES, get_report_type, list_report_types


class TestReportTypes:
    def test_rapport_initial_exists(self):
        rt = get_report_type("rapport_initial")
        assert rt is not None
        assert rt["label"] == "Rapport Initial"

    def test_rapport_initial_has_7_sections(self):
        rt = get_report_type("rapport_initial")
        assert len(rt["sections"]) == 7
        assert "PROFESSION" in rt["sections"]
        assert "CONCLUSION" in rt["sections"]

    def test_rapport_initial_section_order(self):
        rt = get_report_type("rapport_initial")
        expected = [
            "PROFESSION", "FORMATION", "INCERTITUDE_ET_OBSTACLE",
            "ORIENTATION", "FORMATION_DURANT_MESURE", "STAGE", "CONCLUSION",
        ]
        assert rt["sections"] == expected

    def test_list_report_types(self):
        types = list_report_types()
        assert len(types) == 4
        keys = [t["key"] for t in types]
        assert "rapport_initial" in keys
        assert "rapport_final" in keys

    def test_unknown_type_returns_none(self):
        assert get_report_type("inexistant") is None

    def test_standby_types_have_empty_sections(self):
        for key in ["rapport_intermediaire", "rapport_stage", "rapport_final"]:
            rt = get_report_type(key)
            assert rt is not None
            assert rt["sections"] == [], f"{key} should have empty sections (standby)"
