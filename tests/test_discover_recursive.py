"""
Tests pour discover_client_documents_recursive() - Scan récursif avec contrôle profondeur
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from src.rhpro.client_finder import discover_client_documents_recursive


@pytest.fixture
def temp_client_folder():
    """Crée une structure de dossier client temporaire pour tests"""
    temp_dir = tempfile.mkdtemp()
    client_folder = Path(temp_dir) / "TEST_Client"
    client_folder.mkdir()
    
    # Fichiers racine
    (client_folder / "rapport.docx").touch()
    (client_folder / "cv.pdf").touch()
    (client_folder / "notes.txt").touch()
    (client_folder / "audio1.mp3").touch()
    
    # Fichier Office temporaire (doit être ignoré)
    (client_folder / "~$rapport.docx").touch()
    
    # Fichier .DS_Store (doit être ignoré)
    (client_folder / ".DS_Store").touch()
    
    # Sous-dossier niveau 1 : "01 Dossier personnel"
    subdir1 = client_folder / "01 Dossier personnel"
    subdir1.mkdir()
    (subdir1 / "identite.pdf").touch()
    (subdir1 / "diplomes.pdf").touch()
    
    # Sous-dossier niveau 1 : "03 Tests et bilans"
    subdir2 = client_folder / "03 Tests et bilans"
    subdir2.mkdir()
    (subdir2 / "test_francais.docx").touch()
    (subdir2 / "bilan.pdf").touch()
    
    # Sous-dossier niveau 2 (dans "03 Tests")
    subdir2_1 = subdir2 / "Archives"
    subdir2_1.mkdir()
    (subdir2_1 / "ancien_test.pdf").touch()
    
    # Dossier à ignorer
    ignored = client_folder / "node_modules"
    ignored.mkdir()
    (ignored / "package.json").touch()
    
    yield client_folder
    
    # Cleanup
    shutil.rmtree(temp_dir)


class TestDiscoverClientDocumentsRecursive:
    """Tests pour scan récursif avec profondeur contrôlée"""
    
    def test_max_depth_0_only_root(self, temp_client_folder):
        """max_depth=0 : ne retourne que les fichiers racine"""
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=0,
            include_subfolders=True
        )
        
        # Vérifier que seuls les fichiers racine sont trouvés
        assert len(result['files']['docx']) == 1  # rapport.docx
        assert len(result['files']['pdf']) == 1   # cv.pdf
        assert len(result['files']['txt']) == 1   # notes.txt
        assert len(result['files']['audio']) == 1 # audio1.mp3
        assert result['total_files'] == 4
        
        # Vérifier que ~$rapport.docx et .DS_Store sont ignorés
        all_files = [f.name for files in result['files'].values() for f in files]
        assert '~$rapport.docx' not in all_files
        assert '.DS_Store' not in all_files
    
    def test_max_depth_1_includes_direct_subfolders(self, temp_client_folder):
        """max_depth=1 : inclut les fichiers des sous-dossiers directs"""
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=1,
            include_subfolders=True
        )
        
        # Racine : 4 fichiers
        # "01 Dossier personnel" : 2 pdf
        # "03 Tests et bilans" : 1 docx + 1 pdf
        # Total : 4 + 2 + 2 = 8 (pas "Archives/ancien_test.pdf" car profondeur 2)
        
        assert result['total_files'] == 8
        assert len(result['files']['docx']) == 2  # rapport.docx + test_francais.docx
        assert len(result['files']['pdf']) == 4   # cv.pdf + identite.pdf + diplomes.pdf + bilan.pdf
        
        # Vérifier que "Archives/ancien_test.pdf" n'est PAS inclus (profondeur 2)
        all_paths = [str(f) for files in result['files'].values() for f in files]
        assert not any('Archives' in p for p in all_paths)
    
    def test_max_depth_2_includes_nested_subfolders(self, temp_client_folder):
        """max_depth=2 : inclut les sous-dossiers de niveau 2"""
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=2,
            include_subfolders=True
        )
        
        # Doit inclure "Archives/ancien_test.pdf"
        assert result['total_files'] == 9
        
        # Vérifier que Archives/ancien_test.pdf est inclus
        all_paths = [str(f) for files in result['files'].values() for f in files]
        assert any('Archives' in p and 'ancien_test.pdf' in p for p in all_paths)
    
    def test_include_subfolders_false_forces_depth_0(self, temp_client_folder):
        """include_subfolders=False : force max_depth=0 même si depth passé"""
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=5,  # Volontairement élevé
            include_subfolders=False  # Force depth=0
        )
        
        # Doit retourner uniquement fichiers racine
        assert result['total_files'] == 4
        assert len(result['files']['docx']) == 1
    
    def test_ignore_office_temp_files(self, temp_client_folder):
        """Fichiers temporaires Office (~$*.docx) sont ignorés"""
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=0
        )
        
        all_files = [f.name for files in result['files'].values() for f in files]
        assert '~$rapport.docx' not in all_files
    
    def test_ignore_ds_store(self, temp_client_folder):
        """.DS_Store est ignoré"""
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=0
        )
        
        all_files = [f.name for files in result['files'].values() for f in files]
        assert '.DS_Store' not in all_files
    
    def test_ignore_dirs_node_modules(self, temp_client_folder):
        """Dossiers ignorés (node_modules, .git, etc.) ne sont pas scannés"""
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=2
        )
        
        # Vérifier que node_modules/package.json n'est PAS inclus
        all_paths = [str(f) for files in result['files'].values() for f in files]
        assert not any('node_modules' in p for p in all_paths)
    
    def test_max_files_limit(self, temp_client_folder):
        """max_files limite le nombre de fichiers scannés"""
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=2,
            max_files=5  # Limite volontairement basse
        )
        
        assert result['total_files'] <= 5
        assert result['truncated'] is True
    
    def test_stats_by_subfolder(self, temp_client_folder):
        """stats_by_subfolder contient stats par sous-dossier"""
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=1
        )
        
        stats = result['stats_by_subfolder']
        
        # Doit contenir "Racine", "01 Dossier personnel", "03 Tests et bilans"
        assert 'Racine' in stats
        assert '01 Dossier personnel' in stats
        assert '03 Tests et bilans' in stats
        
        # Vérifier nombre fichiers par sous-dossier
        assert stats['Racine']['docx'] == 1
        assert stats['Racine']['pdf'] == 1
        assert stats['01 Dossier personnel']['pdf'] == 2
        assert stats['03 Tests et bilans']['docx'] == 1
        assert stats['03 Tests et bilans']['pdf'] == 1
    
    def test_stats_by_type(self, temp_client_folder):
        """stats_by_type contient nombre total par type"""
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=1
        )
        
        stats = result['stats_by_type']
        
        assert stats['docx'] == 2
        assert stats['pdf'] == 4
        assert stats['txt'] == 1
        assert stats['audio'] == 1
    
    def test_allowed_exts_custom(self, temp_client_folder):
        """allowed_exts personnalisé filtre les types"""
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=0,
            allowed_exts={'.docx'}  # Seulement DOCX
        )
        
        assert len(result['files']['docx']) == 1
        assert len(result['files']['pdf']) == 0
        assert len(result['files']['txt']) == 0
        assert result['total_files'] == 1
    
    def test_msg_files_detected(self, temp_client_folder):
        """Fichiers .msg sont détectés et classés séparément"""
        # Ajouter un fichier .msg
        (temp_client_folder / "email.msg").touch()
        
        result = discover_client_documents_recursive(
            temp_client_folder,
            max_depth=0
        )
        
        assert len(result['files']['msg']) == 1
        assert result['files']['msg'][0].name == 'email.msg'
    
    def test_nonexistent_folder_raises_error(self):
        """Dossier inexistant lève FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            discover_client_documents_recursive(Path("/nonexistent/folder"))


class TestDiscoverIntegration:
    """Tests d'intégration sur structure RH-Pro réaliste"""
    
    def test_typical_rhpro_structure(self):
        """Structure typique RH-Pro avec sous-dossiers numérotés"""
        temp_dir = tempfile.mkdtemp()
        client_folder = Path(temp_dir) / "ARIFI Elodie"
        client_folder.mkdir()
        
        # Structure RH-Pro typique
        (client_folder / "Compte_Rendu_Final.docx").touch()
        
        subdir1 = client_folder / "01 Dossier personnel"
        subdir1.mkdir()
        (subdir1 / "CV.pdf").touch()
        (subdir1 / "Diplomes.pdf").touch()
        
        subdir2 = client_folder / "03 Tests et bilans"
        subdir2.mkdir()
        (subdir2 / "Test_Francais.docx").touch()
        (subdir2 / "Bilan_Competences.pdf").touch()
        
        subdir3 = client_folder / "06 Rapport final"
        subdir3.mkdir()
        (subdir3 / "Rapport_Orientation.docx").touch()
        
        try:
            # Scan avec max_depth=1 (cas typique)
            result = discover_client_documents_recursive(
                client_folder,
                max_depth=1,
                include_subfolders=True
            )
            
            # Doit trouver tous les fichiers (racine + sous-dossiers niveau 1)
            assert result['total_files'] == 6
            assert len(result['files']['docx']) == 3
            assert len(result['files']['pdf']) == 3
            
            # Vérifier stats par sous-dossier
            stats = result['stats_by_subfolder']
            assert '01 Dossier personnel' in stats
            assert '03 Tests et bilans' in stats
            assert '06 Rapport final' in stats
            
        finally:
            shutil.rmtree(temp_dir)
