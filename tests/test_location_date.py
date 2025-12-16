"""Tests pour le module core/location_date.py."""

from datetime import datetime

from core.location_date import build_location_date


class TestBuildLocationDate:
    """Tests pour la génération du champ LIEU_ET_DATE."""

    def test_manual_date_used_when_provided(self):
        """Utilise la date manuelle si fournie."""
        result = build_location_date(
            location="Genève",
            manual_value="Genève, le 15/12/2025",
            auto_date=False
        )
        assert result == "Genève, le 15/12/2025"

    def test_auto_date_generates_today(self):
        """Génère la date du jour si auto_date=True."""
        fixed_date = datetime(2025, 12, 16)
        result = build_location_date(
            location="Lausanne",
            manual_value="",
            auto_date=True,
            reference_time=fixed_date
        )
        assert result == "Lausanne, le 16/12/2025"

    def test_handles_empty_location(self):
        """Gère une ville vide."""
        result = build_location_date(
            location="",
            manual_value="01/01/2025",
            auto_date=False
        )
        assert result == "01/01/2025"

    def test_strips_whitespace(self):
        """Supprime les espaces superflus."""
        result = build_location_date(
            location="  Genève  ",
            manual_value="  Genève, le 15/12/2025  ",
            auto_date=False
        )
        assert result == "Genève, le 15/12/2025"
