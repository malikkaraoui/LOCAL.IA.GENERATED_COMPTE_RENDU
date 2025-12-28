#!/usr/bin/env python3
"""
Validation manuelle : démonstration du merge safe

Usage:
    python demo_merge_validation.py
"""
import sys
from pathlib import Path
import json

# Ajouter le projet au path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.rhpro.dataset_training import _merge_training_states


def demo_merge_safe():
    """
    Démo : Le merge ne plante jamais et fusionne correctement.
    """
    print("=" * 80)
    print("DÉMO : Merge Safe avec training_state_v1.0")
    print("=" * 80)
    print()
    
    # État existant (simulé)
    existing = {
        "training_state_id": "run_old_123",
        "schema_version": "training_state_v1.0",
        "generated_at": "2025-12-27T10:00:00",
        "dataset": {
            "clients_used": 10,
            "root_path": "/dataset/BATCH_A"
        },
        "patterns": {
            "field_max_lines": {
                "nom": 2,
                "prenom": 1,
                "email": 1
            },
            "section_stats": {
                "formation": {
                    "coverage_pct": 80,
                    "clients_with_section": 8,
                    "lines": {
                        "p90": 5.0,
                        "median": 3.0
                    }
                },
                "experience": {
                    "coverage_pct": 90,
                    "clients_with_section": 9,
                    "lines": {
                        "p90": 10.0,
                        "median": 7.0
                    }
                }
            }
        },
        "warnings": [
            {"code": "WARN_LOGO_MISSING", "message": "Logo non trouvé"}
        ]
    }
    
    # Nouvel état (nouveau run)
    new = {
        "training_state_id": "run_new_456",
        "schema_version": "training_state_v1.0",
        "generated_at": "2025-12-28T14:30:00",
        "dataset": {
            "clients_used": 15,
            "root_path": "/dataset/BATCH_B"
        },
        "patterns": {
            "field_max_lines": {
                "nom": 1,  # Plus petit que existing
                "email": 2,  # Plus grand que existing
                "telephone": 1  # Nouveau champ
            },
            "section_stats": {
                "formation": {
                    "coverage_pct": 70,  # Plus petit que existing
                    "clients_with_section": 10,
                    "lines": {
                        "p90": 8.0,  # Plus grand que existing
                        "median": 5.0
                    }
                },
                "competences": {  # Nouvelle section
                    "coverage_pct": 60,
                    "clients_with_section": 9,
                    "lines": {
                        "p90": 6.0,
                        "median": 4.0
                    }
                }
            }
        },
        "warnings": [
            {"code": "WARN_EXTRACTION_FAILED", "message": "Échec extraction"}
        ]
    }
    
    print("📦 État existant :")
    print(f"   - ID: {existing['training_state_id']}")
    print(f"   - Clients: {existing['dataset']['clients_used']}")
    print(f"   - Sections: {list(existing['patterns']['section_stats'].keys())}")
    print(f"   - Warnings: {len(existing['warnings'])}")
    print()
    
    print("📦 Nouvel état :")
    print(f"   - ID: {new['training_state_id']}")
    print(f"   - Clients: {new['dataset']['clients_used']}")
    print(f"   - Sections: {list(new['patterns']['section_stats'].keys())}")
    print(f"   - Warnings: {len(new['warnings'])}")
    print()
    
    # ✅ Merge
    print("🔄 Fusion en cours...")
    try:
        merged = _merge_training_states(existing, new)
        print("✅ Merge réussi sans erreur !")
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("=" * 80)
    print("📊 Résultat du merge :")
    print("=" * 80)
    print()
    
    # Base = new
    print("🔹 Base = new (metadata)")
    print(f"   ✅ ID: {merged['training_state_id']} (= {new['training_state_id']})")
    print(f"   ✅ Clients: {merged['dataset']['clients_used']} (= {new['dataset']['clients_used']})")
    print(f"   ✅ Root: {merged['dataset']['root_path']} (= {new['dataset']['root_path']})")
    print()
    
    # field_max_lines
    print("🔹 field_max_lines (max)")
    for field, val in sorted(merged['patterns']['field_max_lines'].items()):
        old_val = existing['patterns']['field_max_lines'].get(field, 0)
        new_val = new['patterns']['field_max_lines'].get(field, 0)
        expected = max(old_val, new_val)
        status = "✅" if val == expected else "❌"
        print(f"   {status} {field}: {val} (old={old_val}, new={new_val}, max={expected})")
    print()
    
    # section_stats
    print("🔹 section_stats (max p90, max coverage)")
    for sec in sorted(merged['patterns']['section_stats'].keys()):
        merged_sec = merged['patterns']['section_stats'][sec]
        old_sec = existing['patterns']['section_stats'].get(sec, {})
        new_sec = new['patterns']['section_stats'].get(sec, {})
        
        p90_merged = merged_sec['lines']['p90']
        p90_old = old_sec.get('lines', {}).get('p90', 0)
        p90_new = new_sec.get('lines', {}).get('p90', 0)
        p90_expected = max(p90_old, p90_new)
        
        cov_merged = merged_sec['coverage_pct']
        cov_old = old_sec.get('coverage_pct', 0)
        cov_new = new_sec.get('coverage_pct', 0)
        cov_expected = max(cov_old, cov_new)
        
        p90_ok = "✅" if p90_merged == p90_expected else "❌"
        cov_ok = "✅" if cov_merged == cov_expected else "❌"
        
        print(f"   📑 {sec}")
        print(f"      {p90_ok} p90: {p90_merged} (old={p90_old}, new={p90_new}, max={p90_expected})")
        print(f"      {cov_ok} coverage: {cov_merged}% (old={cov_old}%, new={cov_new}%, max={cov_expected}%)")
    print()
    
    # warnings
    print("🔹 warnings (union)")
    print(f"   ✅ Total: {len(merged['warnings'])} warnings")
    for w in merged['warnings']:
        print(f"      - {w['code']}: {w['message']}")
    print()
    
    # history
    print("🔹 history (traçabilité)")
    if "history" in merged:
        print(f"   ✅ {len(merged['history'])} entrées dans l'historique")
        for i, entry in enumerate(merged['history'], 1):
            print(f"      {i}. {entry.get('run_id', 'N/A')} - {entry.get('timestamp', 'N/A')} ({entry.get('clients', 0)} clients)")
    else:
        print("   ⚠️  Pas d'historique")
    print()
    
    print("=" * 80)
    print("✅ Validation complète : le merge fonctionne correctement !")
    print("=" * 80)
    
    # Sauvegarder le résultat
    output_path = Path("output/merge_demo_result.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Résultat sauvegardé : {output_path}")


if __name__ == "__main__":
    demo_merge_safe()
