"""
Test unitaire pour le module Training UI.
"""
import pytest
from pathlib import Path
import json
import tempfile
import shutil


def test_batch_analyzer_import():
    """Test import du module batch_analyzer."""
    try:
        from src.rhpro.batch_analyzer import (
            scan_batch_clients,
            calculate_compatibility_score,
            get_client_analysis_detail,
        )
        assert True
    except ImportError as e:
        pytest.fail(f"Impossible d'importer batch_analyzer : {e}")


def test_rag_generator_import():
    """Test import du module rag_generator."""
    try:
        from src.rhpro.rag_generator import RAGGenerator, get_chunks_preview
        assert True
    except ImportError as e:
        # LlamaIndex peut ne pas être installé
        if "llama_index" in str(e):
            pytest.skip("LlamaIndex non installé")
        else:
            pytest.fail(f"Erreur import rag_generator : {e}")


def test_report_generator_import():
    """Test import du module report_generator."""
    try:
        from src.rhpro.report_generator import (
            RHProReportGenerator,
            generate_report_from_normalized,
        )
        assert True
    except ImportError as e:
        pytest.fail(f"Impossible d'importer report_generator : {e}")


def test_calculate_compatibility_score():
    """Test calcul du score de compatibilité."""
    from src.rhpro.batch_analyzer import calculate_compatibility_score
    
    # Client pipeline-ready
    scan_result_ready = {
        "stats": {
            "gold_found": True,
            "gold_score": 0.8,
            "rag_sources_count": 5,
            "folders_detected": 5,
        },
        "pipeline_ready": True,
    }
    
    score = calculate_compatibility_score(scan_result_ready)
    assert score >= 0.7, f"Score trop faible pour client ready : {score}"
    
    # Client pas ready
    scan_result_not_ready = {
        "stats": {
            "gold_found": False,
            "gold_score": 0.0,
            "rag_sources_count": 0,
            "folders_detected": 1,
        },
        "pipeline_ready": False,
    }
    
    score = calculate_compatibility_score(scan_result_not_ready)
    assert score < 0.3, f"Score trop élevé pour client not ready : {score}"


def test_get_client_analysis_detail():
    """Test génération de l'analyse détaillée."""
    from src.rhpro.batch_analyzer import get_client_analysis_detail
    
    # Mock scan result
    scan_result = {
        "gold": {
            "path": "/path/to/rapport.docx",
            "score": 0.85,
            "strategy": "06_rapport_final",
            "size_bytes": 50000,
        },
        "rag_sources": [
            {
                "path": "/path/to/source1.docx",
                "category": "01_personnel",
                "extension": ".docx",
                "size_bytes": 10000,
            },
            {
                "path": "/path/to/source2.pdf",
                "category": "03_tests",
                "extension": ".pdf",
                "size_bytes": 20000,
            },
        ],
        "folder_structure": {
            "01_personnel": "/path/to/01",
            "06_rapport": "/path/to/06",
        },
        "stats": {
            "gold_found": True,
            "gold_score": 0.85,
            "rag_sources_count": 2,
            "folders_detected": 2,
        },
        "pipeline_ready": True,
    }
    
    analysis = get_client_analysis_detail(scan_result)
    
    # Vérifier les sections
    assert "what_found" in analysis
    assert "what_usable" in analysis
    assert "what_missing" in analysis
    assert "gold_choice" in analysis
    
    # Vérifier GOLD trouvé
    assert analysis["what_found"]["gold"] is not None
    assert analysis["what_found"]["gold"]["score"] == 0.85
    
    # Vérifier sources RAG
    assert len(analysis["what_found"]["rag_sources"]) == 2
    
    # Vérifier exploitabilité
    assert analysis["what_usable"]["gold_usable"] is True


def test_default_template_fields():
    """Test que les champs par défaut sont bien définis."""
    from src.rhpro.report_generator import DEFAULT_TEMPLATE_FIELDS
    
    assert len(DEFAULT_TEMPLATE_FIELDS) > 0
    assert "nom" in DEFAULT_TEMPLATE_FIELDS
    assert "prenom" in DEFAULT_TEMPLATE_FIELDS
    assert "objectifs_professionnels" in DEFAULT_TEMPLATE_FIELDS


def test_report_generator_init():
    """Test initialisation du générateur de rapports."""
    from src.rhpro.report_generator import RHProReportGenerator
    
    generator = RHProReportGenerator(
        template_path=None,
        template_fields=["nom", "prenom"],
    )
    
    assert generator.template_path is None
    assert generator.template_fields == ["nom", "prenom"]
    assert generator.rag_generator is None


def test_chunks_preview_empty_folder():
    """Test aperçu chunks avec dossier vide."""
    try:
        from src.rhpro.rag_generator import get_chunks_preview
    except ImportError:
        pytest.skip("LlamaIndex non installé")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        chunks = get_chunks_preview(tmpdir, max_chunks=10)
        assert chunks == [], "Dossier vide devrait retourner liste vide"


def test_training_page_import():
    """Test import de la page training."""
    try:
        from pages_streamlit import training
        assert hasattr(training, "show_training_page")
        assert hasattr(training, "show_batch_mode")
        assert hasattr(training, "show_detailed_analysis")
        assert hasattr(training, "show_normalize_view")
        assert hasattr(training, "show_generate_view")
    except ImportError as e:
        pytest.fail(f"Impossible d'importer training page : {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
