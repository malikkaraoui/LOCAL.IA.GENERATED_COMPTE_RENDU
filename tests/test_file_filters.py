"""Tests pour le filtrage des fichiers temporaires et système."""

from pathlib import Path
import pytest
from src.utils.file_filters import is_ignored_filename


class TestFileFilters:
    """Tests pour is_ignored_filename()."""
    
    def test_office_temp_files_are_ignored(self):
        """Les fichiers temporaires Office doivent être ignorés."""
        assert is_ignored_filename("~$Contrat de travail.docx") is True
        assert is_ignored_filename("~$rapport.xlsx") is True
        assert is_ignored_filename("~$présentation.pptx") is True
        
    def test_office_lock_files_are_ignored(self):
        """Les fichiers lock Office doivent être ignorés."""
        assert is_ignored_filename(".~lock.docx") is True
        assert is_ignored_filename(".~lock.xlsx") is True
        
    def test_office_tmp_files_are_ignored(self):
        """Les fichiers .tmp Office doivent être ignorés."""
        assert is_ignored_filename("~WRL0001.tmp") is True
        assert is_ignored_filename(".~WRL0001.tmp") is True
        
    def test_system_files_are_ignored(self):
        """Les fichiers système doivent être ignorés."""
        assert is_ignored_filename(".DS_Store") is True
        assert is_ignored_filename("Thumbs.db") is True
        
    def test_normal_files_not_ignored(self):
        """Les fichiers normaux ne doivent pas être ignorés."""
        assert is_ignored_filename("Contrat de travail.docx") is False
        assert is_ignored_filename("rapport.xlsx") is False
        assert is_ignored_filename("présentation.pptx") is False
        assert is_ignored_filename("document.pdf") is False
        assert is_ignored_filename("notes.txt") is False
        
    def test_normal_tmp_files_not_ignored(self):
        """Les fichiers .tmp normaux (sans préfixe Office) ne sont pas ignorés."""
        assert is_ignored_filename("data.tmp") is False
        assert is_ignored_filename("backup.tmp") is False
        
    def test_works_with_path_objects(self):
        """is_ignored_filename doit accepter des objets Path."""
        assert is_ignored_filename(Path("~$test.docx")) is True
        assert is_ignored_filename(Path("test.docx")) is False
        
    def test_works_with_full_paths(self):
        """is_ignored_filename doit fonctionner avec des chemins complets."""
        assert is_ignored_filename("/path/to/~$document.docx") is True
        assert is_ignored_filename("/path/to/document.docx") is False
        assert is_ignored_filename(Path("/path/to/.DS_Store")) is True
