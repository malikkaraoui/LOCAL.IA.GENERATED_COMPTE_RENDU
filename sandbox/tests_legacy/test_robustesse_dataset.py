#!/usr/bin/env python3
"""
Test du correctif de robustesse sur analyze_dataset()
"""
import sys
from pathlib import Path

# Ajouter le projet au path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.rhpro.dataset_training import analyze_dataset

def test_robustesse():
    """Test du correctif de robustesse"""
    
    print("=" * 60)
    print("TEST CORRECTIF ROBUSTESSE - analyze_dataset()")
    print("=" * 60)
    print()
    
    # Dossier test (adapter selon votre environnement)
    test_dir = "CLIENTS/"
    
    if not Path(test_dir).exists():
        print(f"❌ Dossier {test_dir} introuvable")
        print("   Utiliser un autre dossier pour tester")
        return 1
    
    print(f"📁 Analyse de : {test_dir}")
    print()
    
    try:
        # Analyser avec limite à 5 clients pour test rapide
        result = analyze_dataset(test_dir, limit=5)
        
        print("✅ Analyse terminée sans crash !")
        print()
        print("📊 Résultats :")
        print(f"  Clients analysés  : {result.stats['total_clients']}")
        print(f"  Scans réussis     : {result.stats['successful_scans']}")
        print(f"  Erreurs           : {result.stats['errors']}")
        print()
        
        # Afficher les extensions
        if result.stats.get('extensions_distribution'):
            print("📄 Extensions détectées :")
            for ext, count in sorted(result.stats['extensions_distribution'].items()):
                print(f"  {ext} : {count}")
            print()
        
        # Afficher les erreurs si présentes
        if result.stats.get('errors', 0) > 0:
            print("❌ Erreurs détectées :")
            errors_top = result.stats.get('errors_top', [])
            for error_type, count in errors_top:
                print(f"  {error_type} : {count} client(s)")
            print()
            
            # Détail des clients en erreur
            error_clients = [c for c in result.clients if "error" in c]
            if error_clients:
                print("  Détail :")
                for client in error_clients[:3]:
                    print(f"    • {client['folder_name']}")
                    print(f"      Type  : {client.get('error_type', 'N/A')}")
                    print(f"      Message : {client.get('error', 'N/A')[:100]}...")
                if len(error_clients) > 3:
                    print(f"    ... et {len(error_clients) - 3} autres")
            print()
        
        # Validation des critères
        print("=" * 60)
        print("VALIDATION")
        print("=" * 60)
        
        success = True
        
        # Critère 1 : Au moins 1 scan réussi
        if result.stats['successful_scans'] > 0:
            print("✅ Au moins 1 scan réussi")
        else:
            print("❌ Aucun scan réussi")
            success = False
        
        # Critère 2 : Extensions détectées
        if result.stats.get('extensions_distribution'):
            print(f"✅ Extensions détectées ({len(result.stats['extensions_distribution'])})")
        else:
            print("⚠️  Aucune extension détectée")
        
        # Critère 3 : Stats cohérentes
        total = result.stats['total_clients']
        successful = result.stats['successful_scans']
        errors = result.stats['errors']
        
        if total == successful + errors:
            print(f"✅ Stats cohérentes ({total} = {successful} + {errors})")
        else:
            print(f"❌ Stats incohérentes ({total} ≠ {successful} + {errors})")
            success = False
        
        # Critère 4 : Erreurs documentées si présentes
        if errors > 0:
            if result.stats.get('errors_top'):
                print(f"✅ Erreurs documentées (top {len(result.stats['errors_top'])})")
            else:
                print("⚠️  Erreurs présentes mais non documentées")
        
        print()
        
        if success:
            print("✅ Tous les critères sont validés !")
            return 0
        else:
            print("❌ Certains critères ne sont pas validés")
            return 1
        
    except Exception as e:
        print(f"❌ Erreur pendant l'analyse : {e}")
        import traceback
        traceback.print_exc()
        return 1

def main():
    print("🧪 Test du correctif de robustesse")
    print()
    
    result = test_robustesse()
    
    print()
    if result == 0:
        print("🎉 Test réussi !")
        print()
        print("Le correctif permet maintenant :")
        print("  • Gestion robuste des variations de schéma scan_result")
        print("  • Capture et documentation des erreurs")
        print("  • Affichage des erreurs dans le rapport")
        print("  • Stats cohérentes (total = successful + errors)")
    else:
        print("⚠️  Test échoué ou incomplet")
        print()
        print("Actions recommandées :")
        print("  • Vérifier les messages d'erreur ci-dessus")
        print("  • S'assurer que le dossier test contient des clients valides")
        print("  • Relancer avec un autre dossier si nécessaire")
    
    return result

if __name__ == "__main__":
    sys.exit(main())
