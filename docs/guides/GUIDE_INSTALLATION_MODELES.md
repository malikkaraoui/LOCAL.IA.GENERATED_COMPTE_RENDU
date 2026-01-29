# 🤖 Guide d'installation des modèles LLM

## ❌ Problème : "Modèle introuvable sur Ollama"

Vous voyez cette erreur quand vous essayez d'utiliser un modèle qui n'est **pas téléchargé** dans Ollama.

### Diagnostic rapide

```bash
# 1. Vérifier les modèles disponibles
curl http://localhost:11434/api/tags | python3 -m json.tool

# 2. Vérifier les modèles en mémoire
curl http://localhost:11434/api/ps | python3 -m json.tool
```

## ✅ Solutions

### Option 1 : Télécharger le modèle manquant

```bash
# Télécharger mistral (7B, ~4GB)
ollama pull mistral:latest

# Télécharger qwen3-next (80B, ~50GB) - ATTENTION: très gros!
ollama pull qwen3-next:latest

# Télécharger qwen2.5 (14B, ~9GB)
ollama pull qwen2.5:14b

# Télécharger llama3.1 (8B, ~5GB)
ollama pull llama3.1:8b
```

**Temps de téléchargement:**
- 7B models (~4GB): 5-15 minutes
- 14B models (~9GB): 10-30 minutes  
- 80B models (~50GB): 1-3 heures

### Option 2 : Utiliser un modèle déjà disponible

Modifiez le frontend pour utiliser un modèle déjà téléchargé :

**Frontend:** [frontend/src/pages/ClientSelection.jsx](frontend/src/pages/ClientSelection.jsx)
```javascript
// Ligne 38
const [llmModel, setLlmModel] = useState('llama3.1:8b'); // ← Changez ici
```

**Backend (optionnel):** [backend/config.py](backend/config.py)
```python
# Ligne 50
OLLAMA_MODEL: str = "llama3.1:8b"  # ← Changez ici
```

### Option 3 : Précharger un modèle au démarrage

Créez un script de préchargement :

```python
#!/usr/bin/env python3
"""Précharge un modèle Ollama en mémoire"""
import requests
import time

MODEL = "llama3.1:8b"
URL = "http://localhost:11434"

print(f"🔄 Préchargement de {MODEL}...")
start = time.time()

response = requests.post(
    f"{URL}/api/generate",
    json={
        "model": MODEL,
        "prompt": "Hello",
        "stream": False
    },
    timeout=300
)

elapsed = time.time() - start
print(f"✅ Modèle chargé en {elapsed:.1f}s")
```

## 📋 Modèles recommandés par taille

### Petit (2-8B) - Rapide, moins précis
- **llama3.1:8b** (5GB) - Bon équilibre vitesse/qualité ✅
- **qwen3-vl:2b** (2GB) - Très rapide, vision
- **phi3:mini** (2GB) - Ultra rapide

### Moyen (14-32B) - Équilibre
- **qwen2.5:14b** (9GB) - Excellent pour français
- **mixtral:8x7b** (26GB) - Très bon sur multi-tâches

### Grand (70B+) - Lent, très précis
- **qwen3-next:latest** (50GB) - Top qualité français ⭐
- **llama3.1:70b** (40GB) - Excellent pour anglais

## 🔧 Configuration selon usage

### Développement local
```python
# Rapide pour tester
model = "llama3.1:8b"
timeout = 60.0
```

### Production (qualité maximale)
```python
# Précis mais lent
model = "qwen3-next:latest"
timeout = 900.0
```

### Production (équilibre)
```python
# Bon compromis
model = "qwen2.5:14b"
timeout = 300.0
```

## 🐛 Résolution de problèmes

### "Modèle introuvable" alors qu'il est téléchargé

**Cause:** Le modèle existe dans `/api/tags` mais pas en mémoire (`/api/ps`)

**Solution:** Précharger le modèle :
```bash
python3 preload_qwen3.py  # ou votre modèle
```

### "Timeout après 900s"

**Cause:** Le modèle est trop gros pour le timeout configuré

**Solutions:**
1. Augmenter le timeout dans `backend/config.py`:
   ```python
   OLLAMA_TIMEOUT: int = 1800  # 30 minutes
   ```

2. Utiliser un modèle plus petit

3. Passer en mode streaming (non implémenté actuellement)

### "Service Ollama indisponible"

**Cause:** Ollama n'est pas démarré

**Solution:**
```bash
# Vérifier Ollama
curl http://localhost:11434/api/version

# Si erreur, démarrer Ollama
ollama serve
```

### Modèle téléchargé mais pas visible dans l'UI

**Cause:** Le frontend charge la liste depuis le backend qui utilise `/api/tags`

**Solution:**
```bash
# Vérifier que le backend voit le modèle
curl http://localhost:8000/api/ollama/models

# Si vide, redémarrer le backend
pkill -f "uvicorn backend.main"
cd /path/to/SCRIPT.IA
./start_all.sh
```

## 📊 Comparaison des modèles disponibles

| Modèle | Taille | VRAM | Vitesse | Qualité FR | Recommandé |
|--------|--------|------|---------|------------|------------|
| llama3.1:8b | 5GB | 6GB | ⚡⚡⚡ | ⭐⭐⭐ | ✅ Dev |
| qwen2.5:14b | 9GB | 10GB | ⚡⚡ | ⭐⭐⭐⭐ | ✅ Prod |
| qwen3-next | 50GB | 52GB | ⚡ | ⭐⭐⭐⭐⭐ | ✅ Premium |
| gpt-oss | 14GB | 15GB | ⚡⚡ | ⭐⭐⭐ | - |
| mistral | 4GB | 5GB | ⚡⚡⚡ | ⭐⭐⭐ | - |

## 🚀 Script d'installation rapide

```bash
#!/bin/bash
# install_models.sh - Installe les modèles essentiels

echo "📦 Installation des modèles LLM..."

# Modèle léger pour dev
echo "🔄 1/3 - llama3.1:8b (dev)"
ollama pull llama3.1:8b

# Modèle moyen pour prod
echo "🔄 2/3 - qwen2.5:14b (prod)"
ollama pull qwen2.5:14b

# Modèle premium (optionnel)
read -p "Installer qwen3-next (50GB, 1-3h)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 3/3 - qwen3-next:latest (premium)"
    ollama pull qwen3-next:latest
fi

echo "✅ Installation terminée!"
echo ""
echo "Modèles disponibles:"
curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    print(f\"  - {m['name']} ({m.get('size', 0) / 1e9:.1f} GB)\")
"
```

## 📚 Ressources

- [Ollama Model Library](https://ollama.com/library)
- [Qwen Models](https://huggingface.co/Qwen)
- [Llama Models](https://huggingface.co/meta-llama)
- [Documentation Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md)

## ✅ Checklist avant génération

- [ ] Ollama démarré: `curl http://localhost:11434/api/version`
- [ ] Modèle téléchargé: `curl http://localhost:11434/api/tags`
- [ ] Backend actif: `curl http://localhost:8000/api/health`
- [ ] Worker actif: `ps aux | grep start_worker`
- [ ] Modèle sélectionné dans l'UI correspond à un modèle disponible

---

**Dernière mise à jour:** 2025-12-30
