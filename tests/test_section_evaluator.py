# tests/test_section_evaluator.py
from core.section_evaluator import evaluate_section, SectionEvaluation, SectionCheck
from core.field_specs_v3 import get_field_spec_v3


class TestSectionEvaluator:
    def test_empty_text_returns_vide(self):
        spec = get_field_spec_v3("PROFESSION")
        result = evaluate_section(spec, "")
        assert result.status == "VIDE"
        assert result.score == 0.0

    def test_non_renseigne_returns_vide(self):
        spec = get_field_spec_v3("PROFESSION")
        result = evaluate_section(spec, "Non renseigné")
        assert result.status == "VIDE"

    def test_good_profession_text(self):
        spec = get_field_spec_v3("PROFESSION")
        text = (
            "Monsieur Dupont était en arrêt maladie depuis 2022. "
            "Il occupait un poste de technicien de maintenance dans une PME industrielle. "
            "Ses missions principales comprenaient la maintenance préventive des machines, "
            "le diagnostic de pannes et la gestion des stocks de pièces détachées. "
            "Il travaillait en équipe de 5 personnes, principalement sur le terrain. "
            "Suite à un accident du travail, il a dû cesser son activité. "
            "Ses compétences techniques et sa polyvalence sont transférables "
            "vers des postes de contrôle qualité ou de coordination technique."
        )
        result = evaluate_section(spec, text)
        assert result.status == "BON"
        assert result.score >= 0.75

    def test_partial_profession_text(self):
        spec = get_field_spec_v3("PROFESSION")
        text = "Monsieur Dupont était technicien. Il travaillait en équipe."
        result = evaluate_section(spec, text)
        assert result.status == "A_REVOIR"
        assert result.score < 0.75
        # Should identify missing elements
        missing = [c.element for c in result.checks if not c.found]
        assert len(missing) > 0

    def test_comment_lists_missing_elements(self):
        spec = get_field_spec_v3("PROFESSION")
        text = "Monsieur Dupont était technicien."
        result = evaluate_section(spec, text)
        assert result.comment  # Non-empty comment
        assert "manque" in result.comment.lower() or "absent" in result.comment.lower()

    def test_checks_contain_all_required_elements(self):
        spec = get_field_spec_v3("PROFESSION")
        result = evaluate_section(spec, "Du texte quelconque.")
        element_names = [c.element for c in result.checks]
        for req in spec.required_elements:
            assert req in element_names

    def test_keywords_matched_populated(self):
        spec = get_field_spec_v3("PROFESSION")
        text = "Il était en arrêt maladie et occupait un poste de technicien."
        result = evaluate_section(spec, text)
        found_checks = [c for c in result.checks if c.found]
        for check in found_checks:
            assert len(check.keywords_matched) > 0

    def test_conclusion_evaluation(self):
        spec = get_field_spec_v3("CONCLUSION")
        text = (
            "Le stage a confirmé la cible professionnelle de Monsieur Dupont. "
            "Les résultats du stage sont positifs et les limitations physiques "
            "ont été respectées tout au long de la mesure."
        )
        result = evaluate_section(spec, text)
        assert result.status == "BON"
