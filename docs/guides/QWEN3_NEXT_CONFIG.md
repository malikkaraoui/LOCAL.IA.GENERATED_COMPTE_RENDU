# Configuration optimisée pour qwen3-next:latest

## 🚀 Résolution des erreurs HTTP 404 avec qwen3-next:latest

### 📋 Problème identifié
- **Modèle**: qwen3-next:latest (79.7B paramètres) 
- **Hash**: b2ebb986e4e9
- **Cause**: Timeouts trop courts pour un modèle de cette taille

### ✅ Solutions appliquées

1. **Timeouts augmentés**:
   - API génération: 30s → 600s (10 min)
   - Timeout global: 300s → 900s (15 min) 
   - Vérifications santé: 5s → 15s

2. **Configurations mises à jour**:
   - `qwen3-next:latest` défini comme modèle par défaut
   - Tous les presets pointent vers le nouveau modèle
   - Frontend et backend synchronisés

3. **Outils créés**:
   - `preload_qwen3.py`: Pré-charge le modèle en mémoire
   - `diagnose_ollama.py`: Diagnostic rapide de l'état

### 🔧 Utilisation

```bash
# Pré-charger le modèle (recommandé avant utilisation)
python3 preload_qwen3.py

# Diagnostic rapide
python3 diagnose_ollama.py

# Redémarrer avec nouveaux timeouts
FORCE_RESTART=1 ./scripts/start-all.sh
```

### ⚡ Performance attendue

- **Premier chargement**: 2-5 minutes
- **Réponses ultérieures**: 30-120 secondes selon complexité
- **Mémoire VRAM**: ~8.8 GB
- **Expiration cache**: 15 minutes d'inactivité

### 💡 Conseils d'optimisation

1. **Gardez le modèle chargé**: Utilisez `keep_alive: "15m"` dans les requêtes
2. **Requêtes courtes**: Pour les tests, utilisez `num_predict: 1-5`
3. **Timeout adaptatifs**: Ajustez selon le type de génération
4. **Monitoring**: Surveillez l'état avec `curl -s localhost:11434/api/ps`

### 🆔 Identifiants du modèle

```json
{
  "name": "qwen3-next:latest",
  "digest": "b2ebb986e4e960bb3f2d636472a466b4027939c4d8d9a62fc82bed8ebfd1ae19",
  "family": "qwen3next", 
  "parameter_size": "79.7B",
  "size": 51109829632,
  "size_vram": 8877377024
}
```