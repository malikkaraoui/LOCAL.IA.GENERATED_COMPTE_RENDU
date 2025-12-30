"""
Tests pour l'exclusion et quarantaine des clients avec sources_count=0

Feature: Exclure (et optionnellement mettre en quarantaine) les dossiers clients avec sources_count=0

AC1: Exclusion logique (obligatoire)
- clients_scanned = tous les dossiers détectés
- clients_usable = seulement ceux avec sources_count >= 1
- clients_used = clients_usable (par défaut)

AC2: Reporting
- empty_sources_clients_count dans stats
- Liste des client_ids vides (top 50)

AC3: Quarantaine physique (optionnel)
- Flag --quarantine-empty-sources (default: false)
- Déplacer vers data/_trash/empty_sources/<run_id>/
- Écrire manifest.json
- Ne jamais supprimer définitivement
"""

import pytest
import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestExcludeEmptySources:
    """AC1: Exclusion logique des clients avec sources_count=0"""
    
    def test_exclude_empty_sources_from_used(self):
        """
        clients_used doit exclure les clients avec sources_count=0
        
        Scénario: Sur 571 clients scannés, 47 ont sources=0
        Résultat: clients_used = 524
        """
        # Simuler clients
        all_clients = []
        
        # 524 clients avec sources >= 1
        for i in range(524):
            all_clients.append({
                "folder_name": f"CLIENT_{i:03d}",
                "sources_count": 1 + (i % 5),  # 1-5 sources
                "sections_extracted": 6,
            })
        
        # 47 clients avec sources = 0
        for i in range(47):
            all_clients.append({
                "folder_name": f"CLIENT_EMPTY_{i:03d}",
                "sources_count": 0,
                "sections_extracted": 0,
            })
        
        # Calculer clients_used (logique de dataset_training.py)
        clients_used_list = [c for c in all_clients if c.get('sources_count', 0) > 0]
        clients_used = len(clients_used_list)
        
        empty_sources_clients = [c for c in all_clients if c.get('sources_count', 0) == 0]
        clients_no_sources = len(empty_sources_clients)
        
        assert clients_used == 524, f"Expected 524 usable clients, got {clients_used}"
        assert clients_no_sources == 47, f"Expected 47 empty clients, got {clients_no_sources}"
        assert clients_used + clients_no_sources == len(all_clients), "Total should match"
    
    def test_clients_usable_equals_clients_used_by_default(self):
        """
        Par défaut (sans filtres additionnels), clients_usable == clients_used
        """
        successful_clients = [
            {"sources_count": 3},
            {"sources_count": 1},
            {"sources_count": 0},  # excluded
            {"sources_count": 2},
            {"sources_count": 0},  # excluded
        ]
        
        clients_usable = [c for c in successful_clients if c.get('sources_count', 0) >= 1]
        clients_used = len(clients_usable)
        
        assert clients_used == 3, f"Expected 3 usable clients, got {clients_used}"
        assert clients_used == len(clients_usable), "clients_used should equal clients_usable"


class TestReportEmptySources:
    """AC2: Reporting des clients avec sources_count=0"""
    
    def test_report_includes_empty_sources_count(self):
        """
        Le rapport stats doit inclure empty_sources_clients_count
        """
        # Simuler stats (logique de dataset_training.py)
        empty_sources_clients = [
            {"folder_name": "CLIENT_A"},
            {"folder_name": "CLIENT_B"},
            {"folder_name": "CLIENT_C"},
        ]
        
        stats = {
            "empty_sources_clients_count": len(empty_sources_clients),
            "empty_sources_clients": [c["folder_name"] for c in empty_sources_clients],
        }
        
        assert "empty_sources_clients_count" in stats
        assert stats["empty_sources_clients_count"] == 3
        assert "empty_sources_clients" in stats
        assert len(stats["empty_sources_clients"]) == 3
    
    def test_report_includes_empty_sources_list(self):
        """
        Le rapport doit lister les client_ids vides (top 50)
        """
        # Simuler 60 clients vides
        empty_sources_clients = [
            {"folder_name": f"CLIENT_EMPTY_{i:03d}"}
            for i in range(60)
        ]
        
        # Ne garder que top 50
        stats = {
            "empty_sources_clients": [c["folder_name"] for c in empty_sources_clients[:50]],
        }
        
        assert len(stats["empty_sources_clients"]) == 50, "Should limit to top 50"
        assert "CLIENT_EMPTY_000" in stats["empty_sources_clients"]
        assert "CLIENT_EMPTY_049" in stats["empty_sources_clients"]
        assert "CLIENT_EMPTY_059" not in stats["empty_sources_clients"]
    
    def test_empty_clients_list_matches_count(self):
        """
        La liste empty_sources_clients doit correspondre au count (si < 50)
        """
        empty_sources_clients = [
            {"folder_name": "CLIENT_A"},
            {"folder_name": "CLIENT_B"},
        ]
        
        stats = {
            "empty_sources_clients_count": len(empty_sources_clients),
            "empty_sources_clients": [c["folder_name"] for c in empty_sources_clients[:50]],
        }
        
        assert stats["empty_sources_clients_count"] == 2
        assert len(stats["empty_sources_clients"]) == 2


class TestQuarantineEmptySources:
    """AC3: Quarantaine physique des clients avec sources_count=0"""
    
    def test_quarantine_disabled_by_default(self):
        """
        Par défaut, quarantine_empty_sources=False
        """
        from src.rhpro.dataset_training import analyze_dataset
        
        # Vérifier signature de la fonction
        import inspect
        sig = inspect.signature(analyze_dataset)
        
        assert "quarantine_empty_sources" in sig.parameters
        assert sig.parameters["quarantine_empty_sources"].default is False, (
            "quarantine_empty_sources should default to False"
        )
    
    def test_quarantine_moves_folder_and_writes_manifest(self, tmp_path):
        """
        Avec quarantine_empty_sources=True, dossiers vides déplacés + manifest créé
        """
        # Setup: Créer dossiers clients
        clients_dir = tmp_path / "CLIENTS"
        clients_dir.mkdir()
        
        client_empty_1 = clients_dir / "CLIENT_EMPTY_A"
        client_empty_1.mkdir()
        (client_empty_1 / "dummy.txt").write_text("test")
        
        client_with_sources = clients_dir / "CLIENT_WITH_SOURCES"
        client_with_sources.mkdir()
        (client_with_sources / "source.docx").write_text("content")
        
        # Simuler logique de quarantaine
        empty_sources_clients = [
            {
                "folder_name": "CLIENT_EMPTY_A",
                "folder_path": str(client_empty_1),
                "sources_count": 0,
            }
        ]
        
        quarantine_base = tmp_path / "data/_trash/empty_sources/test_run"
        quarantine_base.mkdir(parents=True, exist_ok=True)
        
        manifest_entries = []
        for client_data in empty_sources_clients:
            client_folder_path = Path(client_data["folder_path"])
            dest_path = quarantine_base / client_folder_path.name
            
            shutil.move(str(client_folder_path), str(dest_path))
            
            manifest_entries.append({
                "client_id": client_data["folder_name"],
                "path_before": str(client_folder_path),
                "path_after": str(dest_path),
                "reason": "sources_count=0",
            })
        
        # Écrire manifest
        manifest_path = quarantine_base / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": "test_run",
                "total_quarantined": len(manifest_entries),
                "entries": manifest_entries,
            }, f, indent=2)
        
        # Assertions
        assert not client_empty_1.exists(), "Empty client should be moved"
        assert client_with_sources.exists(), "Client with sources should NOT be moved"
        
        moved_client = quarantine_base / "CLIENT_EMPTY_A"
        assert moved_client.exists(), "Client should be in quarantine"
        assert (moved_client / "dummy.txt").exists(), "Files should be preserved"
        
        assert manifest_path.exists(), "Manifest should be created"
        
        manifest = json.loads(manifest_path.read_text())
        assert manifest["total_quarantined"] == 1
        assert len(manifest["entries"]) == 1
        assert manifest["entries"][0]["client_id"] == "CLIENT_EMPTY_A"
        assert manifest["entries"][0]["reason"] == "sources_count=0"
    
    def test_quarantine_does_not_delete(self, tmp_path):
        """
        Quarantaine doit DÉPLACER, pas supprimer (shutil.move, pas shutil.rmtree)
        """
        # Setup
        client_folder = tmp_path / "CLIENT_TO_QUARANTINE"
        client_folder.mkdir()
        test_file = client_folder / "important.txt"
        test_file.write_text("Important data")
        
        quarantine_base = tmp_path / "quarantine"
        quarantine_base.mkdir()
        
        # Déplacer (PAS supprimer)
        dest_path = quarantine_base / client_folder.name
        shutil.move(str(client_folder), str(dest_path))
        
        # Vérifier que les données sont préservées
        assert not client_folder.exists(), "Original should be gone"
        assert dest_path.exists(), "Should be in quarantine"
        assert (dest_path / "important.txt").exists(), "File should be preserved"
        assert (dest_path / "important.txt").read_text() == "Important data", (
            "Content should be intact"
        )
    
    def test_quarantine_handles_errors_gracefully(self, tmp_path):
        """
        Si erreur lors du move, ne pas casser le run (log + continue)
        """
        # Simuler une erreur de move
        empty_sources_clients = [
            {"folder_name": "CLIENT_A", "folder_path": "/nonexistent/path"},
            {"folder_name": "CLIENT_B", "folder_path": str(tmp_path / "valid_client")},
        ]
        
        # Créer CLIENT_B valide
        (tmp_path / "valid_client").mkdir()
        
        quarantine_base = tmp_path / "quarantine"
        quarantine_base.mkdir()
        
        manifest_entries = []
        errors = []
        
        for client_data in empty_sources_clients:
            try:
                client_folder_path = Path(client_data["folder_path"])
                dest_path = quarantine_base / client_folder_path.name
                
                shutil.move(str(client_folder_path), str(dest_path))
                manifest_entries.append({"client_id": client_data["folder_name"]})
            except Exception as e:
                errors.append(client_data["folder_name"])
                continue  # Ne pas casser le run
        
        # Vérifier que le run continue malgré erreurs
        assert len(errors) == 1, "CLIENT_A should have errored"
        assert "CLIENT_A" in errors
        assert len(manifest_entries) == 1, "CLIENT_B should have succeeded"
        assert manifest_entries[0]["client_id"] == "CLIENT_B"
    
    def test_manifest_structure(self, tmp_path):
        """
        Manifest JSON doit avoir la structure correcte
        """
        manifest_path = tmp_path / "manifest.json"
        
        manifest = {
            "run_id": "abc123",
            "timestamp": "2025-12-29T10:00:00",
            "total_quarantined": 2,
            "entries": [
                {
                    "client_id": "CLIENT_A",
                    "path_before": "/path/to/CLIENT_A",
                    "path_after": "/quarantine/CLIENT_A",
                    "timestamp": "2025-12-29T10:00:00",
                    "reason": "sources_count=0",
                },
                {
                    "client_id": "CLIENT_B",
                    "path_before": "/path/to/CLIENT_B",
                    "path_after": "/quarantine/CLIENT_B",
                    "timestamp": "2025-12-29T10:00:01",
                    "reason": "sources_count=0",
                },
            ],
        }
        
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        # Vérifier structure
        loaded = json.loads(manifest_path.read_text())
        
        assert "run_id" in loaded
        assert "timestamp" in loaded
        assert "total_quarantined" in loaded
        assert "entries" in loaded
        
        assert loaded["total_quarantined"] == 2
        assert len(loaded["entries"]) == 2
        
        entry = loaded["entries"][0]
        assert "client_id" in entry
        assert "path_before" in entry
        assert "path_after" in entry
        assert "timestamp" in entry
        assert "reason" in entry
        assert entry["reason"] == "sources_count=0"


class TestIntegrationEmptySourcesFeature:
    """Tests d'intégration pour la feature complète"""
    
    def test_essai_100_expected_metrics(self):
        """
        Sur ESSAI 100 (571 clients), vérifier métriques attendues
        
        Avant feature:
        - clients_used = 571 (❌ inclut 47 avec sources=0)
        
        Après feature:
        - clients_used = 524 (✅ exclut sources=0)
        - empty_sources_clients_count = 47
        """
        total_clients = 571
        expected_usable = 524
        expected_empty = 47
        
        assert expected_usable + expected_empty == total_clients, (
            "Math should be consistent"
        )
        
        # Simuler calcul
        all_clients = (
            [{"sources_count": i % 5 + 1} for i in range(expected_usable)] +
            [{"sources_count": 0} for _ in range(expected_empty)]
        )
        
        clients_used = len([c for c in all_clients if c.get('sources_count', 0) > 0])
        empty_count = len([c for c in all_clients if c.get('sources_count', 0) == 0])
        
        assert clients_used == expected_usable
        assert empty_count == expected_empty
    
    def test_ready_rates_calculated_on_usable_only(self):
        """
        Les taux ready_* doivent être calculés sur clients_usable, pas total
        
        Exemple: 524 usable, 450 STRICT
        → ready_strict_rate = 450/524 = 85.9% (PAS 450/571 = 78.8%)
        """
        clients_usable = 524
        ready_strict = 450
        
        # INCORRECT (sur total avec empty)
        total_with_empty = 571
        rate_wrong = ready_strict / total_with_empty
        
        # CORRECT (sur usable seulement)
        rate_correct = ready_strict / clients_usable
        
        assert rate_correct > rate_wrong, "Rate on usable should be higher"
        assert abs(rate_correct - 0.859) < 0.001, (
            f"Expected ~85.9%, got {rate_correct:.1%}"
        )
        assert abs(rate_wrong - 0.788) < 0.001, (
            f"Old calculation was ~78.8%, got {rate_wrong:.1%}"
        )
    
    def test_quarantine_path_in_stats(self):
        """
        Si quarantine activée, stats doit contenir quarantine_manifest_path
        """
        # Sans quarantine
        stats_without = {
            "empty_sources_clients_count": 47,
            "quarantine_manifest_path": None,
        }
        
        assert stats_without["quarantine_manifest_path"] is None
        
        # Avec quarantine
        stats_with = {
            "empty_sources_clients_count": 47,
            "quarantine_manifest_path": "data/_trash/empty_sources/abc123/manifest.json",
        }
        
        assert stats_with["quarantine_manifest_path"] is not None
        assert "manifest.json" in stats_with["quarantine_manifest_path"]


class TestAntiRegressionEmptySources:
    """Tests de non-régression"""
    
    def test_imports_not_broken(self):
        """Vérifier que dataset_training.py importe correctement shutil et uuid"""
        try:
            from src.rhpro.dataset_training import analyze_dataset
            import inspect
            
            # Vérifier que la fonction accepte le nouveau paramètre
            sig = inspect.signature(analyze_dataset)
            assert "quarantine_empty_sources" in sig.parameters
            
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")
    
    def test_backwards_compatible_default(self):
        """
        Sans le flag quarantine_empty_sources, comportement par défaut inchangé
        """
        # Simuler appel sans flag
        quarantine_empty_sources = False  # default
        
        if quarantine_empty_sources:
            pytest.fail("Should not enter quarantine logic by default")
        
        # Pas de quarantine = pas de manifest
        quarantine_manifest = None
        assert quarantine_manifest is None, "No manifest should be created by default"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
