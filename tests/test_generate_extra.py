"""Tests pour couvrir davantage core/generate.py."""

import pytest
from core.generate import (
    sanitize_output,
    looks_like_json_or_markdown,
    truncate_lines,
    truncate_chars,
    validate_allowed_value
)


class TestAdditionalGenerateTests:
    """Tests supplémentaires pour generate.py."""

    def test_sanitize_handles_complex_markdown(self):
        """Gère du Markdown complexe."""
        text = "```json\n{\"key\": \"value\"}\n```\nPlus de texte"
        result = sanitize_output(text)
        assert "Plus de texte" in result
        assert "```" not in result

    def test_looks_like_json_detects_complex_structures(self):
        """Détecte des structures JSON complexes."""
        assert looks_like_json_or_markdown('{"nested": {"key": "value"}}')
        assert looks_like_json_or_markdown('[1, 2, {"a": "b"}]')

    def test_truncate_lines_preserves_content(self):
        """Préserve le contenu lors du tronquage."""
        text = "ligne1\nligne2\nligne3\nligne4\nligne5"
        result = truncate_lines(text, max_lines=3)
        assert "ligne1" in result
        assert "ligne2" in result

    def test_truncate_chars_adds_ellipsis(self):
        """Ajoute des ellipses lors du tronquage."""
        text = "a" * 100
        result = truncate_chars(text, max_chars=50)
        assert len(result) <= 55  # 50 + ellipsis

    def test_validate_with_special_characters(self):
        """Valide avec caractères spéciaux."""
        value, error = validate_allowed_value("François-José", ["François-José"])
        assert value == "François-José"
        assert error is None

    def test_validate_case_variations(self):
        """Gère les variations de casse."""
        value, error = validate_allowed_value("bon", ["Bon", "Moyen", "Faible"])
        assert value == "Bon"  # Retourne la valeur canonique
        assert error is None

    def test_sanitize_preserves_french_text(self):
        """Préserve le texte français."""
        text = "Résumé de l'évaluation"
        result = sanitize_output(text)
        assert "Résumé" in result
        assert "l'évaluation" in result
