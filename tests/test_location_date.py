"""Tests pour le module core/location_date.py."""

import pytest
from datetime import datetime
from core.location_date import build_location_date


class TestBuildLocationDate:
    """Tests pour la génération du champ LIEU_ET_DATE."""

    def test_manual_date_used_when_provided(self):
        """Utilise la date manuelle si fournie."""
        result = build_location_date(
            city="Genève",
            manual_date="15/12/2025",
            auto_date=False
        )
        assert result == "Genève, le 15/12/2025"

    def test_auto_date_generates_today(self):
        """Génère la date du jour si auto_date=True."""
        result = build_location_date(
            city="Lausanne",
            manual_date="",
            auto_date=True
        )
        # Vérifie que le format est correct et contient l'année actuelle
        assert "Lausanne, le " in result
        assert "2025" in result

    def test_handles_empty_city(self):
        """Gère une ville vide."""
        result = build_location_date(
            city="",
            manual_date="01/01/2025",
            auto_date=False
        )
        assert result == ", le 01/01/2025"

    def test_strips_whitespace(self):
        """Supprime les espaces superflus."""
        result = build_location_date(
            city="  Genève  ",
            manual_date="  15/12/2025  ",
            auto_date=False
        )
        assert result == "Genève, le 15/12/2025"
