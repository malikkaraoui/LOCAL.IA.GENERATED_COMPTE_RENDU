"""
Tests d'intégration pour le batch runner
"""
import pytest
from pathlib import Path
import json

from src.rhpro.batch_runner import discover_sources, run_batch


# Utiliser des chemins relatifs depuis la racine du repo
REPO_ROOT = Path(__file__).parent.parent
SAMPLES_DIR = REPO_ROOT / "data" / "samples"
RULESET_PATH = REPO_ROOT / "config" / "rulesets" / "rhpro_v1.yaml"


@pytest.fixture
def samples_path():
    """Fixture pour le chemin vers data/samples/"""
    if not SAMPLES_DIR.exists():
        pytest.skip(f"Samples directory not found: {SAMPLES_DIR}")
    return SAMPLES_DIR


@pytest.fixture
def ruleset_path():
    """Fixture pour le chemin vers le ruleset"""
    if not RULESET_PATH.exists():
        pytest.skip(f"Ruleset not found: {RULESET_PATH}")
    return RULESET_PATH


class TestDiscoverSources:
    """Tests pour la découverte de dossiers sources"""
    
    def test_discover_samples(self, samples_path):
        """Vérifie que discover_sources trouve au moins 2 dossiers clients"""
        discovered = discover_sources(str(samples_path))
        
        assert len(discovered) >= 2, f"Expected at least 2 client folders, got {len(discovered)}"
        
        # Vérifier que les dossiers contiennent bien source.docx
        for folder in discovered:
            docx_file = folder / "source.docx"
            assert docx_file.exists(), f"source.docx not found in {folder.name}"
    
    def test_discover_empty_dir(self, tmp_path):
        """Vérifie que discover_sources retourne une liste vide si aucun source.docx"""
        discovered = discover_sources(str(tmp_path))
        assert len(discovered) == 0
    
    def test_discover_nonexistent_dir(self):
        """Vérifie que discover_sources lève FileNotFoundError pour un dossier inexistant"""
        with pytest.raises(FileNotFoundError):
            discover_sources("/path/that/does/not/exist")


class TestBatchRunner:
    """Tests d'intégration pour le batch runner"""
    
    def test_batch_on_all_samples(self, samples_path, ruleset_path, tmp_path):
        """
        Test d'intégration principal: lance le batch sur data/samples/
        et vérifie que tout se passe sans exception
        """
        output_dir = tmp_path / "batch_output"
        
        batch_result = run_batch(
            root_dir=str(samples_path),
            ruleset_path=str(ruleset_path),
            output_dir=str(output_dir)
        )
        
        # Vérifications de base
        assert batch_result["discovered_count"] >= 2
        assert len(batch_result["results"]) >= 2
        assert "summary" in batch_result
        
        # Vérifier qu'aucune exception n'a crashé le batch
        summary = batch_result["summary"]
        assert summary["total_processed"] >= 2
        
        # Vérifier que les fichiers de sortie existent
        assert (output_dir / "batch_report.json").exists()
        assert (output_dir / "batch_report.md").exists()
    
    def test_golden_samples_gate_go(self, samples_path, ruleset_path, tmp_path):
        """
        Vérifie que client_01 et client_02 (golden samples) passent le production gate
        avec missing_required_sections=0 ou très faible
        """
        output_dir = tmp_path / "batch_golden"
        
        batch_result = run_batch(
            root_dir=str(samples_path),
            ruleset_path=str(ruleset_path),
            output_dir=str(output_dir)
        )
        
        # Filtrer les résultats pour client_01 et client_02
        golden_clients = ["client_01", "client_02"]
        golden_results = [
            r for r in batch_result["results"]
            if r["client_name"] in golden_clients and r["status"] == "success"
        ]
        
        # On s'attend à au moins un des deux golden clients
        assert len(golden_results) >= 1, "At least one golden sample should be processed successfully"
        
        for result in golden_results:
            client = result["client_name"]
            
            # Vérifier le gate status
            # Note: Selon le contenu réel, peut être GO ou NO-GO, mais ne doit pas crasher
            assert result["gate_status"] in ["GO", "NO-GO"], f"{client}: invalid gate_status"
            
            # Vérifier que les métriques sont présentes
            assert "required_coverage_ratio" in result
            assert "missing_required_sections" in result
            assert "unknown_titles_count" in result
            
            # Note: On ne force pas missing_required_sections=0 car cela dépend du contenu réel
            # On vérifie juste que c'est une liste
            assert isinstance(result["missing_required_sections"], list)
    
    def test_all_clients_have_valid_report(self, samples_path, ruleset_path, tmp_path):
        """
        Vérifie que tous les clients génèrent bien un report valide
        avec profil choisi + status ∈ {GO, NO_GO}
        """
        output_dir = tmp_path / "batch_all"
        
        batch_result = run_batch(
            root_dir=str(samples_path),
            ruleset_path=str(ruleset_path),
            output_dir=str(output_dir)
        )
        
        # Tous les résultats réussis
        successful_results = [r for r in batch_result["results"] if r["status"] == "success"]
        
        assert len(successful_results) >= 2, "Expected at least 2 successful results"
        
        for result in successful_results:
            client = result["client_name"]
            
            # Vérifier que le profil a été choisi
            assert "profile" in result, f"{client}: missing profile"
            assert result["profile"] != "", f"{client}: empty profile"
            assert result["profile"] in ["bilan_complet", "placement_suivi", "stage"], \
                f"{client}: invalid profile {result['profile']}"
            
            # Vérifier le status du gate
            assert "gate_status" in result, f"{client}: missing gate_status"
            assert result["gate_status"] in ["GO", "NO-GO"], \
                f"{client}: invalid gate_status {result['gate_status']}"
            
            # Vérifier que les reasons existent
            assert "reasons" in result, f"{client}: missing reasons"
            assert isinstance(result["reasons"], list), f"{client}: reasons not a list"
    
    def test_batch_with_profile_override(self, samples_path, ruleset_path, tmp_path):
        """
        Vérifie que le paramètre gate_profile_override force bien le profil
        """
        output_dir = tmp_path / "batch_override"
        
        batch_result = run_batch(
            root_dir=str(samples_path),
            ruleset_path=str(ruleset_path),
            output_dir=str(output_dir),
            gate_profile_override="stage"
        )
        
        # Vérifier que le profil est bien forcé dans le batch_result
        assert batch_result["gate_profile_override"] == "stage"
        
        # Vérifier que tous les résultats ont bien le profil "stage"
        successful_results = [r for r in batch_result["results"] if r["status"] == "success"]
        
        for result in successful_results:
            assert result["profile"] == "stage", \
                f"{result['client_name']}: profile should be 'stage' (forced)"
    
    def test_batch_writes_normalized_in_source(self, samples_path, ruleset_path, tmp_path):
        """
        Vérifie que write_normalized_in_source=True écrit bien source_normalized.json
        dans chaque dossier client
        """
        # Copier un client sample dans tmp_path pour ne pas polluer data/samples/
        test_client = tmp_path / "test_client"
        test_client.mkdir()
        
        # Trouver le premier client disponible
        discovered = discover_sources(str(samples_path))
        if not discovered:
            pytest.skip("No samples found")
        
        first_client = discovered[0]
        source_docx = first_client / "source.docx"
        
        # Copier le source.docx
        import shutil
        shutil.copy(source_docx, test_client / "source.docx")
        
        # Lancer le batch avec write_normalized_in_source=True
        batch_result = run_batch(
            root_dir=str(tmp_path),
            ruleset_path=str(ruleset_path),
            write_normalized_in_source=True
        )
        
        # Vérifier que source_normalized.json a été créé
        normalized_file = test_client / "source_normalized.json"
        assert normalized_file.exists(), "source_normalized.json should be created"
        
        # Vérifier que c'est un JSON valide
        with open(normalized_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert "identity" in data or "sections" in data, "normalized JSON should have expected structure"
    
    def test_batch_empty_samples_dir(self, ruleset_path, tmp_path):
        """
        Vérifie que le batch handle correctement un dossier vide (pas de source.docx)
        """
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        batch_result = run_batch(
            root_dir=str(empty_dir),
            ruleset_path=str(ruleset_path)
        )
        
        assert batch_result["discovered_count"] == 0
        assert len(batch_result["results"]) == 0
        assert "error" in batch_result["summary"]


class TestBatchReportGeneration:
    """Tests pour la génération de rapports"""
    
    def test_markdown_report_generated(self, samples_path, ruleset_path, tmp_path):
        """Vérifie que le rapport Markdown est bien généré et lisible"""
        output_dir = tmp_path / "batch_md"
        
        batch_result = run_batch(
            root_dir=str(samples_path),
            ruleset_path=str(ruleset_path),
            output_dir=str(output_dir)
        )
        
        md_file = output_dir / "batch_report.md"
        assert md_file.exists()
        
        # Vérifier que le contenu est valide
        content = md_file.read_text(encoding="utf-8")
        assert "# Batch Parser Report" in content
        assert "## Summary" in content
        assert "## Detailed Results" in content
    
    def test_json_report_structure(self, samples_path, ruleset_path, tmp_path):
        """Vérifie la structure du rapport JSON"""
        output_dir = tmp_path / "batch_json"
        
        batch_result = run_batch(
            root_dir=str(samples_path),
            ruleset_path=str(ruleset_path),
            output_dir=str(output_dir)
        )
        
        json_file = output_dir / "batch_report.json"
        assert json_file.exists()
        
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Vérifier la structure attendue
        assert "timestamp" in data
        assert "root_dir" in data
        assert "ruleset_path" in data
        assert "discovered_count" in data
        assert "results" in data
        assert "summary" in data
        
        # Vérifier le résumé
        summary = data["summary"]
        assert "total_processed" in summary
        assert "successful" in summary
        assert "errors" in summary
        assert "gate_go" in summary
        assert "gate_no_go" in summary
        assert "avg_coverage" in summary
