"""Configuration pytest partagée pour tous les tests."""

import pytest
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def sample_payload() -> Dict[str, Any]:
    """Payload d'extraction type pour les tests."""
    return {
        "documents": [
            {
                "path": "test.pdf",
                "text": "John Doe travaille comme développeur Python.\nIl a 5 ans d'expérience.",
                "metadata": {"pages": 1},
            }
        ],
        "chunks": [
            {"text": "John Doe travaille comme développeur Python.", "source": "test.pdf", "chunk_id": 0},
            {"text": "Il a 5 ans d'expérience.", "source": "test.pdf", "chunk_id": 1},
        ],
    }


@pytest.fixture
def temp_client_dir(tmp_path: Path) -> Path:
    """Crée un dossier client temporaire pour les tests."""
    client_dir = tmp_path / "test_client"
    client_dir.mkdir()
    
    # Créer quelques fichiers test
    (client_dir / "cv.txt").write_text("Nom: John Doe\nProfession: Développeur")
    (client_dir / "notes.txt").write_text("Excellent candidat avec 5 ans d'expérience")
    
    return client_dir


@pytest.fixture
def mock_llm_response() -> str:
    """Réponse LLM type pour les tests."""
    return "Développeur Python"
