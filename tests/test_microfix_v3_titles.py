"""
Tests pour Micro-Fix v3 : Tests/Sections internes, conteneurs, max_lines

Contraintes testées:
1. Mapping vers section interne 'tests' (EVALUATIONS, positionnements, etc.)
2. Mapping "RESULTATS DE LA DISCUSSION" vers pistes_metiers
3. Conteneurs (SOCIALES, PROFESSIONNELLES, etc.) ne créent pas de sections
4. apply_max_lines() compresse sans inventer de contenu
"""
import pytest
from src.rhpro.dataset_training import (
    is_container_heading,
    apply_max_lines,
    match_title_to_canonical,
    normalize_heading_for_titles,
    SEED_SECTION_TITLE_MAP,
    CONTAINER_HEADINGS,
)


class TestSectionTests:
    """Tests pour la section interne 'tests' (non-canonique)"""
    
    def test_mapping_evaluations(self):
        """EVALUATIONS doit mapper vers 'tests'"""
        assert match_title_to_canonical("EVALUATIONS") == "tests"
        assert match_title_to_canonical("evaluations") == "tests"  # casse
        assert match_title_to_canonical("EVALUATION") == "tests"
    
    def test_mapping_francais_niveau(self):
        """Tests de français doivent mapper vers 'tests'"""
        assert match_title_to_canonical("FRANCAIS - NIVEAU 2") == "tests"
        assert match_title_to_canonical("FRANCAIS - NIVEAU 3") == "tests"
        assert match_title_to_canonical("FRANCAIS - NIVEAU 2/3") == "tests"
        assert match_title_to_canonical("FRANCAIS NIVEAU 2") == "tests"
    
    def test_mapping_positionnement(self):
        """Tests de positionnement doivent mapper vers 'tests'"""
        assert match_title_to_canonical("POSITIONNEMENT DE NIVEAU DE FRANCAIS") == "tests"
        assert match_title_to_canonical("WORD - POSITIONNEMENT DE NIVEAU") == "tests"
        assert match_title_to_canonical("EXCEL - POSITIONNEMENT DE NIVEAU") == "tests"
        assert match_title_to_canonical("POWERPOINT - POSITIONNEMENT DE NIVEAU") == "tests"
    
    def test_mapping_outlook(self):
        """OUTLOOK doit mapper vers 'tests'"""
        assert match_title_to_canonical("OUTLOOK 2010") == "tests"
        assert match_title_to_canonical("OUTLOOK") == "tests"


class TestResultatsDiscussion:
    """Tests pour mapping RESULTATS DE LA DISCUSSION vers pistes_metiers"""
    
    def test_mapping_resultats_discussion(self):
        """RESULTATS DE LA DISCUSSION doit mapper vers pistes_metiers"""
        assert match_title_to_canonical("RESULTATS DE LA DISCUSSION AVEC L'ASSURE") == "pistes_metiers"
        assert match_title_to_canonical("RESULTATS DE LA DISCUSSION AVEC L ASSURE") == "pistes_metiers"
        assert match_title_to_canonical("RESULTATS DE LA DISCUSSION") == "pistes_metiers"
    
    def test_mapping_resultats_variantes_accents(self):
        """Variantes avec accents doivent fonctionner"""
        # La normalisation enlève les accents
        title_accents = "RÉSULTATS DE LA DISCUSSION AVEC L'ASSURÉ"
        # normalize_heading_for_titles enlève les accents
        normalized = normalize_heading_for_titles(title_accents)
        assert normalized == "RESULTATS DE LA DISCUSSION AVEC L'ASSURE"
        # Le mapping doit fonctionner
        assert match_title_to_canonical(title_accents) == "pistes_metiers"


class TestContainerHeadings:
    """Tests pour conteneurs/sous-titres (ne doivent pas créer de sections)"""
    
    def test_container_exact_match(self):
        """Conteneurs définis doivent être détectés"""
        assert is_container_heading("RESSOURCES COMPORTEMENTALES")
        assert is_container_heading("SOCIALES")
        assert is_container_heading("PROFESSIONNELLES")
        assert is_container_heading("RESSOURCES")
    
    def test_container_case_insensitive(self):
        """Conteneurs doivent être détectés (casse)"""
        assert is_container_heading("sociales")
        assert is_container_heading("Professionnelles")
        assert is_container_heading("ressources comportementales")
    
    def test_container_short_titles(self):
        """Titres courts (1-2 mots) non mappés = conteneurs"""
        # Titre court non mappé explicitement
        assert is_container_heading("COURT")
        assert is_container_heading("UN MOT")
    
    def test_not_container_mapped_titles(self):
        """Titres mappés explicitement ne doivent PAS être conteneurs"""
        # Ces titres sont mappés explicitement dans SEED_SECTION_TITLE_MAP
        assert not is_container_heading("FORMATION")
        assert not is_container_heading("COMPETENCES")
        assert not is_container_heading("OBJECTIFS")
    
    def test_not_container_long_titles(self):
        """Titres longs non mappés ne doivent PAS être conteneurs automatiquement"""
        long_title = "VOICI UN TRES LONG TITRE DE SECTION QUI NE DOIT PAS ETRE CONTENEUR"
        # Plus de 20 caractères
        assert not is_container_heading(long_title)


class TestApplyMaxLines:
    """Tests pour apply_max_lines() - compression sans invention"""
    
    def test_text_already_within_limit(self):
        """Texte déjà dans la limite ne doit pas être modifié"""
        text = "Ligne 1\nLigne 2\nLigne 3"
        result = apply_max_lines(text, 5)
        assert result == text
        assert len(result.split('\n')) <= 5
    
    def test_compress_to_max_lines(self):
        """Texte > max_lines doit être compressé"""
        lines = [f"Ligne {i}" for i in range(1, 11)]  # 10 lignes
        text = '\n'.join(lines)
        
        result = apply_max_lines(text, 4)
        result_lines = result.split('\n')
        
        # Doit avoir exactement max_lines
        assert len(result_lines) == 4
        
        # Les 3 premières lignes doivent être intactes
        assert result_lines[0] == "Ligne 1"
        assert result_lines[1] == "Ligne 2"
        assert result_lines[2] == "Ligne 3"
        
        # La dernière ligne doit contenir le reste fusionné
        assert "Ligne 4" in result_lines[3]
        assert ";" in result_lines[3]  # Séparateur
    
    def test_no_invented_content(self):
        """Aucune ligne ne doit être ajoutée ex nihilo"""
        text = "Alpha\nBeta\nGamma\nDelta\nEpsilon"
        result = apply_max_lines(text, 3)
        
        # Vérifier que toutes les lignes originales sont présentes
        # (soit intactes, soit fusionnées)
        assert "Alpha" in result
        assert "Beta" in result
        assert "Gamma" in result or ";" in result  # Gamma peut être dans la fusion
        assert "Delta" in result
        assert "Epsilon" in result
    
    def test_empty_lines_cleaned(self):
        """Lignes vides doivent être nettoyées"""
        text = "Ligne 1\n\n\nLigne 2\n   \nLigne 3"
        result = apply_max_lines(text, 5)
        result_lines = result.split('\n')
        
        # Ne doit contenir que les lignes non vides
        assert all(line.strip() for line in result_lines)
    
    def test_order_preserved(self):
        """L'ordre original doit être conservé"""
        text = "Premier\nDeuxieme\nTroisieme\nQuatrieme\nCinquieme"
        result = apply_max_lines(text, 3)
        
        # Vérifier que l'ordre est respecté
        assert result.index("Premier") < result.index("Deuxieme")
        assert result.index("Deuxieme") < result.index("Troisieme")
    
    def test_max_lines_zero(self):
        """max_lines = 0 doit retourner le texte tel quel"""
        text = "Ligne 1\nLigne 2"
        result = apply_max_lines(text, 0)
        assert result == text
    
    def test_empty_text(self):
        """Texte vide doit retourner texte vide"""
        result = apply_max_lines("", 4)
        assert result == ""
    
    def test_long_merged_line_truncated(self):
        """Ligne fusionnée trop longue doit être tronquée"""
        # Créer des lignes très longues
        lines = [f"Ligne tres longue numero {i} avec beaucoup de contenu inutile pour tester la troncature" for i in range(1, 21)]
        text = '\n'.join(lines)
        
        result = apply_max_lines(text, 3)
        result_lines = result.split('\n')
        
        # Doit avoir max_lines
        assert len(result_lines) == 3
        
        # La dernière ligne ne doit pas être excessivement longue
        assert len(result_lines[2]) <= 210  # 200 + "..."


class TestIntegrationMicroFixV3:
    """Tests d'intégration pour le micro-fix v3"""
    
    def test_all_sections_tests_mapped(self):
        """Tous les patterns tests doivent être mappés"""
        tests_patterns = [
            "EVALUATIONS",
            "TESTS METIERS",
            "FRANCAIS - NIVEAU 2",
            "WORD - POSITIONNEMENT DE NIVEAU",
            "OUTLOOK 2010",
        ]
        
        for pattern in tests_patterns:
            canonical = match_title_to_canonical(pattern)
            assert canonical == "tests", f"{pattern} n'est pas mappé vers 'tests'"
    
    def test_containers_not_in_seed_map(self):
        """Les conteneurs ne doivent PAS être dans SEED_SECTION_TITLE_MAP"""
        for container in CONTAINER_HEADINGS:
            assert container not in SEED_SECTION_TITLE_MAP, \
                f"Conteneur {container} ne doit pas être dans SEED_SECTION_TITLE_MAP"
    
    def test_resultats_discussion_variants(self):
        """Toutes les variantes RESULTATS doivent mapper vers pistes_metiers"""
        variants = [
            "RESULTATS DE LA DISCUSSION AVEC L'ASSURE",
            "RESULTATS DE LA DISCUSSION AVEC L ASSURE",
            "RESULTATS DE LA DISCUSSION",
            "RÉSULTATS DE LA DISCUSSION AVEC L'ASSURÉ",
        ]
        
        for variant in variants:
            canonical = match_title_to_canonical(variant)
            assert canonical == "pistes_metiers", \
                f"{variant} n'est pas mappé vers 'pistes_metiers'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
