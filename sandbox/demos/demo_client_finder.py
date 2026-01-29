#!/usr/bin/env python3
"""
Demo Client Finder — CLI pour rechercher des clients par nom

Usage:
    python demo_client_finder.py /path/to/dataset ARIFI
    python demo_client_finder.py /path/to/dataset "arifi elodie"
"""
import argparse
import sys
from pathlib import Path

# Ajouter src/ au path pour les imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rhpro.client_finder import find_client_folders, find_client_folder, format_search_results, discover_client_documents


def main():
    parser = argparse.ArgumentParser(
        description="Rechercher des dossiers clients RH-Pro par nom",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_client_finder.py data/samples client_02
  python demo_client_finder.py /path/to/dataset ARIFI
  python demo_client_finder.py /path/to/dataset "karaoui malik"
  python demo_client_finder.py data/samples --list-all
        """
    )
    
    parser.add_argument(
        "root_dir",
        help="Dossier racine contenant les dossiers clients"
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="Nom du client à rechercher (optionnel si --list-all)"
    )
    
    parser.add_argument(
        "--list-all",
        action="store_true",
        help="Lister tous les dossiers clients sans filtrage"
    )
    
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.3,
        help="Score minimum pour inclure un résultat (défaut: 0.3)"
    )
    
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Nombre max de résultats à afficher (défaut: 10)"
    )
    
    parser.add_argument(
        "--show-docs",
        action="store_true",
        help="Afficher les documents trouvés dans chaque dossier"
    )
    
    args = parser.parse_args()
    
    # Validation
    root_path = Path(args.root_dir)
    if not root_path.exists():
        print(f"❌ Erreur: dossier racine introuvable: {args.root_dir}")
        sys.exit(1)
    
    if not args.list_all and not args.query:
        print("❌ Erreur: fournir un terme de recherche ou utiliser --list-all")
        parser.print_help()
        sys.exit(1)
    
    # Recherche
    print(f"📂 Dataset: {args.root_dir}")
    print()
    
    try:
        if args.list_all:
            # Lister tous les dossiers
            results = find_client_folders(args.root_dir)
            print(f"📋 Liste complète ({len(results)} dossiers):")
            print()
        else:
            # Recherche avec query
            results = find_client_folders(args.root_dir, args.query, args.min_score)
        
        # Afficher les résultats
        print(format_search_results(results, args.max_results))
        print()
        
        # Afficher les documents si demandé
        if args.show_docs and results:
            print("=" * 60)
            print("📄 DOCUMENTS PAR DOSSIER")
            print("=" * 60)
            
            for result in results[:args.max_results]:
                folder_path = result['path']
                folder_name = result['name']
                
                try:
                    docs = discover_client_documents(folder_path)
                    
                    total_docs = len(docs['docx']) + len(docs['pdf']) + len(docs['txt']) + len(docs['audio'])
                    
                    if total_docs > 0:
                        print(f"\n📁 {folder_name}")
                        if docs['docx']:
                            print(f"  📄 DOCX: {len(docs['docx'])}")
                            for d in docs['docx'][:3]:
                                print(f"     • {d.name}")
                        if docs['pdf']:
                            print(f"  📕 PDF: {len(docs['pdf'])}")
                        if docs['txt']:
                            print(f"  📝 TXT: {len(docs['txt'])}")
                        if docs['audio']:
                            print(f"  🎤 Audio: {len(docs['audio'])}")
                    else:
                        print(f"\n📁 {folder_name} (vide)")
                
                except Exception as e:
                    print(f"\n📁 {folder_name} (erreur: {e})")
            
            print()
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
