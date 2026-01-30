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
    pkill -f "vite.*5174" 2>/dev/null && echo -e "${YELLOW}🛑 Frontend arrêté${NC}" || echo -e "${GREEN}✓ Aucun frontend en cours${NC}"
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

# Pour éviter le "je coupe et je ne peux plus rien faire" (job long + worker unique),
# on lance 2 workers par défaut sur macOS (SimpleWorker, sans fork).
WORKER_COUNT="${WORKER_COUNT:-}"
if [ -z "$WORKER_COUNT" ]; then
    if [ "$(uname -s)" = "Darwin" ]; then
        WORKER_COUNT=2
    else
        WORKER_COUNT=1
    fi
fi

current_workers=$(pgrep -f "scripts/start_worker.py" 2>/dev/null | wc -l | tr -d ' ')
current_workers=${current_workers:-0}

if [ "$current_workers" -ge "$WORKER_COUNT" ]; then
    echo -e "${GREEN}✅ Workers déjà actifs (${current_workers}/${WORKER_COUNT})${NC}"
else
    to_start=$((WORKER_COUNT - current_workers))
    echo -e "${YELLOW}⏳ Lancement de ${to_start} worker(s) (${current_workers} déjà actif(s))...${NC}"

    for i in $(seq 1 $to_start); do
        # Déterminer l'index global du worker (1 => /tmp/worker.log, 2 => /tmp/worker_2.log, ...)
        idx=$((current_workers + i))
        if [ "$idx" -le 1 ]; then
            log_path="/tmp/worker.log"
        else
            log_path="/tmp/worker_${idx}.log"
        fi

        nohup .venv/bin/python scripts/start_worker.py > "$log_path" 2>&1 &
        WORKER_PID=$!
        sleep 0.6
        if ps -p $WORKER_PID > /dev/null; then
            echo -e "${GREEN}✅ Worker démarré (PID: $WORKER_PID) - log: ${log_path}${NC}"
        else
            echo -e "${RED}❌ Échec démarrage worker${NC}"
            tail -20 "$log_path" || true
            exit 1
        fi
    done
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
if curl -s http://localhost:5174 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend déjà actif${NC}"
else
    cd frontend
    nohup npm run dev > /tmp/frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    echo -e "${YELLOW}⏳ Attente du frontend...${NC}"
    for i in {1..15}; do
        if curl -s http://localhost:5174 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Frontend démarré (PID: $FRONTEND_PID)${NC}"
            break
        fi
        sleep 1
    done

    if ! curl -s http://localhost:5174 > /dev/null 2>&1; then
        echo -e "${RED}❌ Frontend non accessible${NC}"
        tail -20 /tmp/frontend.log
        exit 1
    fi
fi
echo ""

# 7. Démarrer Streamlit (application principale avec menu)
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "${CYAN}7️⃣  Démarrage Streamlit (Menu Navigation)${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
if curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Streamlit déjà actif${NC}"
else
    nohup .venv/bin/streamlit run streamlit_app.py --server.port 8501 --server.headless true > /tmp/streamlit.log 2>&1 &
    STREAMLIT_PID=$!
    echo -e "${YELLOW}⏳ Attente de Streamlit...${NC}"
    for i in {1..10}; do
        if curl -s http://localhost:8501 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Streamlit démarré (PID: $STREAMLIT_PID)${NC}"
            break
        fi
        sleep 1
    done

    if ! curl -s http://localhost:8501 > /dev/null 2>&1; then
        echo -e "${RED}❌ Streamlit non accessible${NC}"
        tail -20 /tmp/streamlit.log
        exit 1
    fi
fi
echo ""

# 8. Résumé
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 Tous les services sont démarrés !${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}📱 Frontend:${NC}   http://localhost:5174"
echo -e "${CYAN}🎓 Streamlit:${NC}  http://localhost:8501 (avec menu)"
echo -e "${CYAN}🔧 Backend:${NC}    ${API_BASE_URL}/api/health"
echo -e "${CYAN}📚 API Docs:${NC}   ${API_BASE_URL}/api/docs"
echo -e "${CYAN}🔐 Login:${NC}      admin / admin123"
echo ""
echo -e "${CYAN}📋 Logs:${NC}"
echo -e "   Worker:    tail -f /tmp/worker.log"
echo -e "   Backend:   tail -f /tmp/backend.log"
echo -e "   Frontend:  tail -f /tmp/frontend.log"
echo -e "   Streamlit: tail -f /tmp/streamlit.log"
echo -e "   Tout-en-un: ./scripts/tail-logs.sh"
echo ""
echo -e "${YELLOW}💡 Pour arrêter tous les services: ./scripts/stop.sh${NC}"
echo ""
echo -e "${GREEN}🚀 Ouvrez votre navigateur sur:${NC}"
echo -e "   ${GREEN}Frontend:${NC}   http://localhost:5174"
echo -e "   ${GREEN}Streamlit:${NC}  http://localhost:8501"
echo ""

# Ouvrir le navigateur (optionnel)
if command -v open &> /dev/null; then
    echo -e "${CYAN}🌐 Ouverture du navigateur...${NC}"
    sleep 2
    open http://localhost:5174
fi
