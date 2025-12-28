# SCRIPT.IA - Sprint 3: Backend/Frontend Separation

## 🏗️ Architecture

```
SCRIPT.IA/
├── backend/              # FastAPI Backend
│   ├── api/
│   │   ├── routes/      # Endpoints REST
│   │   └── models/      # Modèles Pydantic
│   ├── workers/         # RQ Workers
│   ├── config.py        # Configuration
│   └── main.py          # Application FastAPI
│
├── frontend/            # React + Vite Frontend
│   ├── src/
│   │   ├── pages/      # Pages (ClientSelection, Progress)
│   │   ├── services/   # API Client
│   │   └── App.jsx     # Router principal
│   └── package.json
│
├── core/                # Logique métier existante
│   ├── extract.py
│   ├── generate.py
│   ├── orchestrator.py
│   └── errors.py       # Result[T] pattern
│
└── tests/               # Tests (194 tests, 50% coverage)
```

## 🚀 Démarrage Rapide

### Prérequis

1. **Python 3.11+** avec environnement virtuel activé
2. **Node.js 18+** et npm
3. **Redis** (pour la queue de jobs)
4. **Ollama** avec modèle qwen2.5:latest

### Installation

```bash
# 1. Dépendances Python
pip install -r requirements.txt

# 2. Dépendances frontend
cd frontend
npm install
cd ..
```

### Configuration

Créer un fichier `.env` à la racine :

```env
# Serveur
HOST=0.0.0.0
PORT=8000

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:latest
OLLAMA_TIMEOUT=120

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Chemins
CLIENTS_DIR=./CLIENTS
OUTPUT_DIR=./output
```

### Lancement (4 terminaux requis)

#### Terminal 1: Redis
```bash
redis-server
```

#### Terminal 2: RQ Worker
```bash
python scripts/start_worker.py
```

#### Terminal 3: Backend FastAPI
```bash
python -m backend.main
```

#### Terminal 4: Frontend React
```bash
cd frontend
npm run dev
```

### Accès

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📡 API Endpoints

### Health
- `GET /health` - Status général
- `GET /health/ollama` - Status Ollama

### Reports
- `POST /reports` - Créer un rapport (retourne job_id)
- `GET /reports/{job_id}` - Statut du rapport
- `GET /reports/{job_id}/stream` - SSE streaming (temps réel)
- `GET /reports/{job_id}/download` - Télécharger DOCX
- `DELETE /reports/{job_id}` - Supprimer un job

## 🔄 Workflow

1. **Utilisateur** : Sélectionne un client sur le frontend
2. **Frontend** : POST /reports → reçoit job_id
3. **Backend** : Enqueue job dans Redis Queue
4. **RQ Worker** : Traite le job (extraction, génération, rendu)
5. **Frontend** : SSE streaming pour suivi en temps réel
6. **Utilisateur** : Télécharge le DOCX une fois terminé

## 🧪 Tests

```bash
# Tous les tests (194 tests, 50% coverage)
pytest

# Coverage report
pytest --cov=. --cov-report=html
```

## 📦 Technologies

- **Backend**: FastAPI, Redis, RQ, Pydantic, Uvicorn
- **Frontend**: React, Vite, React Router, Axios
- **Queue**: Redis + RQ (Python)
- **LLM**: Ollama (qwen2.5:latest)
- **Tests**: pytest, coverage

## 🔐 Sécurité (TODO Sprint 3.5)

- JWT authentication
- Token refresh
- Protected routes
- CORS configuration

## 🪟 Déploiement Windows (TODO Sprint 3.7)

- IIS pour frontend statique
- FastAPI comme service Windows (NSSM)
- Redis comme service Windows
- Reverse proxy IIS → FastAPI
- HTTPS avec certificat

## 📝 Sprint 3 Status

✅ **Terminé**:
- Backend FastAPI avec CRUD complet
- Redis + RQ pour jobs asynchrones
- Frontend React + Vite avec routing
- Pages: ClientSelection, Progress
- SSE streaming pour temps réel
- API service avec Axios

⏳ **En cours**:
- Tests d'intégration complète

❌ **À faire**:
- JWT authentication
- Upload de fichiers
- Historique des rapports
- Tests backend
- Documentation déploiement Windows

## 🐛 Troubleshooting

### Redis connection refused
```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis
```

### Ollama not available
```bash
# Démarrer Ollama
ollama serve

# Vérifier le modèle
ollama list
ollama pull qwen2.5:latest
```

### Port already in use
```bash
# Changer le port dans .env
PORT=8001

# Ou tuer le processus
lsof -ti:8000 | xargs kill -9
```

## 📚 Documentation Sprint 2

- [Sprint 2 Report](docs/sprint2-report.md) - Architecture Result[T]
- [Sprint 2 Guide](docs/sprint2-guide.md) - Guide d'utilisation

---

**Version**: Sprint 3.0  
**Auteur**: SCRIPT.IA Team  
**Date**: 2024
