"""Tests pour positionnement_extractor.py"""

import pytest
from src.rhpro.positionnement_extractor import (
    extract_positionnement_level,
    is_positionnement_title,
    extract_positionnement_from_segments,
)


class TestExtractPositionnementLevel:
    """Tests pour extract_positionnement_level()"""
    
    def test_extracts_cecrl_c2(self):
        """Extrait niveau CECRL C2."""
        text = "FRANCAIS – POSITIONNEMENT DE NIVEAU :\nC2\n"
        assert extract_positionnement_level(text) == "C2"
    
    def test_extracts_cecrl_b1(self):
        """Extrait niveau CECRL B1."""
        text = "Niveau obtenu: B1"
        assert extract_positionnement_level(text) == "B1"
    
    def test_extracts_cecrl_case_insensitive(self):
        """Extrait niveau CECRL insensible à la casse."""
        assert extract_positionnement_level("niveau: b2") == "B2"
        assert extract_positionnement_level("NIVEAU: a1") == "A1"
    
    def test_extracts_fraction_score(self):
        """Extrait score fraction."""
        text = "ANGLAIS – POSITIONNEMENT DE NIVEAU : 12/20"
        assert extract_positionnement_level(text) == "12/20"
    
    def test_extracts_fraction_with_spaces(self):
        """Extrait score fraction avec espaces."""
        assert extract_positionnement_level("Score: 15 / 20") == "15/20"
    
    def test_extracts_percentage(self):
        """Extrait pourcentage."""
        assert extract_positionnement_level("Résultat: 85%") == "85%"
        assert extract_positionnement_level("Score: 90 %") == "90%"
    
    def test_rejects_invalid_percentage(self):
        """Rejette pourcentage invalide (>100)."""
        assert extract_positionnement_level("150%") == "Non renseigné"
    
    def test_returns_non_renseigne_when_no_level(self):
        """Retourne 'Non renseigné' si aucun niveau détecté."""
        text = "ANGLAIS – POSITIONNEMENT DE NIVEAU :\n(texte sans niveau)\n"
        assert extract_positionnement_level(text) == "Non renseigné"
    
    def test_returns_non_renseigne_when_empty(self):
        """Retourne 'Non renseigné' si texte vide."""
        assert extract_positionnement_level("") == "Non renseigné"
        assert extract_positionnement_level("   ") == "Non renseigné"
    
    def test_prioritizes_cecrl_over_scores(self):
        """Priorité CECRL sur scores."""
        text = "Niveau C1 obtenu avec 85%"
        assert extract_positionnement_level(text) == "C1"


class TestIsPositionnementTitle:
    """Tests pour is_positionnement_title()"""
    
    def test_detects_francais_positionnement(self):
        """Détecte 'FRANCAIS - POSITIONNEMENT DE NIVEAU'."""
        assert is_positionnement_title("FRANCAIS POSITIONNEMENT DE NIVEAU")
        assert is_positionnement_title("FRANCAIS - POSITIONNEMENT DE NIVEAU")
        assert is_positionnement_title("FRANCAIS – POSITIONNEMENT DE NIVEAU")  # Tiret typographique
        assert is_positionnement_title("FRANCAIS — POSITIONNEMENT DE NIVEAU")  # Tiret long
    
    def test_detects_anglais_positionnement(self):
        """Détecte 'ANGLAIS - POSITIONNEMENT DE NIVEAU'."""
        assert is_positionnement_title("ANGLAIS POSITIONNEMENT DE NIVEAU")
        assert is_positionnement_title("ANGLAIS - POSITIONNEMENT DE NIVEAU")
    
    def test_detects_allemand_positionnement(self):
        """Détecte 'ALLEMAND - POSITIONNEMENT DE NIVEAU'."""
        assert is_positionnement_title("ALLEMAND POSITIONNEMENT DE NIVEAU")
    
    def test_detects_word_excel_positionnement(self):
        """Détecte positionnement outils bureautiques."""
        assert is_positionnement_title("WORD POSITIONNEMENT DE NIVEAU")
        assert is_positionnement_title("EXCEL - POSITIONNEMENT DE NIVEAU")
        assert is_positionnement_title("POWERPOINT POSITIONNEMENT DE NIVEAU")
    
    def test_rejects_francais_niveau_only(self):
        """Rejette 'FRANCAIS NIVEAU 2' (pas de POSITIONNEMENT)."""
        assert not is_positionnement_title("FRANCAIS NIVEAU 2")
        assert not is_positionnement_title("FRANCAIS - NIVEAU 2")
    
    def test_rejects_other_tests(self):
        """Rejette autres sections tests."""
        assert not is_positionnement_title("TESTS METIERS")
        assert not is_positionnement_title("CALCUL NIVEAU 1")
        assert not is_positionnement_title("TRI ET CLASSEMENT")


class TestExtractPositionnementFromSegments:
    """Tests pour extract_positionnement_from_segments()"""
    
    def test_extracts_multiple_positionnements(self):
        """Extrait plusieurs niveaux de positionnement."""
        segments = [
            {
                "normalized_title": "FRANCAIS - POSITIONNEMENT DE NIVEAU",
                "lines": ["C2"],
            },
            {
                "normalized_title": "ANGLAIS - POSITIONNEMENT DE NIVEAU",
                "lines": ["Score: 12/20"],
            },
            {
                "normalized_title": "ALLEMAND - POSITIONNEMENT DE NIVEAU",
                "lines": ["(pas de test effectué)"],
            },
        ]
        
        result = extract_positionnement_from_segments(segments)
        
        assert result["francais"] == "C2"
        assert result["anglais"] == "12/20"
        assert result["allemand"] == "Non renseigné"
    
    def test_ignores_non_positionnement_segments(self):
        """Ignore les segments qui ne sont pas des positionnements."""
        segments = [
            {
                "normalized_title": "FRANCAIS NIVEAU 2",
                "lines": ["Grammaire: 15/20"],
            },
            {
                "normalized_title": "FRANCAIS - POSITIONNEMENT DE NIVEAU",
                "lines": ["B1"],
            },
        ]
        
        result = extract_positionnement_from_segments(segments)
        
        assert "francais" in result
        assert result["francais"] == "B1"
        assert len(result) == 1  # Seulement le positionnement


class TestAntiRegressionESSAI100:
    """Tests anti-régression basés sur ESSAI 100"""
    
    def test_t1_extraction_cecrl(self):
        """T1 — Extraction CECRL"""
        text = "FRANCAIS – POSITIONNEMENT DE NIVEAU :\nC2\n"
        assert extract_positionnement_level(text) == "C2"
    
    def test_t2_extraction_score(self):
        """T2 — Extraction score"""
        text = "ANGLAIS – POSITIONNEMENT DE NIVEAU : 12/20"
        assert extract_positionnement_level(text) == "12/20"
    
    def test_t3_no_hallucination(self):
        """T3 — No hallucination : retourne 'Non renseigné' sans appeler le LLM"""
        text = "ANGLAIS – POSITIONNEMENT DE NIVEAU :\n(texte sans niveau)\n"
        result = extract_positionnement_level(text)
        
        assert result == "Non renseigné"
        # NOTE: Le test que le LLM n'est PAS appelé doit être fait dans le pipeline principal
    
    def test_t4_normalisation_titres_variantes(self):
        """T4 — Normalisation titres avec tirets typographiques"""
        # Toutes ces variantes doivent être détectées
        assert is_positionnement_title("ANGLAIS - POSITIONNEMENT DE NIVEAU")
        assert is_positionnement_title("ANGLAIS – POSITIONNEMENT DE NIVEAU")  # U+2013
        assert is_positionnement_title("ANGLAIS — POSITIONNEMENT DE NIVEAU")  # U+2014
        assert is_positionnement_title("ANGLAIS  -  POSITIONNEMENT  DE  NIVEAU")  # Espaces multiples
