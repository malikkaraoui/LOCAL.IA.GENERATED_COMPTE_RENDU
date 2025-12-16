"""Tests pour le module core/generate.py."""

import pytest
from core.generate import (
    sanitize_output,
    looks_like_json_or_markdown,
    truncate_lines,
    truncate_chars,
    validate_allowed_value,
)


class TestSanitizeOutput:
    """Tests pour la fonction sanitize_output."""

    def test_removes_code_blocks(self):
        """Supprime les marqueurs de code."""
        assert sanitize_output("```json\ntest\n```") == "test"

    def test_removes_json_prefix(self):
        """Supprime le préfixe JSON."""
        assert sanitize_output("json: test content") == "test content"

    def test_handles_empty_string(self):
        """Gère les chaînes vides."""
        assert sanitize_output("") == ""

    def test_strips_whitespace(self):
        """Supprime les espaces en début/fin."""
        assert sanitize_output("  content  ") == "content"


class TestLooksLikeJsonOrMarkdown:
    """Tests pour la détection JSON/Markdown."""

    def test_detects_json_object(self):
        """Détecte un objet JSON."""
        assert looks_like_json_or_markdown('{"key": "value"}') is True

    def test_detects_json_array(self):
        """Détecte un tableau JSON."""
        assert looks_like_json_or_markdown('[1, 2, 3]') is True

    def test_detects_code_blocks(self):
        """Détecte les blocs de code."""
        assert looks_like_json_or_markdown('```python\ncode\n```') is True

    def test_plain_text_is_false(self):
        """Le texte brut n'est pas détecté comme JSON/Markdown."""
        assert looks_like_json_or_markdown('Simple text') is False


class TestTruncateLines:
    """Tests pour la troncature par lignes."""

    def test_truncates_to_max_lines(self):
        """Tronque au nombre de lignes max."""
        text = "line1\nline2\nline3\nline4"
        result = truncate_lines(text, max_lines=2)
        assert result == "line1\nline2"

    def test_no_truncation_if_under_limit(self):
        """Pas de troncature si sous la limite."""
        text = "line1\nline2"
        result = truncate_lines(text, max_lines=5)
        assert result == "line1\nline2"

    def test_ignores_empty_lines(self):
        """Ignore les lignes vides."""
        text = "line1\n\nline2\n\nline3"
        result = truncate_lines(text, max_lines=2)
        assert result == "line1\nline2"


class TestTruncateChars:
    """Tests pour la troncature par caractères."""

    def test_truncates_long_text(self):
        """Tronque le texte trop long."""
        text = "a" * 100
        result = truncate_chars(text, max_chars=50)
        assert len(result) == 50
        assert result.endswith("…")

    def test_no_truncation_if_short(self):
        """Pas de troncature si texte court."""
        text = "short"
        result = truncate_chars(text, max_chars=50)
        assert result == text

    def test_handles_zero_max(self):
        """Gère max_chars=0 (pas de limite)."""
        text = "a" * 100
        result = truncate_chars(text, max_chars=0)
        assert result == text


class TestValidateAllowedValue:
    """Tests pour la validation des valeurs autorisées."""

    def test_exact_match(self):
        """Match exact avec une valeur autorisée."""
        result, error = validate_allowed_value("A1", ["A1", "A2", "B1"])
        assert result == "A1"
        assert error is None

    def test_case_insensitive_match(self):
        """Match insensible à la casse."""
        result, error = validate_allowed_value("a1", ["A1", "A2"])
        assert result == "A1"
        assert error is None

    def test_rejects_invalid_value(self):
        """Rejette une valeur non autorisée."""
        result, error = validate_allowed_value("C1", ["A1", "A2"])
        assert result == ""
        assert error == "NON_AUTORISE"

    def test_no_restriction_if_allowed_is_none(self):
        """Pas de restriction si allowed=None."""
        result, error = validate_allowed_value("anything", None)
        assert result == "anything"
        assert error is None
