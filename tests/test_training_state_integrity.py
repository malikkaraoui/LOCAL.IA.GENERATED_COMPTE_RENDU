"""
Tests anti-régression V4.1 - Intégrité schéma training_state_v1.0

Garantit que training_state.json respecte TOUJOURS les contraintes :
1. coverage_pct ∈ [0..100]
2. clients_with_section ≤ clients_used
3. Si section présente (coverage > 0), alors p90 >= 1
4. merge ne plante jamais
"""
import pytest
import json
from pathlib import Path
import tempfile

from src.rhpro.dataset_training import (
    analyze_dataset,
    export_training_artifacts,
    load_training_state,
    _merge_training_states
)


# ============================================================================
# TEST 1 : Coverage toujours borné [0..100]
# ============================================================================

def test_coverage_pct_always_bounded():
    """
    V4.1 Test : coverage_pct doit TOUJOURS être dans [0..100].
    
    Vérifie qu'aucune section ne peut avoir coverage > 100% ou < 0%.
    """
    # Utiliser BATCH 20 (dataset réel)
    batch20 = Path("/Users/malik/Documents/RH PRO BASE DONNEE/DATASET TRAINING/BATCH 20")
    
    if not batch20.exists():
        pytest.skip("BATCH 20 non disponible")
    
    # Analyser avec limit=5
    with tempfile.TemporaryDirectory() as tmpdir:
        result = analyze_dataset(str(batch20), out_dir=tmpdir, limit=5)
        
        paths = export_training_artifacts(result, out_dir=tmpdir, merge_existing=False)
        
        # Charger training_state.json (utiliser le path retourné par export)
        state = load_training_state(paths["training_state"])
        
        sections_stats = state["patterns"]["section_stats"]  # ✅ Schéma réel: section_stats (singulier)
        
        for sec, stats in sections_stats.items():
            coverage_pct = stats["coverage_pct"]  # ✅ Déjà en pourcentage (int 0-100)
            
            assert 0 <= coverage_pct <= 100, \
                f"Section {sec}: coverage_pct={coverage_pct}% HORS BORNES [0..100]"


# ============================================================================
# TEST 2 : clients_with_section ≤ clients_used
# ============================================================================

def test_clients_with_section_bounded():
    """
    V4.1 Test : clients (nombre de clients avec section) ≤ clients_used.
    
    Vérifie qu'on ne compte jamais plus de clients que le total disponible.
    """
    batch20 = Path("/Users/malik/Documents/RH PRO BASE DONNEE/DATASET TRAINING/BATCH 20")
    
    if not batch20.exists():
        pytest.skip("BATCH 20 non disponible")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = analyze_dataset(str(batch20), out_dir=tmpdir, limit=5)
        paths = export_training_artifacts(result, out_dir=tmpdir)
        
        state = load_training_state(paths["training_state"])
        
        clients_used = state["dataset"]["clients_used"]
        sections_stats = state["patterns"]["section_stats"]  # ✅ Schéma réel
        
        for sec, stats in sections_stats.items():
            clients_with_section = stats.get("clients", 0)
            
            assert clients_with_section <= clients_used, \
                f"Section {sec}: clients={clients_with_section} > clients_used={clients_used}"


# ============================================================================
# TEST 3 : Section présente → p90 >= 1
# ============================================================================

def test_section_present_implies_lines_nonzero():
    """
    V4.1 Test : Si une section est présente (coverage > 0), alors p90_lines >= 1.
    
    Évite les sections fantômes (coverage>0 mais lines=0).
    """
    batch20 = Path("/Users/malik/Documents/RH PRO BASE DONNEE/DATASET TRAINING/BATCH 20")
    
    if not batch20.exists():
        pytest.skip("BATCH 20 non disponible")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = analyze_dataset(str(batch20), out_dir=tmpdir, limit=5)
        paths = export_training_artifacts(result, out_dir=tmpdir)
        
        state = load_training_state(paths["training_state"])
        
        sections_stats = state["patterns"]["section_stats"]  # ✅ Schéma réel
        
        for sec, stats in sections_stats.items():
            coverage_pct = stats["coverage_pct"]  # ✅ Déjà en %
            p90_lines = stats["lines"]["p90"]
            
            if coverage_pct > 0:
                assert p90_lines >= 1, \
                    f"Section {sec}: coverage={coverage_pct}% mais p90_lines={p90_lines} (devrait être >= 1)"


# ============================================================================
# TEST 4 : Merge ne plante jamais
# ============================================================================

def test_merge_never_crashes():
    """
    V4.1 Test : merge_existing=True ne doit jamais lever d'exception.
    
    Même si les schémas existing/new diffèrent, le merge doit fonctionner.
    """
    batch20 = Path("/Users/malik/Documents/RH PRO BASE DONNEE/DATASET TRAINING/BATCH 20")
    
    if not batch20.exists():
        pytest.skip("BATCH 20 non disponible")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run 1 : créer training_state initial
        result1 = analyze_dataset(str(batch20), out_dir=tmpdir, limit=3)
        paths1 = export_training_artifacts(result1, out_dir=tmpdir, merge_existing=False)
        
        # Vérifier que training_state.json existe
        training_state_path = Path(paths1["training_state"])
        assert training_state_path.exists(), "training_state.json non créé"
        
        # Run 2 : merge avec existant (utiliser le même out_dir pour forcer le merge)
        result2 = analyze_dataset(str(batch20), out_dir=tmpdir, limit=5)
        
        # ✅ Ne doit PAS planter
        try:
            paths2 = export_training_artifacts(result2, out_dir=tmpdir, merge_existing=True)
        except Exception as e:
            pytest.fail(f"Merge a planté : {e}")
        
        # Charger merged state (utiliser le nouveau path retourné)
        state = load_training_state(paths2["training_state"])
        
        # Vérifier intégrité
        assert "patterns" in state
        assert "section_stats" in state["patterns"]  # ✅ Schéma réel
        assert "unknown_titles_top" in state["patterns"]


# ============================================================================
# TEST 5 : _merge_training_states compatible v1.0
# ============================================================================

def test_merge_function_compatible_v1_0():
    """
    V4.1 Test : _merge_training_states() accepte schéma training_state_v1.0.
    
    Teste la fonction pure sans dépendances fichiers.
    """
    # État existant (v1.0)
    existing = {
        "training_state_id": "old_123",
        "schema_version": "training_state_v1.0",
        "generated_at": "2025-12-27T10:00:00",
        "dataset": {
            "clients_used": 5
        },
        "patterns": {
            "unknown_titles_top": {
                "TITRE_OLD": 10,
                "TITRE_COMMUN": 5
            },
            "sections_stats": {
                "formation": {
                    "coverage": 0.8,
                    "p90_lines": 5.0
                }
            },
            "learned_title_map": {
                "FORMATION": "formation"
            }
        }
    }
    
    # Nouvel état (v1.0)
    new = {
        "training_state_id": "new_456",
        "schema_version": "training_state_v1.0",
        "generated_at": "2025-12-28T10:00:00",
        "dataset": {
            "clients_used": 3
        },
        "patterns": {
            "unknown_titles_top": {
                "TITRE_NEW": 7,
                "TITRE_COMMUN": 3
            },
            "sections_stats": {
                "formation": {
                    "coverage": 0.6,
                    "p90_lines": 7.0
                },
                "competences": {
                    "coverage": 0.5,
                    "p90_lines": 4.0
                }
            },
            "learned_title_map": {
                "COMPETENCES": "competences"
            }
        }
    }
    
    # ✅ Merge ne doit PAS planter
    try:
        merged = _merge_training_states(existing, new)
    except Exception as e:
        pytest.fail(f"_merge_training_states a planté : {e}")
    
    # Vérifications
    assert merged["training_state_id"] == "new_456", "Doit garder le nouvel ID"
    assert "history" in merged, "Doit créer historique"
    assert len(merged["history"]) >= 1, "Doit avoir au moins 1 entrée historique"
    
    # unknown_titles fusionnés
    assert merged["patterns"]["unknown_titles_top"]["TITRE_OLD"] == 10
    assert merged["patterns"]["unknown_titles_top"]["TITRE_NEW"] == 7
    assert merged["patterns"]["unknown_titles_top"]["TITRE_COMMUN"] == 8  # 5 + 3
    
    # sections_stats : p90 = max
    assert merged["patterns"]["sections_stats"]["formation"]["p90_lines"] == 7.0  # max(5, 7)
    
    # learned_title_map : union
    assert "FORMATION" in merged["patterns"]["learned_title_map"]
    assert "COMPETENCES" in merged["patterns"]["learned_title_map"]


# ============================================================================
# TEST 6 : Validation complète schéma
# ============================================================================

def test_training_state_schema_complete():
    """
    V4.1 Test : Vérifie que training_state.json contient TOUS les champs requis.
    """
    batch20 = Path("/Users/malik/Documents/RH PRO BASE DONNEE/DATASET TRAINING/BATCH 20")
    
    if not batch20.exists():
        pytest.skip("BATCH 20 non disponible")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = analyze_dataset(str(batch20), out_dir=tmpdir, limit=5)
        paths = export_training_artifacts(result, out_dir=tmpdir)
        
        state = load_training_state(paths["training_state"])
        
        # Champs racine (schéma réel)
        assert "run_id" in state  # ✅ Schéma réel utilise run_id
        assert "schema_version" in state
        assert state["schema_version"] == "training_state_v1.0"
        assert "created_at" in state  # ✅ Schéma réel: created_at
        assert "dataset" in state
        assert "patterns" in state
        assert "warnings" in state
        
        # dataset
        assert "clients_used" in state["dataset"]
        assert "root_path" in state["dataset"]  # ✅ Schéma réel: root_path
        
        # patterns
        patterns = state["patterns"]
        assert "unknown_titles_top" in patterns
        assert "unknown_titles_count" in patterns
        assert "section_stats" in patterns  # ✅ Schéma réel: section_stats
        assert "section_title_map" in patterns  # ✅ Schéma réel: section_title_map
        
        # section_stats structure (schéma réel)
        for sec, stats in patterns["section_stats"].items():
            assert "coverage_pct" in stats  # ✅ Schéma réel: coverage_pct (int 0-100)
            assert "clients" in stats
            assert "lines" in stats
            assert "avg" in stats["lines"]
            assert "median" in stats["lines"]
            assert "p90" in stats["lines"]
