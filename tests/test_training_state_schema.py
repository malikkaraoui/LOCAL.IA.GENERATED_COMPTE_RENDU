#!/usr/bin/env python3
"""
Tests DoD pour training_state.json.
Vérifie que le training state généré respecte le schéma v1.0 et contient tous les champs attendus.

IMPORTANT: Ces tests créent un mini dataset et vérifient la structure JSON générée.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from src.rhpro.dataset_training import analyze_dataset, export_training_artifacts


class TestTrainingStateSchema:
    """Tests de conformité du schéma training_state.json."""
    
    @pytest.fixture
    def sample_dataset(self, tmp_path):
        """Crée un mini dataset pour tests."""
        dataset_root = tmp_path / "mini_dataset"
        dataset_root.mkdir()
        
        # Client 1
        client1 = dataset_root / "DUPONT Jean"
        client1.mkdir()
        sources1 = client1 / "sources"
        sources1.mkdir()
        
        # Fichiers sources
        (sources1 / "cv.pdf").write_text("CV content")
        (sources1 / "rapport.docx").write_text("Rapport content")
        
        # Client 2
        client2 = dataset_root / "MARTIN Marie"
        client2.mkdir()
        sources2 = client2 / "sources"
        sources2.mkdir()
        (sources2 / "bilan.docx").write_text("Bilan content")
        
        return dataset_root
    
    @pytest.fixture
    def training_state(self, sample_dataset, tmp_path):
        """Génère un training_state pour les tests."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        result = analyze_dataset(
            root_dir=str(sample_dataset),
            out_dir=str(output_dir),
            scan_depth=2
        )
        
        paths = export_training_artifacts(
            result=result,
            out_dir=str(output_dir)
        )
        
        return json.loads(Path(paths["training_state"]).read_text())
    
    def test_training_state_schema_version(self, training_state):
        """Vérifie présence schema_version=1.0."""
        assert "schema_version" in training_state
        assert training_state["schema_version"] == "1.0"
        assert training_state["artifact_type"] == "training_state"
    
    def test_training_state_required_sections(self, training_state):
        """Vérifie présence de toutes les sections obligatoires."""
        # Sections principales
        assert "schema_version" in training_state
        assert "artifact_type" in training_state
        assert "created_at" in training_state
        assert "run_id" in training_state
        assert "dataset" in training_state
        assert "conventions" in training_state
        assert "learned_patterns" in training_state
        assert "validation_profiles" in training_state
        
        # Dataset
        dataset = training_state["dataset"]
        assert "root_path" in dataset
        assert "mode" in dataset
        assert "total_clients_scanned" in dataset
        assert "clients_detected" in dataset
        assert "allowed_extensions" in dataset
        
        # Conventions
        conventions = training_state["conventions"]
        assert "fallback_value" in conventions
        assert conventions["fallback_value"] == "Non renseigné"
        assert "strict_mode_default" in conventions
        assert "max_lines_defaults" in conventions
        
        # Learned patterns
        patterns = training_state["learned_patterns"]
        assert "section_title_map" in patterns
        assert "doc_types_stats" in patterns
    
    def test_training_state_validation_profiles(self, training_state):
        """Vérifie présence des 3 profils STRICT/STANDARD/DRAFT."""
        profiles = training_state["validation_profiles"]
        
        # Les 3 profils doivent exister
        assert "STRICT" in profiles
        assert "STANDARD" in profiles
        assert "DRAFT" in profiles
        
        # Chaque profil doit avoir les champs requis
        for profile_name in ["STRICT", "STANDARD", "DRAFT"]:
            profile = profiles[profile_name]
            assert "required_coverage_min" in profile
            assert "weighted_coverage_min" in profile
            assert "quality_score_min" in profile
            assert "avg_confidence_min" in profile
            assert "sources_count_min" in profile
            assert "critical_fields" in profile
            assert "profession_or_formation_required" in profile
            
            # Types
            assert isinstance(profile["required_coverage_min"], (int, float))
            assert isinstance(profile["weighted_coverage_min"], (int, float))
            assert isinstance(profile["quality_score_min"], (int, float))
            assert isinstance(profile["avg_confidence_min"], (int, float))
            assert isinstance(profile["sources_count_min"], int)
            assert isinstance(profile["critical_fields"], list)
            assert isinstance(profile["profession_or_formation_required"], bool)
    
    def test_training_state_fallback_consistency(self, training_state):
        """Vérifie que fallback_value = 'Non renseigné' (pas NOT_FOUND)."""
        fallback = training_state["conventions"]["fallback_value"]
        assert fallback == "Non renseigné"
    
    def test_training_state_timestamp_format(self, training_state):
        """Vérifie format ISO 8601 pour created_at."""
        created_at = training_state["created_at"]
        # Doit parser en datetime ISO
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            assert dt.year >= 2025
        except ValueError as e:
            pytest.fail(f"created_at format invalide: {created_at}, error: {e}")
    
    def test_training_state_doc_types_stats(self, training_state):
        """Vérifie doc_types_stats contient extensions avec count + coverage."""
        doc_stats = training_state["learned_patterns"]["doc_types_stats"]
        assert isinstance(doc_stats, dict)
        
        # Chaque extension doit avoir count et clients_coverage
        for ext, stats in doc_stats.items():
            assert ext.startswith(".")
            assert "count" in stats
            assert "clients_coverage" in stats
            assert isinstance(stats["count"], int)
            assert isinstance(stats["clients_coverage"], (int, float))
            assert 0 <= stats["clients_coverage"] <= 1
    
    def test_training_state_run_id_unique(self, sample_dataset, tmp_path):
        """Vérifie que run_id est généré et unique."""
        import time
        output_dir1 = tmp_path / "output1"
        output_dir1.mkdir()
        output_dir2 = tmp_path / "output2"
        output_dir2.mkdir()
        
        # Run 1
        result1 = analyze_dataset(root_dir=str(sample_dataset), out_dir=str(output_dir1), scan_depth=2)
        paths1 = export_training_artifacts(result1, str(output_dir1))
        state1 = json.loads(Path(paths1["training_state"]).read_text())
        
        # Attendre 1 seconde pour garantir timestamp différent
        time.sleep(1)
        
        # Run 2
        result2 = analyze_dataset(root_dir=str(sample_dataset), out_dir=str(output_dir2), scan_depth=2)
        paths2 = export_training_artifacts(result2, str(output_dir2))
        state2 = json.loads(Path(paths2["training_state"]).read_text())
        
        # run_id doivent exister et être différents
        assert "run_id" in state1
        assert "run_id" in state2
        assert state1["run_id"] != state2["run_id"], f"run_id should be unique: {state1['run_id']} == {state2['run_id']}"
    
    def test_training_state_max_lines_defaults(self, training_state):
        """Vérifie présence max_lines_defaults pour sections clés."""
        max_lines = training_state["conventions"]["max_lines_defaults"]
        
        # Sections clés doivent avoir des defaults
        expected_sections = ["formation", "profession"]
        for section in expected_sections:
            assert section in max_lines
            assert isinstance(max_lines[section], int)
            assert max_lines[section] > 0
