# 🧭 Accès au Menu de Navigation

## ⚠️ IMPORTANT : Quelle application lancer ?

### ✅ BONNE APPLICATION (avec menu)
```bash
streamlit run streamlit_app.py --server.port 8501
```
**URL:** http://localhost:8501

**Contient:**
- 🧭 Menu de navigation latéral
- Générateur
- Batch Parser RH-Pro
- Validation Batch
- Rapport individuel
- Entraînement
- Training & Test

### ❌ MAUVAISE APPLICATION (sans menu)
```bash
streamlit run pages_streamlit/training_and_test.py --server.port 8501
```
**Problème:** Page isolée SANS menu de navigation

---

## 🚀 Démarrage Automatique

### Script Complet (RECOMMANDÉ)
```bash
./scripts/start-all.sh
```

Ce script démarre automatiquement :
1. Redis
2. Ollama
3. Backend FastAPI (port 8000)
4. RQ Workers
5. Frontend React (port 5173)
6. **Streamlit avec menu** (port 8501)

### Démarrage Manuel Streamlit
Si vous voulez lancer uniquement Streamlit avec le menu :
```bash
cd /Users/malik/Documents/Espace\ de\ travail/SCRIPT.IA
.venv/bin/streamlit run streamlit_app.py --server.port 8501
```

---

## 📍 URLs d'Accès

| Service | URL | Description |
|---------|-----|-------------|
| **Streamlit (MENU)** | http://localhost:8501 | Interface principale avec navigation |
| Frontend React | http://localhost:5173 | Interface web moderne |
| Backend API | http://localhost:8000/docs | Documentation API interactive |

---

## 🔍 Vérifier les Services Actifs

```bash
# Vérifier tous les ports
lsof -ti:8000,8501,5173

# Vérifier Streamlit spécifiquement
lsof -ti:8501
```

---

## 🛑 Arrêter les Services

```bash
# Arrêter tous les services
./scripts/stop.sh

# Arrêter uniquement Streamlit
lsof -ti:8501 | xargs kill -9
```

---

## 🔧 Problèmes Courants

### ❌ "Je n'ai pas le menu !"
**Cause:** Vous avez lancé `pages_streamlit/training_and_test.py` au lieu de `streamlit_app.py`

**Solution:**
```bash
# Arrêter
lsof -ti:8501 | xargs kill -9

# Relancer la BONNE application
.venv/bin/streamlit run streamlit_app.py --server.port 8501
```

### ❌ Port 8501 déjà utilisé
```bash
# Tuer le processus existant
lsof -ti:8501 | xargs kill -9

# Relancer
.venv/bin/streamlit run streamlit_app.py --server.port 8501
```

---

## 📝 Structure des Applications Streamlit

```
SCRIPT.IA/
├── streamlit_app.py           ← ✅ APPLICATION PRINCIPALE (avec menu)
└── pages_streamlit/
    ├── training_and_test.py   ← ❌ Page isolée (sans menu)
    ├── batch_parser.py
    └── validation_batch.py
```

**Règle:** Toujours lancer `streamlit_app.py` pour avoir le menu complet.

---

## ✅ Vérification Rapide

Après démarrage, ouvrez http://localhost:8501 et vérifiez que vous voyez :
- ✅ Barre latérale "🧭 Navigation" à gauche
- ✅ Liste de pages : Générateur, Batch Parser, etc.
- ✅ Possibilité de naviguer entre les pages

Si vous ne voyez pas le menu → Vous êtes sur la mauvaise application !
