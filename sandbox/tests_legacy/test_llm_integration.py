#!/usr/bin/env python3
"""
Test de l'intégration LLM end-to-end
Vérifie que l'objet llm circule correctement du frontend au backend
"""
import requests
import json
import time

def test_ollama_health():
    """Test 1: Vérifier que Ollama est disponible"""
    print("\n🔍 Test 1: Vérification Ollama...")
    try:
        r = requests.get("http://localhost:11434/api/version", timeout=5)
        r.raise_for_status()
        version = r.json().get("version")
        print(f"✅ Ollama disponible: version {version}")
        return True
    except Exception as e:
        print(f"❌ Ollama indisponible: {e}")
        return False

def test_backend_health():
    """Test 2: Vérifier que le backend API est disponible"""
    print("\n🔍 Test 2: Vérification Backend...")
    try:
        r = requests.get("http://localhost:8000/api/health", timeout=5)
        r.raise_for_status()
        status = r.json().get("status")
        print(f"✅ Backend disponible: {status}")
        return True
    except Exception as e:
        print(f"❌ Backend indisponible: {e}")
        return False

def test_ollama_models():
    """Test 3: Vérifier les modèles disponibles"""
    print("\n🔍 Test 3: Modèles Ollama disponibles...")
    try:
        r = requests.get("http://localhost:8000/api/ollama/models", timeout=10)
        r.raise_for_status()
        data = r.json()
        models = data.get("models", [])
        print(f"✅ Modèles disponibles via backend: {len(models)}")
        for model in models:
            print(f"  - {model.get('name')} ({model.get('size', 0) / 1e9:.1f} GB)")
        
        # Vérifier qwen3-next dans /api/ps (modèles en mémoire)
        r2 = requests.get("http://localhost:11434/api/ps", timeout=5)
        if r2.ok:
            loaded = r2.json().get("models", [])
            print(f"\n📦 Modèles chargés en mémoire: {len(loaded)}")
            for model in loaded:
                print(f"  - {model.get('name')} ({model.get('size', 0) / 1e9:.1f} GB VRAM)")
        
        return True
    except Exception as e:
        print(f"❌ Erreur modèles: {e}")
        return False

def test_llm_config_payload():
    """Test 4: Tester le payload LLM unifié"""
    print("\n🔍 Test 4: Test payload LLM unifié...")
    
    # Simuler une requête frontend avec objet llm
    payload = {
        "client_name": "ALI Mohammed",
        "extract_method": "auto",
        "template_name": "TEMPLATE_SIMPLE_BASE1.docx",
        "llm": {
            "provider": "ollama",
            "base_url": "http://localhost:11434",
            "model": "qwen3-next:latest",
            "temperature": 0.2,
            "max_tokens": 4096,
            "top_p": 0.9,
            "timeout": 900.0
        },
        "name": "Mohammed",
        "surname": "Ali",
        "civility": "Monsieur",
        "avs_number": "756.1234.5678.90",
        "location_city": "Genève",
        "clients_root": "./CLIENTS",
        "output_dir": "./output"
    }
    
    try:
        print(f"📤 Envoi requête avec llm.model={payload['llm']['model']}")
        r = requests.post(
            "http://localhost:8000/api/reports",
            json=payload,
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        job_id = data.get("job_id")
        print(f"✅ Job créé: {job_id}")
        
        # Attendre un peu et vérifier le statut
        time.sleep(2)
        r2 = requests.get(f"http://localhost:8000/api/reports/{job_id}", timeout=5)
        if r2.ok:
            status_data = r2.json()
            print(f"📊 Statut job: {status_data.get('status')}")
            if status_data.get('logs'):
                print(f"📝 Logs récents:")
                for log in status_data['logs'][-5:]:
                    print(f"  {log}")
        
        return True
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP: {e}")
        if e.response:
            print(f"   Status: {e.response.status_code}")
            print(f"   Détail: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    print("=" * 60)
    print("🧪 Test d'intégration LLM unifié")
    print("=" * 60)
    
    results = []
    
    # Tests
    results.append(("Ollama Health", test_ollama_health()))
    results.append(("Backend Health", test_backend_health()))
    results.append(("Modèles disponibles", test_ollama_models()))
    results.append(("Payload LLM unifié", test_llm_config_payload()))
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    print(f"\n🎯 Score: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 Tous les tests sont passés!")
    else:
        print("\n⚠️  Certains tests ont échoué")

if __name__ == "__main__":
    main()
