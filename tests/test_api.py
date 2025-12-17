"""Tests pour les routes de l'API backend."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from backend.main import app


@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    with patch('backend.api.routes.reports.redis_conn') as mock:
        yield mock


@pytest.fixture
def mock_queue():
    """Mock RQ Queue."""
    with patch('backend.api.routes.reports.queue') as mock:
        mock_job = Mock()
        mock_job.id = "test-job-123"
        mock_job.get_status.return_value = "queued"
        mock_job.is_finished = False
        mock_job.is_failed = False
        mock_job.result = None
        mock.enqueue.return_value = mock_job
        yield mock


class TestHealthRoutes:
    """Tests pour les routes /health."""
    
    def test_health_check(self, client):
        """Test GET /api/health."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    @patch('backend.api.routes.health.requests.get')
    def test_ollama_health_success(self, mock_get, client):
        """Test GET /api/health/ollama - succès."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "mistral:latest"}]}
        mock_get.return_value = mock_response
        
        response = client.get("/api/health/ollama")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "models" in data
    
    @patch('backend.api.routes.health.requests.get')
    def test_ollama_health_failure(self, mock_get, client):
        """Test GET /api/health/ollama - échec."""
        mock_get.side_effect = Exception("Connection refused")
        
        response = client.get("/api/health/ollama")
        assert response.status_code == 503
        data = response.json()
        assert "error" in data


class TestReportsRoutes:
    """Tests pour les routes /reports."""
    
    def test_create_report_success(self, client, mock_queue, tmp_path):
        """Test POST /api/reports - succès."""
        # Créer un dossier client temporaire
        client_dir = tmp_path / "CLIENTS" / "TEST_CLIENT"
        client_dir.mkdir(parents=True)
        
        with patch('backend.api.routes.reports.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path / "CLIENTS"
            mock_settings.OLLAMA_HOST = "http://localhost:11434"
            mock_settings.OLLAMA_MODEL = "mistral:latest"
            mock_settings.OLLAMA_TIMEOUT = 300
            
            response = client.post("/api/reports", json={
                "client_name": "TEST_CLIENT",
                "name": "John",
                "surname": "Doe"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "pending"
            assert "created_at" in data
    
    def test_create_report_client_not_found(self, client, tmp_path):
        """Test POST /api/reports - client inexistant."""
        with patch('backend.api.routes.reports.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path / "CLIENTS"
            
            response = client.post("/api/reports", json={
                "client_name": "NONEXISTENT_CLIENT"
            })
            
            assert response.status_code == 404
            assert "introuvable" in response.json()["detail"]
    
    def test_create_report_missing_fields(self, client):
        """Test POST /api/reports - champs manquants."""
        response = client.post("/api/reports", json={})
        assert response.status_code == 422  # Validation error
    
    @patch('backend.api.routes.reports.Job')
    def test_get_report_status_success(self, mock_job_class, client, mock_redis):
        """Test GET /api/reports/{job_id} - succès."""
        mock_job = Mock()
        mock_job.get_status.return_value = "finished"
        mock_job.is_finished = True
        mock_job.is_failed = False
        mock_job.result = {"output_path": "/path/to/report.docx"}
        mock_job.meta = {}
        mock_job_class.fetch.return_value = mock_job
        
        response = client.get("/api/reports/test-job-123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "result" in data
    
    @patch('backend.api.routes.reports.Job')
    def test_get_report_status_not_found(self, mock_job_class, client):
        """Test GET /api/reports/{job_id} - job inexistant."""
        mock_job_class.fetch.side_effect = Exception("Job not found")
        
        response = client.get("/api/reports/nonexistent-job")
        assert response.status_code == 404
    
    @patch('backend.api.routes.reports.Job')
    def test_get_report_status_failed(self, mock_job_class, client, mock_redis):
        """Test GET /api/reports/{job_id} - job échoué."""
        mock_job = Mock()
        mock_job.get_status.return_value = "failed"
        mock_job.is_finished = False
        mock_job.is_failed = True
        mock_job.exc_info = "Error: something went wrong"
        mock_job.meta = {}
        mock_job_class.fetch.return_value = mock_job
        
        response = client.get("/api/reports/failed-job")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "error" in data
    
    @patch('backend.api.routes.reports.Job')
    def test_delete_report(self, mock_job_class, client):
        """Test DELETE /api/reports/{job_id}."""
        mock_job = Mock()
        mock_job_class.fetch.return_value = mock_job
        
        response = client.delete("/api/reports/test-job-123")
        assert response.status_code == 200
        assert "supprimé" in response.json()["message"]
        mock_job.delete.assert_called_once()


class TestReportWorker:
    """Tests pour le worker de génération de rapports."""
    
    @patch('backend.workers.orchestrator.ReportOrchestrator')
    def test_process_report_job_success(self, mock_orchestrator_class, tmp_path):
        """Test process_report_job - succès."""
        from backend.workers.report_worker import process_report_job
        
        # Mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.run.return_value = {
            "status": "success",
            "output_path": str(tmp_path / "rapport.docx"),
            "client_name": "TEST"
        }
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Mock settings
        with patch('backend.workers.report_worker.settings') as mock_settings:
            client_dir = tmp_path / "TEST"
            client_dir.mkdir()
            mock_settings.CLIENTS_DIR = tmp_path
            mock_settings.TEMPLATE_PATH = tmp_path / "template.docx"
            
            result = process_report_job(
                client_name="TEST",
                name="John",
                surname="Doe"
            )
            
            assert result["status"] == "success"
            assert "output_path" in result
    
    def test_process_report_job_client_not_found(self, tmp_path):
        """Test process_report_job - client inexistant."""
        from backend.workers.report_worker import process_report_job
        
        with patch('backend.workers.report_worker.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            
            result = process_report_job(client_name="NONEXISTENT")
            
            assert result["status"] == "failed"
            assert "not found" in result["error"].lower()


class TestOrchestrator:
    """Tests pour l'orchestrateur."""
    
    @patch('backend.workers.orchestrator.walk_files')
    @patch('backend.workers.orchestrator.extract_one')
    def test_extraction_step(self, mock_extract, mock_walk, tmp_path):
        """Test de l'étape d'extraction."""
        from backend.workers.orchestrator import ReportOrchestrator, ReportGenerationParams
        from extract_sources import ExtractedDoc
        
        # Mock files
        mock_walk.return_value = [tmp_path / "doc1.pdf"]
        
        # Mock extraction
        mock_doc = ExtractedDoc(
            path=str(tmp_path / "doc1.pdf"),
            ext=".pdf",
            size_bytes=1000,
            mtime_iso="2025-12-16T00:00:00",
            extractor="pymupdf",
            text="Test content",
            text_sha256="abc123",
            pages=None
        )
        mock_extract.return_value = mock_doc
        
        # Créer orchestrator
        params = ReportGenerationParams(
            client_dir=tmp_path,
            template_path=tmp_path / "template.docx",
            output_path=tmp_path / "output.docx"
        )
        
        orchestrator = ReportOrchestrator(params)
        orchestrator.temp_dir = tmp_path / "temp"
        orchestrator.temp_dir.mkdir()
        
        # Test extraction
        extracted_path = orchestrator._extract_sources()
        
        assert extracted_path.exists()
        assert extracted_path.suffix == ".json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
