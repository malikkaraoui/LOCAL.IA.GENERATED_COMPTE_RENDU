"""Tests pour le module core/avs.py."""

import pytest
from core.avs import detect_avs_number


class TestDetectAvsNumber:
    """Tests pour la détection automatique du numéro AVS."""

    def test_detects_standard_format_with_dots(self):
        """Détecte le format standard avec points (756.XXXX.XXXX.XX)."""
        payload = {
            "documents": [
                {
                    "text": "Le numéro AVS du candidat est 756.1234.5678.90",
                }
            ]
        }
        result = detect_avs_number(payload)
        assert result == "756.1234.5678.90"

    def test_detects_format_without_dots(self):
        """Détecte le format sans points."""
        payload = {
            "documents": [
                {
                    "text": "AVS: 7561234567890",
                }
            ]
        }
        result = detect_avs_number(payload)
        assert result == "7561234567890"

    def test_returns_none_if_not_found(self):
        """Retourne None si aucun numéro AVS trouvé."""
        payload = {
            "documents": [
                {
                    "text": "Aucun numéro AVS dans ce document",
                }
            ]
        }
        result = detect_avs_number(payload)
        assert result is None

    def test_returns_first_match_if_multiple(self):
        """Retourne le premier match si plusieurs numéros."""
        payload = {
            "documents": [
                {
                    "text": "AVS 1: 756.1111.2222.33 et AVS 2: 756.4444.5555.66",
                }
            ]
        }
        result = detect_avs_number(payload)
        assert result == "756.1111.2222.33"

    def test_handles_empty_payload(self):
        """Gère un payload vide."""
        payload = {"documents": []}
        result = detect_avs_number(payload)
        assert result is None
