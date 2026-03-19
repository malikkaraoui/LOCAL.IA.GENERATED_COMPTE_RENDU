# tests/test_api_review.py
"""Test review API endpoints (report-types, models, routing)."""
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.main import app
    return TestClient(app)


class TestReportTypeEndpoints:
    def test_list_report_types(self, client):
        """GET /api/report-types returns available types."""
        response = client.get("/api/report-types")
        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        keys = [t["key"] for t in data["types"]]
        assert "rapport_initial" in keys
        assert "rapport_final" in keys

    def test_report_create_request_accepts_report_type(self):
        """ReportCreateRequest model accepts report_type field."""
        from backend.api.models import ReportCreateRequest
        req = ReportCreateRequest(
            client_name="Test Client",
            report_type="rapport_initial",
        )
        assert req.report_type == "rapport_initial"

    def test_report_create_request_report_type_optional(self):
        """report_type is optional (backwards compatible)."""
        from backend.api.models import ReportCreateRequest
        req = ReportCreateRequest(client_name="Test Client")
        assert req.report_type is None
