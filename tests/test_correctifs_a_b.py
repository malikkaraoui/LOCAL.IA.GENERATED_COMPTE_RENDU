"""
Tests unitaires pour les correctifs A et B.

Correctif A: Indexation .msg dans RAG avec option index_msg
Correctif B: Suppression NOM/PRENOM/AVS des unknown_titles
"""

import pytest
from pathlib import Path
import tempfile
import os

from src.rhpro.client_scanner import scan_client_folder
from src.rhpro.dataset_training import is_noise_heading


# ==============================================================================
# CORRECTIF B: Tests is_noise_heading()
# ==============================================================================

class TestCorrectifB:
    """Tests pour le filtrage des titres nominatifs."""
    
    def test_is_noise_heading_nom_prenom_pattern(self):
        """Doit détecter 'NOM xxx PRENOM yyy' comme bruit."""
        assert is_noise_heading("NOM AYNE PRENOM MICKAEL") is True
        assert is_noise_heading("PRENOM MICKAEL NOM AYNE") is True
        assert is_noise_heading("NOM DUPONT PRENOM JEAN") is True
    
    def test_is_noise_heading_avs(self):
        """Doit détecter les numéros AVS comme bruit."""
        assert is_noise_heading("756.1234.5678.90") is True
        assert is_noise_heading("7561234567890") is True
        assert is_noise_heading("AVS 756 1234 5678 90") is True
    
    def test_is_noise_heading_dates(self):
        """Doit détecter les dates comme bruit."""
        assert is_noise_heading("15/03/1985") is True
        assert is_noise_heading("15.03.1985") is True
        assert is_noise_heading("15 03 1985") is True
    
    def test_is_noise_heading_form_labels(self):
        """Doit détecter les libellés de formulaire comme bruit."""
        assert is_noise_heading("NOM") is True
        assert is_noise_heading("PRENOM") is True
        assert is_noise_heading("DATE DE NAISSANCE") is True
        assert is_noise_heading("NUMERO AVS") is True
    
    def test_is_noise_heading_too_many_digits(self):
        """Doit détecter les textes avec trop de chiffres (>= 8) comme bruit."""
        assert is_noise_heading("12345678") is True
        assert is_noise_heading("Ref 12345678") is True
    
    def test_is_noise_heading_valid_titles(self):
        """Ne doit PAS détecter les titres valides comme bruit."""
        assert is_noise_heading("EXPERIENCE PROFESSIONNELLE") is False
        assert is_noise_heading("FORMATIONS") is False
        assert is_noise_heading("COMPETENCES") is False
        assert is_noise_heading("PARCOURS") is False
        assert is_noise_heading("PROJET PROFESSIONNEL") is False


# ==============================================================================
# CORRECTIF A: Tests index_msg
# ==============================================================================

class TestCorrectifA:
    """Tests pour l'indexation des fichiers .msg avec option index_msg."""
    
    @pytest.fixture
    def temp_client_folder(self):
        """Crée un dossier client temporaire avec différents types de fichiers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            client_dir = Path(tmpdir) / "TEST Client"
            client_dir.mkdir()
            
            # Créer structure dossiers
            (client_dir / "01 Dossier personnel").mkdir()
            (client_dir / "06 Rapport final").mkdir()
            
            # Créer fichiers test
            (client_dir / "01 Dossier personnel" / "CV.pdf").write_text("CV content")
            (client_dir / "01 Dossier personnel" / "Email.msg").write_text("Email content")
            (client_dir / "06 Rapport final" / "Bilan.docx").write_text("Bilan content")
            (client_dir / "lettre.txt").write_text("Lettre content")
            
            yield client_dir
    
    def test_scan_with_index_msg_true(self, temp_client_folder):
        """Avec index_msg=True, les .msg doivent être dans rag_sources."""
        result = scan_client_folder(str(temp_client_folder), index_msg=True)
        
        # Vérifier que .msg est inclus
        msg_files = [s for s in result["rag_sources"] if s["extension"] == ".msg"]
        assert len(msg_files) == 1, "Devrait trouver 1 fichier .msg"
        assert "Email.msg" in msg_files[0]["path"]
        
        # Vérifier pas de warning EXT_NOT_INDEXED
        ext_warnings = [w for w in result["warnings"] if "EXT_NOT_INDEXED" in w]
        assert len(ext_warnings) == 0, "Pas de warning EXT_NOT_INDEXED avec index_msg=True"
        
        # Vérifier msg_files_count = 0 (car indexés)
        assert result["stats"]["msg_files_count"] == 0
    
    def test_scan_with_index_msg_false(self, temp_client_folder):
        """Avec index_msg=False, les .msg ne doivent PAS être dans rag_sources."""
        result = scan_client_folder(str(temp_client_folder), index_msg=False)
        
        # Vérifier que .msg n'est PAS inclus
        msg_files = [s for s in result["rag_sources"] if s["extension"] == ".msg"]
        assert len(msg_files) == 0, "Ne devrait PAS trouver de fichier .msg dans rag_sources"
        
        # Vérifier warning EXT_NOT_INDEXED présent
        ext_warnings = [w for w in result["warnings"] if "EXT_NOT_INDEXED" in w]
        assert len(ext_warnings) == 1, "Devrait avoir 1 warning EXT_NOT_INDEXED"
        assert "1 fichier(s) .msg" in ext_warnings[0]
        
        # Vérifier msg_files_count = 1 (comptés mais pas indexés)
        assert result["stats"]["msg_files_count"] == 1
    
    def test_scan_default_index_msg(self, temp_client_folder):
        """Par défaut (sans paramètre), index_msg devrait être False."""
        result = scan_client_folder(str(temp_client_folder))
        
        # Vérifier comportement par défaut = index_msg=False
        msg_files = [s for s in result["rag_sources"] if s["extension"] == ".msg"]
        assert len(msg_files) == 0, "Par défaut, .msg ne doit PAS être indexé"
        
        # Vérifier warning présent
        ext_warnings = [w for w in result["warnings"] if "EXT_NOT_INDEXED" in w]
        assert len(ext_warnings) == 1
    
    def test_scan_no_msg_files(self, temp_client_folder):
        """Sans fichiers .msg, pas de warning EXT_NOT_INDEXED."""
        # Supprimer le fichier .msg
        msg_file = temp_client_folder / "01 Dossier personnel" / "Email.msg"
        msg_file.unlink()
        
        result = scan_client_folder(str(temp_client_folder), index_msg=False)
        
        # Pas de warning EXT_NOT_INDEXED
        ext_warnings = [w for w in result["warnings"] if "EXT_NOT_INDEXED" in w]
        assert len(ext_warnings) == 0, "Pas de warning si aucun .msg"
        
        # msg_files_count = 0
        assert result["stats"]["msg_files_count"] == 0
    
    def test_extensions_count_with_index_msg(self, temp_client_folder):
        """Vérifier que les extensions sont comptées correctement."""
        result_with_msg = scan_client_folder(str(temp_client_folder), index_msg=True)
        result_without_msg = scan_client_folder(str(temp_client_folder), index_msg=False)
        
        # Avec index_msg=True : .msg doit apparaître dans extensions
        assert ".msg" in result_with_msg["stats"]["extensions"]
        assert result_with_msg["stats"]["extensions"][".msg"] == 1
        
        # Avec index_msg=False : .msg ne doit PAS apparaître dans extensions
        assert ".msg" not in result_without_msg["stats"]["extensions"]
        
        # Autres extensions doivent être identiques
        for ext in [".pdf", ".txt"]:  # .docx est le gold
            if ext in result_with_msg["stats"]["extensions"]:
                assert result_with_msg["stats"]["extensions"][ext] == result_without_msg["stats"]["extensions"].get(ext, 0)


# ==============================================================================
# Tests d'intégration
# ==============================================================================

class TestIntegration:
    """Tests d'intégration pour vérifier que les correctifs ne cassent rien."""
    
    @pytest.fixture
    def complex_client_folder(self):
        """Crée un dossier client complexe pour tests d'intégration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            client_dir = Path(tmpdir) / "DUPONT Jean"
            client_dir.mkdir()
            
            # Structure complète
            for folder_num in ["01", "03", "04", "05", "06"]:
                folder_name = {
                    "01": "01 Dossier personnel",
                    "03": "03 Tests et bilans",
                    "04": "04 Stages",
                    "05": "05 Mesures AI",
                    "06": "06 Rapport final"
                }[folder_num]
                (client_dir / folder_name).mkdir()
            
            # Fichiers variés
            (client_dir / "01 Dossier personnel" / "CV_2023.pdf").write_text("CV")
            (client_dir / "01 Dossier personnel" / "Candidature.msg").write_text("Email")
            (client_dir / "03 Tests et bilans" / "Test_psycho.pdf").write_text("Test")
            (client_dir / "04 Stages" / "Rapport_stage.docx").write_text("Stage")
            (client_dir / "05 Mesures AI" / "Suivi.txt").write_text("Suivi")
            (client_dir / "06 Rapport final" / "Bilan_final.docx").write_text("Bilan final rapport")
            (client_dir / "notes.txt").write_text("Notes")
            
            yield client_dir
    
    def test_integration_with_index_msg_true(self, complex_client_folder):
        """Test complet avec index_msg=True."""
        result = scan_client_folder(str(complex_client_folder), index_msg=True)
        
        assert result["pipeline_ready"] is True
        assert result["gold"] is not None
        assert "Bilan_final.docx" in result["gold"]["path"]
        
        # Compter sources (4 PDF/TXT/DOCX + 1 MSG + 1 notes.txt = 6, - 1 gold = 5)
        assert len(result["rag_sources"]) >= 5
        
        # Vérifier .msg inclus
        msg_count = sum(1 for s in result["rag_sources"] if s["extension"] == ".msg")
        assert msg_count == 1
    
    def test_integration_with_index_msg_false(self, complex_client_folder):
        """Test complet avec index_msg=False."""
        result = scan_client_folder(str(complex_client_folder), index_msg=False)
        
        assert result["pipeline_ready"] is True
        
        # Compter sources (sans .msg)
        msg_count = sum(1 for s in result["rag_sources"] if s["extension"] == ".msg")
        assert msg_count == 0
        
        # Vérifier warning
        ext_warnings = [w for w in result["warnings"] if "EXT_NOT_INDEXED" in w]
        assert len(ext_warnings) == 1
        assert result["stats"]["msg_files_count"] == 1
    
    def test_no_regression_on_existing_extensions(self, complex_client_folder):
        """Vérifier qu'il n'y a pas de régression sur PDF/DOCX/TXT."""
        result = scan_client_folder(str(complex_client_folder), index_msg=False)
        
        # Vérifier que tous les types attendus sont présents
        assert ".pdf" in result["stats"]["extensions"]
        assert ".txt" in result["stats"]["extensions"]
        
        # Compter total (devrait avoir au moins 4 sources hors gold)
        assert len(result["rag_sources"]) >= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
