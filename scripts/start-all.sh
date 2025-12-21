#!/bin/bash
# Script de démarrage complet de SCRIPT.IA

set -e

echo "🚀 Démarrage de SCRIPT.IA - Générateur de Rapports"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Répertoire du script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Fonction pour vérifier un service
check_service() {
    local name=$1
    local url=$2
    echo -ne "${CYAN}🔍 Vérification $name...${NC}"
    if curl -s "$url" > /dev/null 2>&1; then
        echo -e " ${GREEN}✅ OK${NC}"
        return 0
    else
        echo -e " ${RED}❌ Non disponible${NC}"
        return 1
    fi
}

API_BASE_URL="http://127.0.0.1:8000"

# 1. Vérifier Redis
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}1️⃣  Vérification Redis${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis est actif${NC}"
else
    echo -e "${RED}❌ Redis n'est pas démarré${NC}"
    echo -e "${YELLOW}Démarrez Redis avec: redis-server &${NC}"
    exit 1
fi
echo ""

# 2. Vérifier Ollama
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}2️⃣  Vérification Ollama${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
if check_service "Ollama" "http://localhost:11434/api/version"; then
    # Vérifier les modèles
    MODELS=$(curl -s http://localhost:11434/api/tags | python3 -c "import json,sys; print(', '.join([m['name'] for m in json.load(sys.stdin)['models'][:3]]))" 2>/dev/null || echo "")
    if [ -n "$MODELS" ]; then
        echo -e "${GREEN}📦 Modèles disponibles: $MODELS${NC}"
    fi
else
    echo -e "${RED}❌ Ollama n'est pas accessible${NC}"
    echo -e "${YELLOW}Démarrez Ollama ou installez-le depuis: https://ollama.com${NC}"
    exit 1
fi
echo ""

# 3. Arrêter les anciens processus
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}3️⃣  Nettoyage des anciens processus${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
FORCE_RESTART="${FORCE_RESTART:-0}"
if [ "$FORCE_RESTART" = "1" ]; then
    pkill -f "start_worker.py" 2>/dev/null && echo -e "${YELLOW}🛑 Worker arrêté${NC}" || echo -e "${GREEN}✓ Aucun worker en cours${NC}"
    pkill -f "backend.main" 2>/dev/null && echo -e "${YELLOW}🛑 Backend arrêté${NC}" || echo -e "${GREEN}✓ Aucun backend en cours${NC}"
    pkill -f "vite.*5173" 2>/dev/null && echo -e "${YELLOW}🛑 Frontend arrêté${NC}" || echo -e "${GREEN}✓ Aucun frontend en cours${NC}"
    sleep 2
else
    echo -e "${GREEN}✓ Mode safe: on ne coupe pas les services déjà démarrés.${NC}"
    echo -e "${YELLOW}💡 Pour forcer un redémarrage propre (et interrompre les jobs en cours) : FORCE_RESTART=1 ./scripts/start-all.sh${NC}"
fi
echo ""

# 4. Démarrer le Worker RQ
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}4️⃣  Démarrage du Worker RQ${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
if pgrep -f "scripts/start_worker.py" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Worker déjà actif${NC}"
else
    nohup .venv/bin/python scripts/start_worker.py > /tmp/worker.log 2>&1 &
    WORKER_PID=$!
    echo -e "${YELLOW}⏳ Attente du worker...${NC}"
    sleep 2
    if ps -p $WORKER_PID > /dev/null; then
        echo -e "${GREEN}✅ Worker démarré (PID: $WORKER_PID) - SimpleWorker sans fork${NC}"
    else
        echo -e "${RED}❌ Échec démarrage worker${NC}"
        tail -20 /tmp/worker.log
        exit 1
    fi
fi
echo ""

# 5. Démarrer le Backend FastAPI
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}5️⃣  Démarrage du Backend FastAPI${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
if curl -s "${API_BASE_URL}/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend déjà actif${NC}"
else
    nohup .venv/bin/python -m backend.main > /tmp/backend.log 2>&1 &
    BACKEND_PID=$!
    echo -e "${YELLOW}⏳ Attente du backend...${NC}"
    for i in {1..10}; do
        if curl -s "${API_BASE_URL}/api/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Backend démarré (PID: $BACKEND_PID)${NC}"
            break
        fi
        sleep 1
    done

    if ! curl -s "${API_BASE_URL}/api/health" > /dev/null 2>&1; then
        echo -e "${RED}❌ Backend non accessible${NC}"
        tail -20 /tmp/backend.log
        exit 1
    fi
fi
echo ""

# 6. Démarrer le Frontend Vite
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}6️⃣  Démarrage du Frontend React${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend déjà actif${NC}"
else
    cd frontend
    nohup npm run dev > /tmp/frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    echo -e "${YELLOW}⏳ Attente du frontend...${NC}"
    for i in {1..15}; do
        if curl -s http://localhost:5173 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Frontend démarré (PID: $FRONTEND_PID)${NC}"
            break
        fi
        sleep 1
    done

    if ! curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo -e "${RED}❌ Frontend non accessible${NC}"
        tail -20 /tmp/frontend.log
        exit 1
    fi
fi
echo ""

# 7. Résumé
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 Tous les services sont démarrés !${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}📱 Frontend:${NC}  http://localhost:5173"
echo -e "${CYAN}🔧 Backend:${NC}   ${API_BASE_URL}/api/health"
echo -e "${CYAN}📚 API Docs:${NC}  ${API_BASE_URL}/api/docs"
echo -e "${CYAN}🔐 Login:${NC}     admin / admin123"
echo ""
echo -e "${CYAN}📋 Logs:${NC}"
echo -e "   Worker:   tail -f /tmp/worker.log"
echo -e "   Backend:  tail -f /tmp/backend.log"
echo -e "   Frontend: tail -f /tmp/frontend.log"
echo -e "   Tout-en-un: ./scripts/tail-logs.sh"
echo ""
echo -e "${YELLOW}💡 Pour arrêter tous les services: ./scripts/stop.sh${NC}"
echo ""
echo -e "${GREEN}🚀 Ouvrez votre navigateur sur http://localhost:5173${NC}"
echo ""

# Ouvrir le navigateur (optionnel)
if command -v open &> /dev/null; then
    echo -e "${CYAN}🌐 Ouverture du navigateur...${NC}"
    sleep 2
    open http://localhost:5173
fi
