#!/bin/bash
# Script pour lancer Streamlit avec le MENU de navigation

cd "$(dirname "$0")"

echo "🚀 Lancement de Streamlit avec MENU de navigation"
echo ""

# Arrêter toute instance existante
lsof -ti:8501 | xargs kill -9 2>/dev/null

echo "✅ Démarrage de streamlit_app.py sur port 8501"
echo ""

# Lancer l'application principale
.venv/bin/streamlit run streamlit_app.py --server.port 8501

echo ""
echo "🎯 Accès: http://localhost:8501"
