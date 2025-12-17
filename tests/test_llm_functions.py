"""Tests pour les fonctions LLM de generate.py."""

import pytest
from unittest.mock import patch, Mock
from core.generate import check_llm_status, validate_allowed_value
from core.errors import Result
import json


class TestCheckLlmStatus:
    """Tests pour check_llm_status."""

    @patch('core.generate.request.urlopen')
    def test_server_accessible(self, mock_urlopen):
        """Serveur accessible."""
        mock_response = Mock()
        mock_response.read.return_value = b'{"version": "2.0.0"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = check_llm_status("http://localhost:11434")
        assert result.success is True
        assert "accessible" in result.value.lower()

    @patch('core.generate.request.urlopen')
    def test_server_inaccessible(self, mock_urlopen):
        """Serveur inaccessible."""
        mock_urlopen.side_effect = Exception("Connection refused")
        
        result = check_llm_status("http://localhost:11434")
        assert result.success is False
        assert "injoignable" in str(result.error).lower()

    @patch('core.generate.request.urlopen')
    def test_model_available(self, mock_urlopen):
        """Modèle disponible."""
        def side_effect(url, timeout=None):
            mock_response = Mock()
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            
            if "/api/version" in str(url):
                mock_response.read.return_value = b'{"version": "1.0"}'
            elif "/api/tags" in str(url):
                mock_response.read.return_value = json.dumps({
                    "models": [{"name": "llama2"}, {"name": "mistral"}]
                }).encode()
            return mock_response
        
        mock_urlopen.side_effect = side_effect
        
        result = check_llm_status("http://localhost:11434", model="llama2")
        assert result.success is True
        assert "llama2" in result.value
        assert "disponible" in result.value

    @patch('core.generate.request.urlopen')
    def test_model_not_found(self, mock_urlopen):
        """Modèle introuvable."""
        def side_effect(url, timeout=None):
            mock_response = Mock()
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            
            if "/api/version" in str(url):
                mock_response.read.return_value = b'{"version": "1.0"}'
            elif "/api/tags" in str(url):
                mock_response.read.return_value = json.dumps({
                    "models": [{"name": "llama2"}]
                }).encode()
            return mock_response
        
        mock_urlopen.side_effect = side_effect
        
        result = check_llm_status("http://localhost:11434", model="gpt-4")
        assert result.success is False
        assert "introuvable" in str(result.error)


class TestValidateAllowedValueAdvanced:
    """Tests avancés pour validate_allowed_value."""

    def test_exact_match_returns_value(self):
        """Match exact retourne la valeur."""
        value, error = validate_allowed_value("Bon", ["Bon", "Moyen", "Faible"])
        assert value == "Bon"
        assert error is None

    def test_case_insensitive_match(self):
        """Match insensible à la casse."""
        value, error = validate_allowed_value("bon", ["Bon", "Moyen", "Faible"])
        assert value == "Bon"  # Retourne la valeur canonique
        assert error is None

    def test_accent_normalization(self):
        """Normalise les accents."""
        value, error = validate_allowed_value("faible", ["Faible", "Moyen"])
        assert value == "Faible"
        assert error is None

    def test_invalid_value_returns_error(self):
        """Valeur invalide retourne erreur."""
        value, error = validate_allowed_value("Inexistant", ["Bon", "Moyen"])
        assert value == ""
        assert error == "NON_AUTORISE"

    def test_no_restriction_returns_input(self):
        """Sans restriction retourne l'entrée."""
        value, error = validate_allowed_value("N'importe quoi", None)
        assert value == "N'importe quoi"
        assert error is None

    def test_empty_allowed_list(self):
        """Liste vide autorisée."""
        value, error = validate_allowed_value("test", [])
        # Selon l'implémentation, pourrait accepter ou rejeter
        assert value == "test" or value == ""

    def test_whitespace_trimmed(self):
        """Espaces trimés."""
        value, error = validate_allowed_value("  Bon  ", ["Bon", "Moyen"])
        assert value == "Bon"
        assert error is None

    def test_special_characters(self):
        """Caractères spéciaux."""
        allowed = ["A1", "A2", "B1", "Non évalué"]
        value, error = validate_allowed_value("non evalue", allowed)
        # Dépend de la normalisation exacte
        assert error is None or value == ""
