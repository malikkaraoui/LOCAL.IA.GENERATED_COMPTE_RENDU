#!/usr/bin/env python3
"""
Script de test pour vérifier la configuration qwen3-next:latest
"""

import json
from core.generate import check_llm_status, ollama_generate


def test_ollama_configuration():
    """Teste la configuration Ollama avec qwen3-next:latest"""
    
    print("🔍 Test de la configuration Ollama")
    print("=" * 50)
    
    # 1. Vérifier la disponibilité du serveur et du modèle
    print("1. Vérification de la disponibilité...")
    result = check_llm_status('http://localhost:11434', 'qwen3-next:latest')
    
    if not result.success:
        print(f"❌ Erreur de connexion: {result.error}")
        return False
    
    print(f"✅ {result.value}")
    
    # 2. Test de génération rapide
    print("\n2. Test de génération (timeout 60s)...")
    gen_result = ollama_generate(
        model='qwen3-next:latest',
        prompt='Répond en une phrase: Tu fonctionnes bien ?',
        host='http://localhost:11434',
        temperature=0.2,
        top_p=0.9,
        timeout=60.0
    )
    
    if not gen_result.success:
        print(f"❌ Erreur de génération: {gen_result.error}")
        if "timeout" in str(gen_result.error).lower():
            print("💡 Le modèle qwen3-next:latest (79.7B) nécessite plus de temps")
            print("   Les applications peuvent augmenter le timeout selon leurs besoins")
        return False
    
    print(f"✅ Génération réussie!")
    print(f"📝 Réponse: {gen_result.value}")
    
    print("\n🎉 Configuration qwen3-next:latest entièrement fonctionnelle!")
    return True


if __name__ == "__main__":
    success = test_ollama_configuration()
    exit(0 if success else 1)