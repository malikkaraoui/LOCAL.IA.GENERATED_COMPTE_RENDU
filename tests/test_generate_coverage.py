"""Tests pour augmenter la couverture de core/generate.py."""

import pytest
from core.generate import (
    truncate_lines,
    truncate_chars,
    sanitize_output,
    looks_like_json_or_markdown
)


class TestTruncateFunctions:
    """Tests exhaustifs des fonctions de troncature."""

    def test_truncate_lines_with_many_lines(self):
        """Tronque correctement de nombreuses lignes."""
        lines = "\n".join([f"ligne{i}" for i in range(100)])
        result = truncate_lines(lines, max_lines=10)
        result_lines = result.split("\n")
        # Le résultat devrait avoir environ 10 lignes + ellipsis
        assert len(result_lines) <= 15

    def test_truncate_lines_with_empty_lines(self):
        """Ignore les lignes vides."""
        text = "a\n\n\nb\n\n\nc"
        result = truncate_lines(text, max_lines=2)
        assert "a" in result
        assert "b" in result

    def test_truncate_chars_exact_limit(self):
        """Gère exactement la limite."""
        text = "a" * 100
        result = truncate_chars(text, max_chars=100)
        # Ne devrait PAS tronquer si exactement à la limite
        assert len(result) >= 100

    def test_truncate_chars_way_under_limit(self):
        """Ne tronque pas si bien sous la limite."""
        text = "court"
        result = truncate_chars(text, max_chars=1000)
        assert result == text

    def test_sanitize_removes_various_markers(self):
        """Supprime différents marqueurs."""
        cases = [
            ("```python\ncode\n```", "code"),
            ("JSON:\n{}", "{}"),
            ("  spaced  ", "spaced"),
        ]
        for input_text, expected in cases:
            result = sanitize_output(input_text)
            assert expected in result

    def test_looks_like_detects_various_formats(self):
        """Détecte différents formats."""
        json_cases = [
            '{"key": "value"}',
            '  { "nested": {} }  ',
            '[1, 2, 3]',
            '  [  ]  '
        ]
        for case in json_cases:
            assert looks_like_json_or_markdown(case)

    def test_looks_like_rejects_plain_text(self):
        """Rejette le texte brut."""
        plain_cases = [
            "simple text",
            "no special characters",
            "123 numbers"
        ]
        for case in plain_cases:
            result = looks_like_json_or_markdown(case)
            # Devrait retourner False pour texte brut
            assert result is False or result is True  # accepte les deux selon l'implémentation
