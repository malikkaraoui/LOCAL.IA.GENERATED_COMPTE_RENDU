#!/usr/bin/env python3
"""
Test rapide du support .msg
"""
import sys
from pathlib import Path

# Ajouter le projet au path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_msg_extractor():
    """Test 1: Vérifier que le module msg_extractor est disponible"""
    print("=" * 60)
    print("TEST 1: Module msg_extractor")
    print("=" * 60)
    try:
        from core.extractors.msg_extractor import MSG_SUPPORT_AVAILABLE, extract_msg_to_text
        print(f"✅ Module importé avec succès")
        print(f"   MSG_SUPPORT_AVAILABLE = {MSG_SUPPORT_AVAILABLE}")
        if MSG_SUPPORT_AVAILABLE:
            print(f"   extract-msg est installé")
        else:
            print(f"   ⚠️  extract-msg n'est pas installé")
        return MSG_SUPPORT_AVAILABLE
    except Exception as e:
        print(f"❌ Erreur import: {e}")
        return False

def test_scanner():
    """Test 2: Vérifier que le scanner inclut les .msg par défaut"""
    print("\n" + "=" * 60)
    print("TEST 2: Scanner avec index_msg par défaut")
    print("=" * 60)
    try:
        from src.rhpro.client_scanner import scan_client_folder, DOCUMENT_EXTENSIONS
        print(f"✅ Scanner importé avec succès")
        print(f"   DOCUMENT_EXTENSIONS = {DOCUMENT_EXTENSIONS}")
        
        # Vérifier que .msg est dans les extensions
        if ".msg" in DOCUMENT_EXTENSIONS:
            print(f"   ✅ .msg est dans DOCUMENT_EXTENSIONS")
        else:
            print(f"   ❌ .msg n'est pas dans DOCUMENT_EXTENSIONS")
            return False
            
        # Vérifier la signature de scan_client_folder
        import inspect
        sig = inspect.signature(scan_client_folder)
        index_msg_param = sig.parameters.get('index_msg')
        if index_msg_param:
            default_value = index_msg_param.default
            print(f"   Paramètre index_msg par défaut: {default_value}")
            if default_value is True:
                print(f"   ✅ index_msg=True par défaut")
                return True
            else:
                print(f"   ⚠️  index_msg={default_value} par défaut (devrait être True)")
                return False
        else:
            print(f"   ❌ Paramètre index_msg non trouvé")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_extract_sources():
    """Test 3: Vérifier que extract_sources.py supporte .msg"""
    print("\n" + "=" * 60)
    print("TEST 3: extract_sources.py")
    print("=" * 60)
    try:
        # Importer depuis CLIENTS/
        sys.path.insert(0, str(project_root / "CLIENTS"))
        import extract_sources
        
        print(f"✅ extract_sources importé")
        print(f"   SUPPORTED_DIRECT = {extract_sources.SUPPORTED_DIRECT}")
        
        if ".msg" in extract_sources.SUPPORTED_DIRECT:
            print(f"   ✅ .msg est dans SUPPORTED_DIRECT")
        else:
            print(f"   ❌ .msg n'est pas dans SUPPORTED_DIRECT")
            return False
            
        print(f"   MSG_SUPPORT_AVAILABLE = {extract_sources.MSG_SUPPORT_AVAILABLE}")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_core_extract():
    """Test 4: Vérifier que core.extract supporte .msg"""
    print("\n" + "=" * 60)
    print("TEST 4: core.extract")
    print("=" * 60)
    try:
        from core.extract import extract_sources, SUPPORTED_MSG
        print(f"✅ core.extract importé")
        print(f"   SUPPORTED_MSG = {SUPPORTED_MSG}")
        
        if ".msg" in SUPPORTED_MSG:
            print(f"   ✅ .msg est dans SUPPORTED_MSG")
            return True
        else:
            print(f"   ❌ .msg n'est pas dans SUPPORTED_MSG")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🧪 Test du support .msg dans SCRIPT.IA")
    print()
    
    results = {
        "msg_extractor": test_msg_extractor(),
        "scanner": test_scanner(),
        "extract_sources": test_extract_sources(),
        "core_extract": test_core_extract(),
    }
    
    print("\n" + "=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    print()
    if all_passed:
        print("✅ Tous les tests sont passés !")
        print()
        print("Les fichiers .msg seront maintenant :")
        print("  • Détectés par le scanner")
        print("  • Comptés dans les statistiques")
        print("  • Extraits pendant le RAG")
        print("  • Énumérés au même titre que PDF/DOCX")
        return 0
    else:
        print("❌ Certains tests ont échoué")
        print()
        print("Actions recommandées :")
        if not results["msg_extractor"]:
            print("  • Installer extract-msg : pip install extract-msg>=0.48.0")
        return 1

if __name__ == "__main__":
    sys.exit(main())
