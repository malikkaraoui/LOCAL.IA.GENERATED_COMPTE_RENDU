#!/usr/bin/env python3
"""
Utilitaire pour pré-charger qwen3-next:latest et éviter les timeouts.
"""

import requests
import time
import sys
from datetime import datetime


def preload_qwen3_next():
    """Pré-charge qwen3-next:latest en mémoire avec un prompt minimal"""
    
    print("🔄 Pré-chargement de qwen3-next:latest...")
    print("💡 Ce processus peut prendre 2-5 minutes selon votre système")
    print("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Requête minimale pour charger le modèle
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen3-next:latest",
                "prompt": "Bonjour",
                "stream": False,
                "keep_alive": "15m",  # Garde en mémoire 15 min
                "options": {
                    "num_predict": 5,  # Très peu de tokens
                    "temperature": 0.1
                }
            },
            timeout=600  # 10 minutes max
        )
        
        response.raise_for_status()
        result = response.json()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ Modèle chargé avec succès en {elapsed:.1f}s")
        print(f"📝 Test de réponse: {result.get('response', 'N/A')[:50]}...")
        
        # Vérifier l'état des modèles en mémoire
        ps_response = requests.get("http://localhost:11434/api/ps", timeout=10)
        ps_data = ps_response.json()
        
        active_models = [m.get("name") for m in ps_data.get("models", [])]
        
        if "qwen3-next:latest" in active_models:
            print("✅ qwen3-next:latest est maintenant actif en mémoire")
        else:
            print("⚠️ Le modèle ne semble pas être actif en mémoire")
        
        print(f"🧠 Modèles actifs: {active_models}")
        
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Timeout lors du chargement (>10 min)")
        print("💡 Le modèle est peut-être trop volumineux pour votre système")
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors du chargement: {e}")
        return False


def check_ollama_status():
    """Vérifie que Ollama est accessible"""
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=5)
        response.raise_for_status()
        version_data = response.json()
        print(f"✅ Ollama accessible (v{version_data.get('version', 'unknown')})")
        return True
    except Exception as e:
        print(f"❌ Ollama non accessible: {e}")
        print("💡 Assurez-vous qu'Ollama est démarré: ollama serve")
        return False


def main():
    """Fonction principale"""
    print("🚀 SCRIPT.IA - Utilitaire de pré-chargement qwen3-next:latest")
    print("=" * 60)
    
    # Vérifier Ollama
    if not check_ollama_status():
        sys.exit(1)
    
    # Pré-charger le modèle
    if preload_qwen3_next():
        print("\n🎉 Pré-chargement terminé avec succès!")
        print("💡 Vous pouvez maintenant utiliser l'application normalement")
        print("   Les premières requêtes seront beaucoup plus rapides")
    else:
        print("\n❌ Échec du pré-chargement")
        print("💡 Essayez avec un modèle plus petit (ex: qwen3-vl:2b)")
        sys.exit(1)


if __name__ == "__main__":
    main()