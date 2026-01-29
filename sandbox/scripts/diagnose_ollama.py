#!/usr/bin/env python3
"""
Script de diagnostic rapide pour Ollama et qwen3-next:latest
"""

import requests
import json
from datetime import datetime


def diagnose_ollama():
    """Diagnostic complet d'Ollama"""
    
    print("🔍 DIAGNOSTIC OLLAMA - qwen3-next:latest")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 1. Version Ollama
        print("1️⃣ Version Ollama:")
        version_resp = requests.get("http://localhost:11434/api/version", timeout=5)
        version_data = version_resp.json()
        print(f"   ✅ Version: {version_data.get('version', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Erreur version: {e}")
        return
    
    try:
        # 2. Modèles disponibles
        print("\n2️⃣ Modèles disponibles:")
        tags_resp = requests.get("http://localhost:11434/api/tags", timeout=10)
        tags_data = tags_resp.json()
        
        models = tags_data.get("models", [])
        print(f"   📦 Total: {len(models)} modèles")
        
        qwen_found = False
        for model in models:
            name = model.get("name", "unknown")
            size_gb = model.get("size", 0) / (1024**3)
            if "qwen" in name.lower():
                print(f"   🧠 {name} ({size_gb:.1f} GB)")
                if name == "qwen3-next:latest":
                    qwen_found = True
            
        if not qwen_found:
            print("   ⚠️ qwen3-next:latest non trouvé!")
        else:
            print("   ✅ qwen3-next:latest trouvé")
            
    except Exception as e:
        print(f"   ❌ Erreur modèles: {e}")
        return
    
    try:
        # 3. Modèles en mémoire
        print("\n3️⃣ Modèles en mémoire:")
        ps_resp = requests.get("http://localhost:11434/api/ps", timeout=5)
        ps_data = ps_resp.json()
        
        active_models = ps_data.get("models", [])
        if not active_models:
            print("   📭 Aucun modèle en mémoire")
        else:
            for model in active_models:
                name = model.get("name", "unknown")
                vram_gb = model.get("size_vram", 0) / (1024**3)
                expires = model.get("expires_at", "unknown")
                print(f"   🧠 {name} ({vram_gb:.1f} GB VRAM)")
                if expires != "unknown":
                    print(f"      ⏰ Expire: {expires}")
                    
    except Exception as e:
        print(f"   ❌ Erreur mémoire: {e}")
    
    try:
        # 4. Test de connectivité qwen3-next
        print("\n4️⃣ Test de connectivité qwen3-next:")
        
        # Test rapide avec timeout court
        test_resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3-next:latest",
                "prompt": "Test",
                "stream": False,
                "options": {"num_predict": 1}
            },
            timeout=30  # Test rapide
        )
        
        if test_resp.status_code == 200:
            print("   ✅ qwen3-next:latest répond (modèle chargé)")
        else:
            print(f"   ⚠️ Code de réponse: {test_resp.status_code}")
            
    except requests.exceptions.Timeout:
        print("   ⏳ Timeout 30s - modèle probablement en cours de chargement")
    except Exception as e:
        print(f"   ❌ Erreur test: {e}")
    
    print("\n" + "="*50)
    print("💡 Conseils:")
    print("   - Si le modèle n'est pas en mémoire, utilisez: python3 preload_qwen3.py")
    print("   - Les premières requêtes peuvent prendre 2-5 minutes")
    print("   - Augmentez les timeouts pour les gros modèles")


if __name__ == "__main__":
    diagnose_ollama()