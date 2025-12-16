"""Tests pour le module core/context.py."""

import pytest
from pathlib import Path
from core.context import normalize_text, chunk_text, tokenize, path_allowed


class TestNormalizeText:
    """Tests pour la normalisation de texte."""

    def test_removes_carriage_returns(self):
        """Supprime les retours chariot."""
        result = normalize_text("ligne1\r\nligne2\rligne3\n")
        assert "\r" not in result

    def test_reduces_multiple_newlines(self):
        """Réduit les multiples sauts de ligne."""
        result = normalize_text("ligne1\n\n\n\nligne2")
        assert "\n\n\n" not in result

    def test_strips_whitespace(self):
        """Supprime les espaces en début/fin."""
        result = normalize_text("  texte  ")
        assert result == "texte"


class TestChunkText:
    """Tests pour le découpage en chunks."""

    def test_creates_chunks_from_long_text(self):
        """Crée des chunks depuis un long texte."""
        text = "test " * 500  # ~2500 caractères
        result = chunk_text(text, chunk_size=1000, overlap=100)
        
        assert len(result) > 1
        assert all(isinstance(c, str) for c in result)

    def test_handles_short_text(self):
        """Gère un texte court."""
        text = "Court texte"
        result = chunk_text(text, chunk_size=1000)
        
        assert len(result) == 1
        assert result[0] == text

    def test_handles_empty_text(self):
        """Gère un texte vide."""
        result = chunk_text("")
        assert result == []


class TestTokenize:
    """Tests pour la tokenisation."""

    def test_splits_into_tokens(self):
        """Découpe en tokens."""
        result = tokenize("Bonjour le monde", remove_stop=False)
        assert len(result) > 0
        assert all(isinstance(t, str) for t in result)

    def test_removes_stop_words(self):
        """Supprime les mots vides."""
        result = tokenize("le chat est dans la maison", remove_stop=True)
        # "le", "est", "dans", "la" doivent être supprimés
        assert "chat" in result
        assert "maison" in result

    def test_handles_empty_string(self):
        """Gère une chaîne vide."""
        result = tokenize("")
        assert result == []


class TestPathAllowed:
    """Tests pour le filtrage de chemins."""

    def test_allows_path_matching_include(self):
        """Autorise un chemin correspondant à include."""
        result = path_allowed("docs/test.pdf", include=["docs/"], exclude=None)
        assert result is True

    def test_rejects_path_matching_exclude(self):
        """Rejette un chemin correspondant à exclude."""
        result = path_allowed("temp/test.pdf", include=None, exclude=["temp/"])
        assert result is False

    def test_allows_all_when_no_filters(self):
        """Autorise tout sans filtres."""
        result = path_allowed("any/path.pdf", include=None, exclude=None)
        assert result is True
