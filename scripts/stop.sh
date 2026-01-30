#!/bin/bash
# Script d'arrêt de tous les services SCRIPT.IA

echo "🛑 Arrêt de tous les services SCRIPT.IA..."
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Arrêter Worker
if pkill -f "start_worker.py" 2>/dev/null; then
    echo -e "${YELLOW}✓ Worker arrêté${NC}"
else
    echo -e "${GREEN}✓ Aucun worker en cours${NC}"
fi

# Arrêter Backend
if pkill -f "backend.main" 2>/dev/null; then
    echo -e "${YELLOW}✓ Backend arrêté${NC}"
else
    echo -e "${GREEN}✓ Aucun backend en cours${NC}"
fi

# Arrêter Frontend
# 1) Tuer explicitement ce qui écoute sur 5174 (le cas le plus fréquent)
if lsof -nP -iTCP:5174 -sTCP:LISTEN >/dev/null 2>&1; then
    pids=$(lsof -nP -iTCP:5174 -sTCP:LISTEN -t 2>/dev/null || true)
    if [ -n "$pids" ]; then
        kill -TERM $pids 2>/dev/null || true
        sleep 1
        kill -KILL $pids 2>/dev/null || true
    fi
fi

# 2) Fallback: tuer vite/node vite
pkill -f "node .*/node_modules/.bin/vite" 2>/dev/null || true
pkill -f "\bvite\b" 2>/dev/null || true

echo -e "${YELLOW}✅ Frontend arrêté${NC}" 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ Tous les services sont arrêtés${NC}"
echo ""
echo -e "${YELLOW}💡 Pour redémarrer: ./scripts/start-all.sh${NC}"
