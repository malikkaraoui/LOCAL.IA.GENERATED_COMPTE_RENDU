"""
Script d'exemple pour lancer le diagnostic GOLD missing.

Usage:
    python demo_gold_diagnostics.py /path/to/CLIENTS_FOLDER
    
Outputs:
    - output/training/gold_missing_debug.jsonl
    - output/training/gold_missing_debug.md
"""

import sys
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from src.rhpro.dataset_training import analyze_dataset


def main():
    """Exemple d'analyse avec diagnostic GOLD missing"""
    
    if len(sys.argv) < 2:
        print("Usage: python demo_gold_diagnostics.py /path/to/CLIENTS_FOLDER")
        sys.exit(1)
    
    clients_folder = sys.argv[1]
    
    print("=" * 80)
    print("DIAGNOSTIC GOLD MISSING")
    print("=" * 80)
    print(f"\n📂 Dossier clients: {clients_folder}")
    print(f"📁 Output: output/training/\n")
    
    # Lancer l'analyse (limite 10 clients pour l'exemple)
    result = analyze_dataset(
        root_dir=clients_folder,
        out_dir="output/training",
        limit=10,  # Limiter pour test rapide
        index_msg=False,  # Exclure .msg pour performance
    )
    
    print("\n" + "=" * 80)
    print("RÉSULTATS")
    print("=" * 80)
    
    # Afficher stats
    stats = result.stats
    print(f"\n📊 Statistiques:")
    print(f"   - Total clients: {stats['total_clients']}")
    print(f"   - Scans réussis: {stats['successful_scans']}")
    print(f"   - GOLD détectés: {stats['gold_detected']}")
    print(f"   - GOLD missing: {result.gold_missing_count}")
    
    # Afficher chemin des diagnostics
    if result.gold_missing_count > 0:
        print(f"\n🔍 Fichiers de diagnostic créés:")
        print(f"   - JSONL: {result.gold_missing_diagnostics_path}")
        print(f"   - Markdown: {result.gold_missing_diagnostics_path.replace('.jsonl', '.md')}")
        
        print(f"\n💡 Pour analyser:")
        print(f"   cat {result.gold_missing_diagnostics_path}")
        print(f"   cat {result.gold_missing_diagnostics_path.replace('.jsonl', '.md')}")
    else:
        print("\n✅ Tous les clients ont un GOLD détecté !")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
