"""Tests pour le module core/extract.py."""

import pytest
from pathlib import Path
from core.extract import walk_files


class TestWalkFiles:
    """Tests pour la fonction walk_files."""

    def test_finds_all_files(self, temp_client_dir: Path):
        """Trouve tous les fichiers dans un dossier."""
        files = walk_files(temp_client_dir)
        assert len(files) == 2
        assert any(f.name == "cv.txt" for f in files)
        assert any(f.name == "notes.txt" for f in files)

    def test_excludes_hidden_files(self, tmp_path: Path):
        """Exclut les fichiers cachés."""
        (tmp_path / ".hidden").write_text("secret")
        (tmp_path / "visible.txt").write_text("public")
        
        files = walk_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "visible.txt"

    def test_excludes_git_directory(self, tmp_path: Path):
        """Exclut le répertoire .git."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("git config")
        (tmp_path / "file.txt").write_text("normal file")
        
        files = walk_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "file.txt"
