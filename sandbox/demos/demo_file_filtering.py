"""
Script de démonstration pour valider le filtrage des fichiers temporaires Office.
"""
import tempfile
from pathlib import Path
from src.rhpro.client_finder import discover_client_documents_recursive, discover_client_documents
from src.utils.file_filters import is_ignored_filename


def demo_file_filtering():
    """Démontre le filtrage des fichiers temporaires Office dans la découverte de documents."""
    
    print("=" * 80)
    print("DÉMONSTRATION : Filtrage des fichiers temporaires Office")
    print("=" * 80)
    print()
    
    # Test unitaire de base
    print("1️⃣ Test unitaire de is_ignored_filename():")
    print("-" * 80)
    test_cases = [
        ("~$Contrat de travail.docx", True),
        (".~lock.docx", True),
        (".DS_Store", True),
        ("Thumbs.db", True),
        ("~WRL0001.tmp", True),
        ("Contrat de travail.docx", False),
        ("rapport.xlsx", False),
        ("data.tmp", False),
    ]
    
    for filename, expected in test_cases:
        result = is_ignored_filename(filename)
        status = "✅" if result == expected else "❌"
        action = "IGNORÉ" if result else "ACCEPTÉ"
        print(f"  {status} {filename:<35} → {action}")
    
    print()
    print("=" * 80)
    print()
    
    # Test d'intégration avec un dossier temporaire
    print("2️⃣ Test d'intégration avec scan de dossier:")
    print("-" * 80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Créer des fichiers de test
        print("Création de fichiers de test...")
        files_created = {
            "normaux": [
                "Contrat de travail.docx",
                "CV - Jean DUPONT.docx",
                "Rapport final.pdf",
                "notes.txt",
            ],
            "temporaires": [
                "~$Contrat de travail.docx",
                "~$CV - Jean DUPONT.docx",
                ".~lock.docx",
                "~WRL0001.tmp",
            ],
            "système": [
                ".DS_Store",
                "Thumbs.db",
            ]
        }
        
        for category, filenames in files_created.items():
            for filename in filenames:
                (tmpdir / filename).write_text(f"Contenu de {filename}")
        
        print(f"  ✅ {len(files_created['normaux'])} fichiers normaux créés")
        print(f"  ✅ {len(files_created['temporaires'])} fichiers temporaires Office créés")
        print(f"  ✅ {len(files_created['système'])} fichiers système créés")
        print()
        
        # Scanner avec discover_client_documents (non récursif)
        print("Scan non-récursif (discover_client_documents):")
        docs = discover_client_documents(tmpdir)
        print(f"  📄 DOCX détectés: {len(docs['docx'])}")
        print(f"  📄 PDF détectés: {len(docs['pdf'])}")
        print(f"  📄 TXT détectés: {len(docs['txt'])}")
        print()
        
        if docs['docx']:
            print("  Fichiers DOCX trouvés:")
            for doc in docs['docx']:
                print(f"    - {doc.name}")
        print()
        
        # Scanner avec discover_client_documents_recursive
        print("Scan récursif (discover_client_documents_recursive):")
        result = discover_client_documents_recursive(tmpdir, max_depth=0)
        
        total_expected = len(files_created['normaux'])
        total_found = result['total_files']
        
        print(f"  📊 Fichiers attendus (normaux): {total_expected}")
        print(f"  📊 Fichiers détectés: {total_found}")
        print()
        
        # Vérifier les stats
        print("  Statistiques par type:")
        for file_type, count in result['stats_by_type'].items():
            print(f"    - {file_type}: {count}")
        print()
        
        # Vérifier qu'aucun fichier temporaire n'est dans les résultats
        all_files = []
        for files_list in result['files'].values():
            all_files.extend([f.name for f in files_list])
        
        print("  Vérification des fichiers exclus:")
        excluded_found = []
        for category in ['temporaires', 'système']:
            for filename in files_created[category]:
                if filename in all_files:
                    excluded_found.append(filename)
                    print(f"    ❌ {filename} ne devrait PAS être présent")
                else:
                    print(f"    ✅ {filename} correctement ignoré")
        
        print()
        print("=" * 80)
        print()
        
        # Résultat final
        if total_found == total_expected and not excluded_found:
            print("🎉 SUCCÈS : Tous les fichiers temporaires et système sont correctement filtrés !")
            return 0
        else:
            print("❌ ÉCHEC : Problème de filtrage détecté")
            if total_found != total_expected:
                print(f"   - Nombre de fichiers incorrect: {total_found} au lieu de {total_expected}")
            if excluded_found:
                print(f"   - Fichiers exclus trouvés: {excluded_found}")
            return 1


if __name__ == "__main__":
    import sys
    sys.exit(demo_file_filtering())
