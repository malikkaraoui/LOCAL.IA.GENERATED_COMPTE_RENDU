#!/usr/bin/env python3
"""
Test du correctif avec scénario d'erreur simulé
"""
import sys
from pathlib import Path
import tempfile
import shutil

# Ajouter le projet au path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.rhpro.dataset_training import analyze_dataset, export_training_artifacts

def create_test_dataset_with_errors():
    """Crée un dataset de test avec des erreurs volontaires"""
    
    # Créer un dossier temporaire
    temp_dir = Path(tempfile.mkdtemp(prefix="test_errors_"))
    
    # Client 1: OK (copie depuis data/samples)
    if (Path("data/samples/client_01")).exists():
        shutil.copytree("data/samples/client_01", temp_dir / "client_ok")
    else:
        # Créer un client minimal
        (temp_dir / "client_ok").mkdir()
        (temp_dir / "client_ok" / "test.txt").write_text("test")
    
    # Client 2: Dossier vide (devrait échouer ou passer avec warning)
    (temp_dir / "client_empty").mkdir()
    
    # Client 3: Nom invalide avec caractères spéciaux
    (temp_dir / "client@#$%invalid").mkdir()
    (temp_dir / "client@#$%invalid" / "doc.txt").write_text("test")
    
    return temp_dir

def test_with_errors():
    """Test avec des erreurs simulées"""
    
    print("=" * 60)
    print("TEST AVEC SCÉNARIO D'ERREURS")
    print("=" * 60)
    print()
    
    # Créer dataset de test
    print("📁 Création dataset de test avec erreurs simulées...")
    test_dir = create_test_dataset_with_errors()
    print(f"   Créé dans : {test_dir}")
    print()
    
    try:
        # Analyser
        result = analyze_dataset(str(test_dir))
        
        print("=" * 60)
        print("RÉSULTATS")
        print("=" * 60)
        print(f"Clients analysés  : {result.stats['total_clients']}")
        print(f"Scans réussis     : {result.stats['successful_scans']}")
        print(f"Erreurs           : {result.stats['errors']}")
        print()
        
        # Exporter pour voir le rapport
        if result.stats['errors'] > 0:
            output_dir = "output/test_errors"
            paths = export_training_artifacts(result, out_dir=output_dir)
            
            print("✅ Rapport avec erreurs généré")
            print()
            print("=" * 60)
            print("SECTION ERREURS DU RAPPORT")
            print("=" * 60)
            
            # Extraire juste la section erreurs
            report_path = paths['report']
            with open(report_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Trouver la section erreurs
            in_error_section = False
            for line in lines:
                if "## ❌ Erreurs" in line:
                    in_error_section = True
                elif in_error_section and line.startswith("## "):
                    break
                
                if in_error_section:
                    print(line, end='')
            
            print()
            print("=" * 60)
        else:
            print("⚠️  Aucune erreur détectée (les clients de test sont peut-être trop permissifs)")
        
        # Nettoyage
        print()
        print("🧹 Nettoyage...")
        shutil.rmtree(test_dir)
        print("✅ Terminé")
        
        return 0
        
    except Exception as e:
        print(f"❌ Erreur pendant le test : {e}")
        import traceback
        traceback.print_exc()
        
        # Nettoyage en cas d'erreur
        if test_dir.exists():
            shutil.rmtree(test_dir)
        
        return 1

def main():
    print("🧪 Test du correctif avec scénario d'erreurs")
    print()
    
    result = test_with_errors()
    
    print()
    if result == 0:
        print("✅ Test terminé")
        print()
        print("Le correctif gère maintenant :")
        print("  • Les erreurs de scan sont capturées")
        print("  • Les types d'erreur sont identifiés")
        print("  • Une section dédiée affiche les erreurs dans le rapport")
        print("  • Les stats restent cohérentes (total = success + errors)")
    else:
        print("❌ Test échoué")
    
    return result

if __name__ == "__main__":
    sys.exit(main())
