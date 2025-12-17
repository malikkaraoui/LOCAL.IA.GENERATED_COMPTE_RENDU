# SCRIPT.IA – Générateur de Rapports Automatique 🚀

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=white)
![Version](https://img.shields.io/badge/Version-2.0.0-0A0A0A)
![Status](https://img.shields.io/badge/LLM-Ollama-brightgreen)

Système complet de génération automatique de rapports pour clients, utilisant l'IA locale (Ollama) pour créer des documents professionnels au format DOCX.

## 🎯 Démarrage Rapide - UN CLIC

### Démarrer tous les services

```bash
./scripts/start-all.sh
```

Ce script unique lance automatiquement :
- ✅ Vérification de Redis et Ollama
- ✅ Worker RQ pour le traitement en arrière-plan
- ✅ Backend FastAPI (API REST)
- ✅ Frontend React (interface utilisateur)
- ✅ Ouverture du navigateur sur http://localhost:5173

### Arrêter tous les services

```bash
./scripts/stop.sh
```

## 📱 Accès aux Services

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | Interface utilisateur React |
| **Backend** | http://localhost:8000/api/health | API REST FastAPI |
| **API Docs** | http://localhost:8000/api/docs | Documentation Swagger interactive |
| **Login** | admin / admin123 | Identifiants de test |

## 🔄 Workflow de Génération - UN CLIC

1. **Ouvrez le navigateur** : http://localhost:5173
2. **Sélectionnez un client** : Choisissez dans la liste déroulante
3. **Cliquez sur "Générer le Rapport"** : Un seul clic suffit !
4. **Le système exécute automatiquement** :
   - 📂 Extraction des données depuis les fichiers .msg et documents
   - 🤖 Génération de contenu par l'IA (Mistral/LLaMA)
   - 📝 Remplissage du template DOCX
   - 💾 Sauvegarde du rapport final

5. **Téléchargez le DOCX** : Cliquez sur "Télécharger" quand le statut est "completed"

## 🛠️ Architecture du Système

```
┌─────────────────┐
│  Frontend React │  ← Interface utilisateur (port 5173)
│   (Vite + TS)   │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Backend API    │  ← Orchestrateur (port 8000)
│   (FastAPI)     │
└────────┬────────┘
         │ Redis Queue
         ▼
┌─────────────────┐
│  Worker RQ      │  ← Traitement asynchrone
│                 │
│  1. Extraction  │──► extract_sources.py (68KB de données)
│  2. Génération  │──► Ollama LLM (~1m35s avec Mistral)
│  3. Rendu DOCX  │──► python-docx (37KB final)
│  4. Export PDF  │──► docx2pdf (optionnel)
│                 │
└─────────────────┘
```

## 📦 Prérequis

### Services Requis

1. **Redis** (file d'attente de tâches)
   ```bash
   brew install redis
   brew services start redis
   ```

2. **Ollama** (modèles LLM locaux)
   ```bash
   brew install ollama
   ollama serve
   ollama pull mistral  # ou llama3.1
   ```

3. **Node.js** (frontend)
   ```bash
   brew install node
   ```

4. **Python 3.13+** (backend)
   ```bash
   brew install python@3.13
   ```

### Installation des Dépendances

```bash
# Backend Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend Node
cd frontend
npm install
```

## 📊 Suivi de l'Exécution

### Logs en Temps Réel

```bash
# Worker (traitement des tâches)
tail -f /tmp/worker.log

# Backend (API)
tail -f /tmp/backend.log

# Frontend (interface)
tail -f /tmp/frontend.log
```

### Vérification de l'État

```bash
# Health check backend
curl http://localhost:8000/api/health

# Liste des clients disponibles
curl http://localhost:8000/api/clients

# Statut d'un rapport
curl http://localhost:8000/api/reports/{report_id}/status
```

## 🔐 Authentification JWT

Le système utilise JWT pour sécuriser l'API :

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Réponse
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}

# Utilisation du token
curl http://localhost:8000/api/reports \
  -H "Authorization: Bearer eyJhbGc..."
```

### Utilisateurs de Test

| Username | Password | Rôle |
|----------|----------|------|
| admin | admin123 | Administrateur (tous droits) |
| user | user123 | Utilisateur (lecture seule) |

## 📝 Structure des Rapports

### Template DOCX

Le fichier template se trouve dans :
```
CLIENTS/templates/template_rapport.docx
```

### Champs Dynamiques

Les marqueurs suivants sont remplacés automatiquement :

- `{{nom_prenom}}` - Nom complet du client
- `{{date_bilan}}` - Date du bilan
- `{{competences_transferables}}` - Liste des compétences
- `{{projet_professionnel}}` - Description du projet
- `{{plan_action}}` - Plan d'action détaillé
- ... et 20+ autres champs

### Sources de Données

Le système extrait automatiquement depuis :
- 📧 Fichiers .msg (emails Outlook)
- 📄 Documents Word (.docx)
- 📊 PDFs de tests psychométriques
- 📑 Bulletins de salaire
- 🎓 Diplômes et certificats

## 🧪 Tests

### Lancer les Tests Unitaires

```bash
# Installation des dépendances de test
pip install -r tests/requirements.txt

# Exécution avec couverture
pytest tests/ -v --cov=backend --cov-report=term-missing

# Tests spécifiques
pytest tests/test_api.py::TestReportsRoutes::test_create_report -v
```

### Tests Manuels via Swagger

1. Ouvrez http://localhost:8000/api/docs
2. Testez les endpoints interactivement
3. Utilisez "Authorize" avec un token JWT

## 🐛 Dépannage

### Redis n'est pas accessible

```bash
# Vérifier Redis
redis-cli ping  # Devrait répondre "PONG"

# Redémarrer Redis
brew services restart redis
```

### Ollama ne répond pas

```bash
# Vérifier Ollama
curl http://localhost:11434/api/version

# Relancer Ollama
ollama serve &

# Vérifier les modèles
ollama list
```

### Worker ne traite pas les tâches

```bash
# Vérifier les logs
tail -f /tmp/worker.log

# Vérifier la queue Redis
redis-cli
> LLEN rq:queue:default
> LRANGE rq:queue:default 0 -1

# Redémarrer le worker
pkill -f start_worker.py
.venv/bin/python scripts/start_worker.py &
```

### Frontend ne se connecte pas au backend

1. Vérifiez que le backend tourne : `curl http://localhost:8000/api/health`
2. Vérifiez les CORS dans `backend/core/config.py`
3. Inspectez la console navigateur (F12)

## 🌐 Déploiement Windows

Consultez le guide complet : [docs/WINDOWS_DEPLOYMENT.md](docs/WINDOWS_DEPLOYMENT.md)

Résumé :
- Installation avec `winget` et PowerShell
- Redis via WSL2 ou Memurai
- Services Windows avec NSSM
- Scripts PowerShell automatisés

## 📊 Performance

### Temps de Génération Typiques

| Étape | Durée | Détails |
|-------|-------|---------|
| Extraction | ~2-5s | Lecture fichiers .msg + PDFs |
| Génération LLM | ~1m30s | Mistral 7B (varie selon modèle) |
| Rendu DOCX | ~1-2s | python-docx |
| **Total** | **~2min** | Pour un rapport complet |

### Optimisations

- **Modèle plus rapide** : `ollama pull llama3.1:8b` (30% plus rapide)
- **GPU** : Ollama utilise automatiquement Metal/CUDA
- **Cache Redis** : Réutilise les extractions existantes

## 🔧 Configuration Avancée

### Variables d'Environnement

Créez `.env` à la racine :

```env
# API
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=mistral:latest

# JWT
SECRET_KEY=votre-clé-secrète-changez-moi
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Logging
LOG_LEVEL=INFO
```

### Personnalisation du Template

1. Modifiez `CLIENTS/templates/template_rapport.docx`
2. Ajoutez vos propres marqueurs `{{nouveau_champ}}`
3. Mettez à jour `CLIENTS/generate_fields.py` pour générer le contenu

## 📚 Documentation Complète

- **API Backend** : http://localhost:8000/api/docs (Swagger)
- **Tests** : [tests/README.md](tests/README.md)
- **Windows** : [docs/WINDOWS_DEPLOYMENT.md](docs/WINDOWS_DEPLOYMENT.md)

## 🤝 Support

Pour toute question ou problème :
1. Consultez les logs : `tail -f /tmp/*.log`
2. Vérifiez les services : `./scripts/start-all.sh`
3. Testez l'API : http://localhost:8000/api/docs

## 📄 Licence

Projet interne - Tous droits réservés
