"""
Tests unitaires pour la couche de validation GO/NO-GO.
"""

import json
import pytest
from pathlib import Path
from src.rhpro.validation_profiles import (
    validate_report,
    validate_batch,
    get_validation_summary,
    ValidationProfile,
    ValidationStatus,
    CRITICAL_FIELDS,
)


@pytest.fixture
def temp_output_dir(tmp_path):
    """Crée un dossier temporaire pour les tests."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def excellent_metrics():
    """Métriques d'un excellent rapport."""
    return {
        "required_coverage": 95,
        "weighted_coverage": 92,
        "quality_score": 0.88,
        "avg_confidence": 0.85,
        "total_fields": 21,
        "filled_fields": 20,
        "required_fields": 10,
        "required_filled": 10,
    }


@pytest.fixture
def excellent_debug():
    """Debug d'un excellent rapport."""
    return {
        "index": {
            "sources_count": 8,
            "chunks_created": 64,
        },
        "extracted_fields": [
            {"field": "nom", "value": "Martin"},
            {"field": "prenom", "value": "Sophie"},
            {"field": "date_naissance", "value": "12/08/1990"},
            {"field": "situation_professionnelle", "value": "En recherche"},
        ],
    }


@pytest.fixture
def poor_metrics():
    """Métriques d'un rapport pauvre."""
    return {
        "required_coverage": 45,
        "weighted_coverage": 38,
        "quality_score": 0.42,
        "avg_confidence": 0.35,
        "total_fields": 21,
        "filled_fields": 8,
        "required_fields": 10,
        "required_filled": 4,
    }


@pytest.fixture
def poor_debug():
    """Debug d'un rapport pauvre."""
    return {
        "index": {
            "sources_count": 1,
            "chunks_created": 5,
        },
        "extracted_fields": [
            {"field": "nom", "value": "Non renseigné"},
            {"field": "prenom", "value": "Non renseigné"},
        ],
    }


class TestValidationProfiles:
    """Tests des profils de validation."""
    
    def test_strict_profile_go(self, temp_output_dir, excellent_metrics, excellent_debug):
        """Test STRICT profile avec excellent rapport → GO."""
        # Créer fichiers
        metrics_path = temp_output_dir / "test_metrics.json"
        debug_path = temp_output_dir / "test_debug.json"
        
        with open(metrics_path, 'w') as f:
            json.dump(excellent_metrics, f)
        
        with open(debug_path, 'w') as f:
            json.dump(excellent_debug, f)
        
        # Valider
        result = validate_report(
            metrics_path=metrics_path,
            debug_path=debug_path,
            profile=ValidationProfile.STRICT,
        )
        
        # Assertions
        assert result.status == ValidationStatus.GO
        assert result.profile == ValidationProfile.STRICT.value
        assert result.scores["quality_score"] >= 0.75
        assert result.scores["required_coverage"] >= 0.85
        assert len(result.reasons) == 0  # Aucune raison si GO
    
    def test_strict_profile_no_go(self, temp_output_dir, poor_metrics, poor_debug):
        """Test STRICT profile avec rapport pauvre → NO_GO."""
        # Créer fichiers
        metrics_path = temp_output_dir / "test_metrics.json"
        debug_path = temp_output_dir / "test_debug.json"
        
        with open(metrics_path, 'w') as f:
            json.dump(poor_metrics, f)
        
        with open(debug_path, 'w') as f:
            json.dump(poor_debug, f)
        
        # Valider
        result = validate_report(
            metrics_path=metrics_path,
            debug_path=debug_path,
            profile=ValidationProfile.STRICT,
        )
        
        # Assertions
        assert result.status == ValidationStatus.NO_GO
        assert result.profile == ValidationProfile.STRICT.value
        assert len(result.reasons) > 0
        assert len(result.actions) > 0
        assert any("low_required_coverage" in r for r in result.reasons)
    
    def test_standard_profile_tolerance(self, temp_output_dir):
        """Test STANDARD profile avec 1 champ critique manquant → GO."""
        # Métriques moyennes mais acceptables
        metrics = {
            "required_coverage": 78,
            "weighted_coverage": 72,
            "quality_score": 0.68,
            "avg_confidence": 0.62,
        }
        
        debug = {
            "index": {"sources_count": 3, "chunks_created": 22},
            "extracted_fields": [
                {"field": "nom", "value": "Bernard"},
                {"field": "prenom", "value": "Luc"},
                {"field": "date_naissance", "value": "Non renseigné"},  # 1 manquant
                {"field": "situation_professionnelle", "value": "Étudiant"},
            ],
        }
        
        # Créer fichiers
        metrics_path = temp_output_dir / "test_metrics.json"
        debug_path = temp_output_dir / "test_debug.json"
        
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f)
        
        with open(debug_path, 'w') as f:
            json.dump(debug, f)
        
        # Valider avec STANDARD (tolérance 1 champ)
        result = validate_report(
            metrics_path=metrics_path,
            debug_path=debug_path,
            profile=ValidationProfile.STANDARD,
        )
        
        # Assertions
        assert result.status == ValidationStatus.GO  # Accepté avec STANDARD
        assert result.profile == ValidationProfile.STANDARD.value
        assert any("missing_fields" in r for r in result.reasons)  # Mais noté
    
    def test_draft_profile_always_draft(self, temp_output_dir, poor_metrics, poor_debug):
        """Test DRAFT profile → toujours DRAFT même avec données pauvres."""
        # Créer fichiers
        metrics_path = temp_output_dir / "test_metrics.json"
        debug_path = temp_output_dir / "test_debug.json"
        
        with open(metrics_path, 'w') as f:
            json.dump(poor_metrics, f)
        
        with open(debug_path, 'w') as f:
            json.dump(poor_debug, f)
        
        # Valider avec DRAFT
        result = validate_report(
            metrics_path=metrics_path,
            debug_path=debug_path,
            profile=ValidationProfile.DRAFT,
        )
        
        # Assertions
        assert result.status == ValidationStatus.DRAFT
        assert result.profile == ValidationProfile.DRAFT.value
        assert "draft_mode_enabled" in result.reasons
        assert "review_and_complete" in result.actions


class TestBatchValidation:
    """Tests de validation batch."""
    
    def test_validate_batch_mixed_results(self, temp_output_dir):
        """Test validation d'un batch avec résultats mixtes."""
        # Créer 3 clients : 1 excellent, 1 moyen, 1 pauvre
        clients = [
            {
                "name": "excellent",
                "metrics": {
                    "required_coverage": 95,
                    "weighted_coverage": 92,
                    "quality_score": 0.88,
                    "avg_confidence": 0.85,
                },
                "debug": {
                    "index": {"sources_count": 8, "chunks_created": 64},
                    "extracted_fields": [
                        {"field": "nom", "value": "Martin"},
                        {"field": "prenom", "value": "Sophie"},
                        {"field": "date_naissance", "value": "12/08/1990"},
                        {"field": "situation_professionnelle", "value": "En recherche"},
                    ],
                },
            },
            {
                "name": "moyen",
                "metrics": {
                    "required_coverage": 72,
                    "weighted_coverage": 68,
                    "quality_score": 0.62,
                    "avg_confidence": 0.58,
                },
                "debug": {
                    "index": {"sources_count": 3, "chunks_created": 18},
                    "extracted_fields": [
                        {"field": "nom", "value": "Durand"},
                        {"field": "prenom", "value": "Paul"},
                        {"field": "date_naissance", "value": "Non renseigné"},
                        {"field": "situation_professionnelle", "value": "Salarié"},
                    ],
                },
            },
            {
                "name": "pauvre",
                "metrics": {
                    "required_coverage": 45,
                    "weighted_coverage": 38,
                    "quality_score": 0.42,
                    "avg_confidence": 0.35,
                },
                "debug": {
                    "index": {"sources_count": 1, "chunks_created": 5},
                    "extracted_fields": [
                        {"field": "nom", "value": "Non renseigné"},
                    ],
                },
            },
        ]
        
        # Créer fichiers
        for client in clients:
            metrics_path = temp_output_dir / f"{client['name']}_metrics.json"
            debug_path = temp_output_dir / f"{client['name']}_debug.json"
            
            with open(metrics_path, 'w') as f:
                json.dump(client["metrics"], f)
            
            with open(debug_path, 'w') as f:
                json.dump(client["debug"], f)
        
        # Valider batch avec STANDARD
        results = validate_batch(temp_output_dir, profile=ValidationProfile.STANDARD)
        
        # Assertions
        assert len(results) == 3
        assert results["excellent"].status == ValidationStatus.GO
        assert results["pauvre"].status == ValidationStatus.NO_GO
        
        # Résumé
        summary = get_validation_summary(results)
        assert summary["total"] == 3
        assert summary["go_count"] >= 1
        assert summary["no_go_count"] >= 1
    
    def test_validation_summary(self, temp_output_dir):
        """Test génération du résumé de validation."""
        # Créer 2 clients
        for i, status in enumerate(["go", "no_go"]):
            metrics = {
                "required_coverage": 90 if status == "go" else 50,
                "weighted_coverage": 88 if status == "go" else 45,
                "quality_score": 0.85 if status == "go" else 0.42,
                "avg_confidence": 0.82 if status == "go" else 0.35,
            }
            
            debug = {
                "index": {"sources_count": 5 if status == "go" else 1},
                "extracted_fields": [
                    {"field": "nom", "value": "Test" if status == "go" else "Non renseigné"},
                ],
            }
            
            with open(temp_output_dir / f"client_{i}_metrics.json", 'w') as f:
                json.dump(metrics, f)
            
            with open(temp_output_dir / f"client_{i}_debug.json", 'w') as f:
                json.dump(debug, f)
        
        # Valider
        results = validate_batch(temp_output_dir, profile=ValidationProfile.STRICT)
        summary = get_validation_summary(results)
        
        # Assertions
        assert summary["total"] == 2
        assert summary["go_count"] + summary["no_go_count"] + summary["draft_count"] == 2
        assert 0 <= summary["go_rate"] <= 1
        assert "avg_scores" in summary
        assert "top_reasons" in summary


class TestCriticalFields:
    """Tests des champs critiques."""
    
    def test_critical_fields_defined(self):
        """Test que les champs critiques sont définis."""
        assert len(CRITICAL_FIELDS) > 0
        assert "nom" in CRITICAL_FIELDS
        assert "prenom" in CRITICAL_FIELDS
        assert "date_naissance" in CRITICAL_FIELDS
        assert "situation_professionnelle" in CRITICAL_FIELDS
    
    def test_missing_critical_fields_detection(self, temp_output_dir):
        """Test détection des champs critiques manquants."""
        metrics = {
            "required_coverage": 50,
            "weighted_coverage": 45,
            "quality_score": 0.5,
            "avg_confidence": 0.4,
        }
        
        # Aucun champ critique extrait
        debug = {
            "index": {"sources_count": 2},
            "extracted_fields": [
                {"field": "objectifs_professionnels", "value": "Trouver un emploi"},
            ],
        }
        
        with open(temp_output_dir / "test_metrics.json", 'w') as f:
            json.dump(metrics, f)
        
        with open(temp_output_dir / "test_debug.json", 'w') as f:
            json.dump(debug, f)
        
        result = validate_report(
            metrics_path=temp_output_dir / "test_metrics.json",
            debug_path=temp_output_dir / "test_debug.json",
            profile=ValidationProfile.STRICT,
        )
        
        # Assertions
        assert result.status == ValidationStatus.NO_GO
        assert any("missing_critical_fields" in r for r in result.reasons)
        assert any("add_identity_sources" in a for a in result.actions)


class TestValidationOutput:
    """Tests des outputs de validation."""
    
    def test_validation_result_to_dict(self, temp_output_dir, excellent_metrics, excellent_debug):
        """Test conversion ValidationResult → dict."""
        with open(temp_output_dir / "test_metrics.json", 'w') as f:
            json.dump(excellent_metrics, f)
        
        with open(temp_output_dir / "test_debug.json", 'w') as f:
            json.dump(excellent_debug, f)
        
        result = validate_report(
            metrics_path=temp_output_dir / "test_metrics.json",
            debug_path=temp_output_dir / "test_debug.json",
            profile=ValidationProfile.STRICT,
        )
        
        result_dict = result.to_dict()
        
        # Assertions
        assert isinstance(result_dict, dict)
        assert "status" in result_dict
        assert "profile" in result_dict
        assert "reasons" in result_dict
        assert "actions" in result_dict
        assert "scores" in result_dict
    
    def test_validation_result_to_json(self, temp_output_dir, excellent_metrics, excellent_debug):
        """Test conversion ValidationResult → JSON."""
        with open(temp_output_dir / "test_metrics.json", 'w') as f:
            json.dump(excellent_metrics, f)
        
        with open(temp_output_dir / "test_debug.json", 'w') as f:
            json.dump(excellent_debug, f)
        
        result = validate_report(
            metrics_path=temp_output_dir / "test_metrics.json",
            debug_path=temp_output_dir / "test_debug.json",
            profile=ValidationProfile.STRICT,
        )
        
        result_json = result.to_json()
        
        # Assertions
        assert isinstance(result_json, str)
        parsed = json.loads(result_json)
        assert parsed["status"] == "GO"
        assert parsed["profile"] == "strict"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
