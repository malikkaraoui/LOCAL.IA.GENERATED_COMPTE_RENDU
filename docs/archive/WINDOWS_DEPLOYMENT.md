# 🪟 Guide de Déploiement Windows

Guide complet pour déployer **SCRIPT.IA - Générateur de Rapports** sur Windows 10/11.

## 📋 Prérequis

### Logiciels requis
- Windows 10/11 (64-bit)
- Droits administrateur
- Connexion Internet

---

## 🔧 Installation des Dépendances

### 1. Python 3.11+

#### Installation via Microsoft Store (Recommandé)
```powershell
# Ouvrir Microsoft Store et installer Python 3.12
```

#### Ou via winget
```powershell
winget install Python.Python.3.12
```

#### Vérification
```powershell
python --version
# Devrait afficher: Python 3.12.x
```

### 2. Node.js 20+

#### Installation
```powershell
winget install OpenJS.NodeJS.LTS
```

#### Vérification
```powershell
node --version  # v20.x.x
npm --version   # 10.x.x
```

### 3. Redis

#### Option A: Redis via WSL2 (Recommandé)
```powershell
# Installer WSL2
wsl --install

# Dans WSL2
sudo apt update
sudo apt install redis-server
redis-server --daemonize yes
```

#### Option B: Redis pour Windows (Memurai)
```powershell
# Télécharger depuis https://www.memurai.com/
# Installer et démarrer le service
```

#### Vérification
```powershell
redis-cli ping
# Devrait retourner: PONG
```

### 4. Ollama

#### Installation
```powershell
# Télécharger depuis https://ollama.com/download/windows
# Exécuter OllamaSetup.exe

# Télécharger le modèle
ollama pull mistral:latest
```

#### Vérification
```powershell
ollama list
# Devrait lister: mistral:latest
```

---

## 📦 Installation du Projet

### 1. Cloner le projet
```powershell
cd C:\Projects
git clone <votre-repo> SCRIPT.IA
cd SCRIPT.IA
```

### 2. Backend Python

```powershell
# Créer l'environnement virtuel
python -m venv .venv

# Activer (PowerShell)
.\.venv\Scripts\Activate.ps1

# Si erreur de politique d'exécution:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Frontend React

```powershell
cd frontend
npm install
cd ..
```

---

## ⚙️ Configuration

### 1. Variables d'environnement Backend

Créer `.env` à la racine :
```env
# API
DEBUG=false
API_PREFIX=/api

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral:latest
OLLAMA_TIMEOUT=300

# Chemins (adapter selon votre installation)
CLIENTS_DIR=CLIENTS
TEMPLATE_PATH=TemplateRapportStage.docx
```

### 2. Variables d'environnement Frontend

Créer `frontend/.env` :
```env
VITE_API_URL=http://localhost:8000/api
```

---

## 🚀 Démarrage des Services

### Option A: Scripts PowerShell

Créer `start-services.ps1` :
```powershell
# Script de démarrage de tous les services

# 1. Vérifier Redis
Write-Host "🔍 Vérification Redis..." -ForegroundColor Cyan
$redisRunning = redis-cli ping 2>&1
if ($redisRunning -ne "PONG") {
    Write-Host "❌ Redis n'est pas démarré" -ForegroundColor Red
    Write-Host "Démarrez Redis avec: redis-server" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Redis OK" -ForegroundColor Green

# 2. Vérifier Ollama
Write-Host "🔍 Vérification Ollama..." -ForegroundColor Cyan
$ollamaRunning = curl -s http://localhost:11434/api/version 2>&1
if (-not $ollamaRunning) {
    Write-Host "❌ Ollama n'est pas démarré" -ForegroundColor Red
    Write-Host "Démarrez Ollama depuis le menu Démarrer" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Ollama OK" -ForegroundColor Green

# 3. Démarrer le Worker RQ
Write-Host "🔧 Démarrage du Worker RQ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$PSScriptRoot'; .\.venv\Scripts\Activate.ps1; `$env:OBJC_DISABLE_INITIALIZE_FORK_SAFETY='YES'; python scripts/start_worker.py" `
    -WindowStyle Normal
Start-Sleep -Seconds 2
Write-Host "✅ Worker démarré" -ForegroundColor Green

# 4. Démarrer le Backend FastAPI
Write-Host "🔧 Démarrage du Backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$PSScriptRoot'; .\.venv\Scripts\Activate.ps1; python -m backend.main" `
    -WindowStyle Normal
Start-Sleep -Seconds 3
Write-Host "✅ Backend démarré sur http://localhost:8000" -ForegroundColor Green

# 5. Démarrer le Frontend Vite
Write-Host "🔧 Démarrage du Frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$PSScriptRoot\frontend'; npm run dev" `
    -WindowStyle Normal
Start-Sleep -Seconds 3
Write-Host "✅ Frontend démarré sur http://localhost:5173" -ForegroundColor Green

Write-Host "`n🎉 Tous les services sont démarrés!" -ForegroundColor Green
Write-Host "📱 Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "🔧 Backend:  http://localhost:8000/api/health" -ForegroundColor Cyan
```

Créer `stop-services.ps1` :
```powershell
# Script d'arrêt de tous les services

Write-Host "🛑 Arrêt des services..." -ForegroundColor Yellow

# Arrêter les processus Python
Get-Process | Where-Object {$_.CommandLine -like "*backend.main*"} | Stop-Process -Force
Get-Process | Where-Object {$_.CommandLine -like "*start_worker*"} | Stop-Process -Force

# Arrêter les processus Node
Get-Process | Where-Object {$_.ProcessName -eq "node"} | Stop-Process -Force

Write-Host "✅ Services arrêtés" -ForegroundColor Green
```

#### Utilisation
```powershell
# Démarrer
.\start-services.ps1

# Arrêter
.\stop-services.ps1
```

### Option B: Installation comme Services Windows

#### 1. NSSM (Non-Sucking Service Manager)
```powershell
winget install NSSM.NSSM
```

#### 2. Créer les services

**Backend Service:**
```powershell
nssm install RapportIA-Backend "C:\Projects\SCRIPT.IA\.venv\Scripts\python.exe"
nssm set RapportIA-Backend AppParameters "-m backend.main"
nssm set RapportIA-Backend AppDirectory "C:\Projects\SCRIPT.IA"
nssm set RapportIA-Backend DisplayName "RapportIA Backend API"
nssm set RapportIA-Backend Description "Backend FastAPI pour génération de rapports"
nssm set RapportIA-Backend Start SERVICE_AUTO_START
nssm start RapportIA-Backend
```

**Worker Service:**
```powershell
nssm install RapportIA-Worker "C:\Projects\SCRIPT.IA\.venv\Scripts\python.exe"
nssm set RapportIA-Worker AppParameters "scripts/start_worker.py"
nssm set RapportIA-Worker AppDirectory "C:\Projects\SCRIPT.IA"
nssm set RapportIA-Worker DisplayName "RapportIA Worker"
nssm set RapportIA-Worker Description "Worker RQ pour traitement des jobs"
nssm set RapportIA-Worker Start SERVICE_AUTO_START
nssm start RapportIA-Worker
```

#### 3. Gérer les services
```powershell
# Démarrer
net start RapportIA-Backend
net start RapportIA-Worker

# Arrêter
net stop RapportIA-Backend
net stop RapportIA-Worker

# Statut
sc query RapportIA-Backend
```

---

## 🔍 Vérification de l'Installation

### Test complet
```powershell
# 1. Backend Health
curl http://localhost:8000/api/health

# 2. Ollama
curl http://localhost:8000/api/health/ollama

# 3. Redis
redis-cli ping

# 4. Frontend
Start-Process "http://localhost:5173"
```

---

## 🐛 Troubleshooting

### Problème: Port déjà utilisé

```powershell
# Trouver le processus utilisant le port 8000
netstat -ano | findstr :8000

# Tuer le processus (remplacer PID)
taskkill /PID <PID> /F
```

### Problème: Redis ne démarre pas

```powershell
# Si WSL2
wsl redis-server --daemonize yes

# Si Memurai
net start Memurai
```

### Problème: Ollama inaccessible

```powershell
# Vérifier le processus
Get-Process | Where-Object {$_.ProcessName -eq "ollama"}

# Redémarrer Ollama depuis le menu Démarrer
```

### Problème: Erreur Python "Module not found"

```powershell
# Réactiver l'environnement
.\.venv\Scripts\Activate.ps1

# Réinstaller les dépendances
pip install --force-reinstall -r requirements.txt
```

### Problème: Frontend ne se charge pas

```powershell
cd frontend

# Nettoyer le cache
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json

# Réinstaller
npm install

# Redémarrer
npm run dev
```

---

## 📊 Logs et Monitoring

### Logs Backend
```powershell
Get-Content -Wait logs/backend.log
```

### Logs Worker
```powershell
Get-Content -Wait logs/worker.log
```

### Logs Redis
```powershell
redis-cli monitor
```

---

## 🔐 Sécurité en Production

### 1. Pare-feu Windows
```powershell
# Autoriser uniquement localhost
New-NetFirewallRule -DisplayName "RapportIA Backend" `
    -Direction Inbound -LocalPort 8000 -Protocol TCP `
    -Action Allow -RemoteAddress 127.0.0.1
```

### 2. Variables d'environnement sécurisées
- Utiliser des variables d'environnement système au lieu de fichiers `.env`
- Changer `SECRET_KEY` dans la configuration

### 3. HTTPS avec Nginx
```powershell
# Installer Nginx pour Windows
winget install nginx.nginx

# Configurer comme reverse proxy
# Voir: https://nginx.org/en/docs/windows.html
```

---

## 📚 Ressources

- [Documentation Python Windows](https://docs.python.org/3/using/windows.html)
- [Node.js sur Windows](https://nodejs.org/en/download/)
- [Redis sur Windows (WSL2)](https://redis.io/docs/getting-started/installation/install-redis-on-windows/)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [NSSM Documentation](https://nssm.cc/usage)

---

## 🆘 Support

Pour toute question ou problème :
1. Vérifier les logs dans `logs/`
2. Consulter la section Troubleshooting
3. Ouvrir une issue sur GitHub
