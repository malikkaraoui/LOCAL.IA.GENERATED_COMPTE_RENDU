#!/bin/bash
# Script de démonstration du workflow complet

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  🎯 DÉMONSTRATION COMPLÈTE - SCRIPT.IA                         ║"
echo "║  Génération automatique de rapport en un clic                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Variables
CLIENT_NAME="KARAOUI Malik"
API_URL="http://localhost:8000/api"

# Fonction pour afficher une étape
step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# 1. Vérifier que tout est démarré
step "1️⃣  Vérification des services"

echo -ne "${YELLOW}⏳ Backend... ${NC}"
if curl -s "$API_URL/health" > /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Backend non accessible${NC}"
    echo "Lancez: ./scripts/start-all.sh"
    exit 1
fi

echo -ne "${YELLOW}⏳ Frontend... ${NC}"
if curl -s "http://localhost:5174" > /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Frontend non accessible${NC}"
    exit 1
fi

echo -ne "${YELLOW}⏳ Redis... ${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Redis non accessible${NC}"
    exit 1
fi

echo -ne "${YELLOW}⏳ Ollama... ${NC}"
if curl -s "http://localhost:11434/api/version" > /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌ Ollama non accessible${NC}"
    exit 1
fi

# 2. Lister les clients disponibles
step "2️⃣  Clients disponibles"

CLIENTS=$(curl -s "$API_URL/clients" | python3 -c "import json,sys; d=json.load(sys.stdin); print('\n'.join([f'   - {c}' for c in d.get('clients', [])]))" 2>/dev/null || echo "   - Erreur de récupération")
echo "$CLIENTS"

# 3. Lancer la génération
step "3️⃣  Démarrage de la génération"

echo -e "${CYAN}Client sélectionné :${NC} $CLIENT_NAME"
echo ""
echo -ne "${YELLOW}🚀 Création de la tâche... ${NC}"

RESPONSE=$(curl -s -X POST "$API_URL/reports" \
    -H "Content-Type: application/json" \
    -d "{\"client_name\":\"$CLIENT_NAME\"}")

REPORT_ID=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('job_id') or d.get('report_id'))" 2>/dev/null || echo "")

if [ -z "$REPORT_ID" ]; then
    echo -e "${RED}❌${NC}"
    echo "Erreur: $RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅${NC}"
echo -e "${GREEN}Report ID: $REPORT_ID${NC}"

# 4. Suivre la progression
step "4️⃣  Suivi de la génération en temps réel"

echo -e "${CYAN}Les étapes du workflow :${NC}"
echo "   1. 📂 Extraction des données (2-5s)"
echo "   2. 🤖 Génération IA avec Mistral (~1m30s)"
echo "   3. 📝 Création du DOCX (1-2s)"
echo "   4. ✅ Rapport final"
echo ""

START_TIME=$(date +%s)
LAST_STATUS=""

while true; do
    STATUS=$(curl -s "$API_URL/reports/$REPORT_ID/status" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['status'])" 2>/dev/null || echo "")
    
    if [ "$STATUS" != "$LAST_STATUS" ]; then
        CURRENT_TIME=$(date +%s)
        ELAPSED=$((CURRENT_TIME - START_TIME))
        
        case "$STATUS" in
            "pending")
                echo -e "${YELLOW}⏳ En attente...${NC} (${ELAPSED}s)"
                ;;
            "started")
                echo -e "${CYAN}🚀 Démarrage...${NC} (${ELAPSED}s)"
                ;;
            "extracting")
                echo -e "${CYAN}📂 Extraction des données...${NC} (${ELAPSED}s)"
                ;;
            "generating")
                echo -e "${YELLOW}🤖 Génération par l'IA...${NC} (${ELAPSED}s)"
                ;;
            "rendering")
                echo -e "${CYAN}📝 Création du DOCX...${NC} (${ELAPSED}s)"
                ;;
            "completed")
                echo -e "${GREEN}✅ Terminé !${NC} (${ELAPSED}s)"
                break
                ;;
            "failed")
                echo -e "${RED}❌ Échec${NC}"
                curl -s "$API_URL/reports/$REPORT_ID/status" | python3 -m json.tool
                exit 1
                ;;
        esac
        
        LAST_STATUS="$STATUS"
    fi
    
    sleep 2
done

# 5. Récupérer les détails
step "5️⃣  Détails du rapport généré"

DETAILS=$(curl -s "$API_URL/reports/$REPORT_ID/status")
echo "$DETAILS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'   ID: {d[\"report_id\"]}')
print(f'   Client: {d[\"client_name\"]}')
print(f'   Statut: {d[\"status\"]}')
if 'result' in d and d['result']:
    r = d['result']
    if 'docx_path' in r:
        print(f'   📄 DOCX: {r[\"docx_path\"]}')
    if 'pdf_path' in r:
        print(f'   📕 PDF: {r[\"pdf_path\"]}')
    if 'extraction_size' in r:
        print(f'   📊 Données extraites: {r[\"extraction_size\"]} octets')
    if 'generation_time' in r:
        print(f'   ⏱️  Temps génération: {r[\"generation_time\"]:.1f}s')
"

# 6. Instructions finales
step "6️⃣  Prochaines étapes"

echo -e "${GREEN}✅ Le rapport a été généré avec succès !${NC}"
echo ""
echo -e "${CYAN}📱 Pour télécharger depuis l'interface :${NC}"
echo "   1. Ouvrez http://localhost:5174"
echo "   2. Le rapport apparaît dans la liste"
echo "   3. Cliquez sur 'Télécharger DOCX'"
echo ""
echo -e "${CYAN}💾 Ou accédez directement au fichier :${NC}"
echo "   CLIENTS/$CLIENT_NAME/06 Rapport final/"
echo ""
echo -e "${CYAN}🔄 Pour générer un nouveau rapport :${NC}"
echo "   - Relancez ce script : ./scripts/demo.sh"
echo "   - Ou utilisez l'interface web"
echo ""

# 7. Résumé
step "📊 Résumé de la démonstration"

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

echo -e "${GREEN}✅ Démonstration terminée !${NC}"
echo ""
echo -e "${CYAN}Statistiques :${NC}"
echo "   ⏱️  Temps total: ${TOTAL_TIME}s (~$((TOTAL_TIME / 60))min)"
echo "   📂 Extraction: ~3-5s"
echo "   🤖 IA (Mistral): ~90s"
echo "   📝 Rendu DOCX: ~2s"
echo ""
echo -e "${YELLOW}💡 Le workflow complet fonctionne en UN SEUL CLIC depuis l'interface !${NC}"
echo ""
