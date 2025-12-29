"""
Tests pour la troncature intelligente de texte (PATCH 11).

Valide :
- Troncature sans ajout de "..."
- Troncature à la fin d'une phrase (. ou ;)
- Fallback sur espace si pas de séparateur
- Multiplicateur de longueur max
"""

import pytest
from core.generate import truncate_chars
from core.field_specs import FieldSpec, apply_max_chars_multiplier


class TestTruncateChars:
    """Tests de la fonction truncate_chars()."""
    
    def test_no_truncation_when_under_limit(self):
        """Pas de troncature si texte plus court que la limite."""
        text = "Court texte."
        result = truncate_chars(text, max_chars=100)
        assert result == text
    
    def test_no_truncation_when_max_zero(self):
        """Pas de troncature si max_chars=0."""
        text = "Texte très long " * 100
        result = truncate_chars(text, max_chars=0)
        # Doit retourner le texte complet mais avec trailing spaces supprimés
        assert len(result) <= len(text)
        assert result.strip() == text.strip()
    
    def test_smart_truncation_at_period(self):
        """Troncature intelligente après un point."""
        text = "Courte phrase. Deuxième phrase très longue qui dépasse largement."
        result = truncate_chars(text, max_chars=25, smart=True)
        
        # "Courte phrase." = 15 chars, 60% de 25 = OK
        assert result == "Courte phrase."
        assert "..." not in result  # PAS de "..." ajouté
        assert "Deuxième" not in result
    
    def test_smart_truncation_at_semicolon(self):
        """Troncature intelligente après un point-virgule."""
        text = "Court A; Partie B très longue qui continue."
        result = truncate_chars(text, max_chars=18, smart=True)
        
        # "Court A;" = 8 chars, > 50% de 18 (9) = Pas OK, fallback sur espace
        # Donc attendu: "Court A" (dernier espace avant limite)
        assert "Court A" in result
        assert "..." not in result
    
    def test_smart_truncation_prefers_period_over_semicolon(self):
        """Préfère le dernier séparateur trouvé."""
        text = "A; B. C très long."
        result = truncate_chars(text, max_chars=7, smart=True)
        
        # Doit prendre le dernier séparateur avant limite (. avant C)
        assert result == "A; B."
    
    def test_smart_truncation_fallback_to_space(self):
        """Fallback sur espace si pas de séparateur."""
        text = "Mot1 Mot2 Mot3 Mot4 Mot5"
        result = truncate_chars(text, max_chars=15, smart=True)
        
        # Doit couper au dernier espace avant limite
        assert "Mot4" in result or "Mot3" in result
        assert "..." not in result
        assert not result.endswith(" Mot5")
    
    def test_smart_truncation_requires_50_percent_usage(self):
        """Séparateur doit être après 50% de la limite."""
        text = "A. " + "B" * 100
        result = truncate_chars(text, max_chars=50, smart=True)
        
        # Point trop tôt (2 chars sur 50) → devrait fallback
        assert len(result) > 10  # Plus que juste "A."
    
    def test_brutal_truncation_when_not_smart(self):
        """Troncature brutale si smart=False."""
        text = "Première phrase. Deuxième phrase."
        result = truncate_chars(text, max_chars=20, smart=False)
        
        # Doit couper exactement à 20 caractères
        assert len(result) <= 20
        assert result.startswith("Première phrase.")
    
    def test_no_ellipsis_added_ever(self):
        """PATCH 11 : Plus jamais de "..." ajouté automatiquement."""
        texts = [
            "Court",
            "Première phrase. Deuxième phrase très longue.",
            "A; B; C; D; E; F; G",
            "Mot " * 1000
        ]
        
        for text in texts:
            for max_chars in [10, 50, 100, 500]:
                result = truncate_chars(text, max_chars=max_chars, smart=True)
                assert "…" not in result, f"Ellipsis trouvé dans: {result}"
                assert "..." not in result, f"Triple point trouvé dans: {result}"
    
    def test_strips_trailing_whitespace(self):
        """Supprime espaces en fin de résultat."""
        text = "Phrase avec espaces.   "
        result = truncate_chars(text, max_chars=100)
        assert not result.endswith(" ")


class TestApplyMaxCharsMultiplier:
    """Tests du multiplicateur de longueur."""
    
    def test_multiplier_one_returns_same_spec(self):
        """Multiplicateur 1.0 retourne spec inchangée."""
        spec = FieldSpec(
            key="TEST",
            field_type="narrative",
            query="Test",
            instructions="Test",
            max_chars=500,
            max_lines=4
        )
        
        result = apply_max_chars_multiplier(spec, 1.0)
        assert result.max_chars == 500
        assert result.max_lines == 4
    
    def test_multiplier_doubles_limits(self):
        """Multiplicateur 2.0 double les limites."""
        spec = FieldSpec(
            key="TEST",
            field_type="narrative",
            query="Test",
            instructions="Test",
            max_chars=500,
            max_lines=4
        )
        
        result = apply_max_chars_multiplier(spec, 2.0)
        assert result.max_chars == 1000
        assert result.max_lines == 8
    
    def test_multiplier_halves_limits(self):
        """Multiplicateur 0.5 divise les limites par 2."""
        spec = FieldSpec(
            key="TEST",
            field_type="narrative",
            query="Test",
            instructions="Test",
            max_chars=500,
            max_lines=4
        )
        
        result = apply_max_chars_multiplier(spec, 0.5)
        assert result.max_chars == 250
        assert result.max_lines == 2
    
    def test_minimum_values_enforced(self):
        """Limites minimales appliquées (50 chars, 1 line)."""
        spec = FieldSpec(
            key="TEST",
            field_type="short",
            query="Test",
            instructions="Test",
            max_chars=100,
            max_lines=1
        )
        
        # 100 * 0.1 = 10 → devrait être ramené à 50
        result = apply_max_chars_multiplier(spec, 0.1)
        assert result.max_chars == 50  # Minimum strict
        assert result.max_lines == 1   # Minimum strict
    
    def test_preserves_other_fields(self):
        """Préserve les autres champs du FieldSpec."""
        spec = FieldSpec(
            key="PROFESSION",
            field_type="narrative",
            query="Profession query",
            instructions="Profession instructions",
            max_chars=500,
            max_lines=4,
            require_sources=True,
            skip_llm_if_no_sources=False,
            allowed_values=["A", "B"]
        )
        
        result = apply_max_chars_multiplier(spec, 2.0)
        
        assert result.key == "PROFESSION"
        assert result.field_type == "narrative"
        assert result.query == "Profession query"
        assert result.instructions == "Profession instructions"
        assert result.require_sources is True
        assert result.skip_llm_if_no_sources is False
        assert result.allowed_values == ["A", "B"]
    
    def test_zero_max_chars_preserved(self):
        """max_chars=0 (pas de limite) préservé."""
        spec = FieldSpec(
            key="TEST",
            field_type="narrative",
            query="Test",
            instructions="Test",
            max_chars=0,
            max_lines=4
        )
        
        result = apply_max_chars_multiplier(spec, 2.0)
        assert result.max_chars == 0
        assert result.max_lines == 8


class TestRealWorldScenarios:
    """Tests sur scénarios réels d'utilisation."""
    
    def test_narrative_field_500_chars(self):
        """Champ narrative par défaut : 500 chars."""
        text = "Le candidat possède une solide expérience dans le domaine de la gestion d'équipe. " * 10
        result = truncate_chars(text, max_chars=500, smart=True)
        
        assert len(result) <= 500
        assert "..." not in result
        # Doit se terminer par un séparateur ou mot complet
        assert result[-1] in ['.', ';'] or not result.endswith(' ')
    
    def test_multiplier_2x_gives_1000_chars(self):
        """Avec multiplicateur 2x, narrative passe à 1000 chars."""
        spec = FieldSpec(
            key="PROFESSION",
            field_type="narrative",
            query="Test",
            instructions="Test",
            max_chars=500,
            max_lines=4
        )
        
        doubled = apply_max_chars_multiplier(spec, 2.0)
        assert doubled.max_chars == 1000
        
        # Test avec long texte
        long_text = "Phrase complète. " * 100
        result = truncate_chars(long_text, max_chars=doubled.max_chars, smart=True)
        
        assert len(result) <= 1000
        assert result.endswith('.')
    
    def test_multiplier_0_5x_gives_250_chars(self):
        """Avec multiplicateur 0.5x, narrative passe à 250 chars."""
        spec = FieldSpec(
            key="PROFESSION",
            field_type="narrative",
            query="Test",
            instructions="Test",
            max_chars=500,
            max_lines=4
        )
        
        halved = apply_max_chars_multiplier(spec, 0.5)
        assert halved.max_chars == 250
        
        # Test avec texte moyen
        medium_text = "Expérience significative en gestion. Le candidat maîtrise les outils bureautiques. Formation continue."
        result = truncate_chars(medium_text, max_chars=halved.max_chars, smart=True)
        
        assert len(result) <= 250
        assert "..." not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
