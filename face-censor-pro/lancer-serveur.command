#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo "  Face Censor Pro — Installation & démarrage"
echo "  ─────────────────────────────────────────"
echo ""
echo "  Installation des dépendances (première fois ~2 min)..."
pip3 install -r requirements.txt -q
echo ""
echo "  Démarrage du serveur sur http://localhost:8765"
echo "  Laissez cette fenêtre ouverte."
echo ""
python3 server.py
read -p "Appuyez sur Entrée pour fermer..."
