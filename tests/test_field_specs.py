"""Tests pour le module core/field_specs.py."""

import pytest
from core.field_specs import get_field_spec, FIELD_SPECS, FieldSpec, normalize_allowed_value


class TestGetFieldSpec:
    """Tests pour la récupération de spécifications de champs."""

    def test_returns_spec_for_known_field(self):
        """Retourne la spec pour un champ connu."""
        result = get_field_spec("NOM")
        assert result is not None
        assert isinstance(result, FieldSpec)
        assert result.key in ("NOM", "NAME", "SURNAME")

    def test_returns_default_for_unknown_field(self):
        """Retourne le spec par défaut pour un champ inconnu."""
        result = get_field_spec("CHAMP_TOTALEMENT_INEXISTANT_999")
        assert result is not None
        assert isinstance(result, FieldSpec)

    def test_field_spec_has_required_properties(self):
        """Chaque spec a les propriétés requises."""
        result = get_field_spec("PROFESSION")
        assert hasattr(result, "key")
        assert hasattr(result, "field_type")
        assert hasattr(result, "query")


class TestFieldSpecsConstant:
    """Tests pour la constante FIELD_SPECS."""

    def test_field_specs_is_dict(self):
        """FIELD_SPECS est un dictionnaire."""
        assert isinstance(FIELD_SPECS, dict)
        assert len(FIELD_SPECS) > 0

    def test_all_specs_are_field_spec_instances(self):
        """Tous les specs sont des instances de FieldSpec."""
        for spec in FIELD_SPECS.values():
            assert isinstance(spec, FieldSpec)

    def test_has_default_spec(self):
        """Contient une spec DEFAULT."""
        assert "DEFAULT" in FIELD_SPECS
        assert isinstance(FIELD_SPECS["DEFAULT"], FieldSpec)

    def test_no_duplicate_keys(self):
        """Pas de clés dupliquées."""
        keys = list(FIELD_SPECS.keys())
        assert len(keys) == len(set(keys))


class TestNormalizeAllowedValue:
    """Tests pour la normalisation des valeurs autorisées."""

    def test_lowercases_text(self):
        """Convertit en minuscules."""
        result = normalize_allowed_value("TEXTE")
        assert result == result.lower()

    def test_strips_whitespace(self):
        """Supprime les espaces."""
        result = normalize_allowed_value("  texte  ")
        assert result == "texte"

    def test_removes_accents(self):
        """Supprime les accents."""
        result = normalize_allowed_value("éàü")
        assert "é" not in result
        assert "à" not in result

    def test_handles_empty_string(self):
        """Gère une chaîne vide."""
        result = normalize_allowed_value("")
        assert result == ""
