#!/bin/bash
# ============================================================
#  KAHLO CAFÉ ERP — Script de démarrage
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "  ██╗  ██╗ █████╗ ██╗  ██╗██╗      ██████╗ "
echo "  ██║ ██╔╝██╔══██╗██║  ██║██║     ██╔═══██╗"
echo "  █████╔╝ ███████║███████║██║     ██║   ██║"
echo "  ██╔═██╗ ██╔══██║██╔══██║██║     ██║   ██║"
echo "  ██║  ██╗██║  ██║██║  ██║███████╗╚██████╔╝"
echo "  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ "
echo "  CAFÉ · ERP · LYON"
echo ""

# Vérifier que .env existe
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠  Fichier .env manquant — copie depuis .env.example${NC}"
    cp .env.example .env
    echo -e "${RED}→  Remplissez les variables dans .env avant de continuer${NC}"
    exit 1
fi

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker non installé${NC}"
    exit 1
fi

# Détecter Docker Compose (plugin ou standalone)
if docker compose version &> /dev/null; then
    DC="docker compose"
elif command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    echo -e "${RED}✗ Docker Compose non installé${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker détecté ($DC)${NC}"

# Mode
MODE=${1:-"dev"}

if [ "$MODE" = "dev" ]; then
    echo -e "${YELLOW}→ Démarrage en mode développement...${NC}"
    $DC up --build

elif [ "$MODE" = "prod" ]; then
    echo -e "${YELLOW}→ Démarrage en mode production...${NC}"
    $DC up -d --build
    echo ""
    echo -e "${GREEN}✅ Kahlo ERP démarré en arrière-plan${NC}"
    echo "   Frontend : http://localhost"
    echo "   API docs : http://localhost/api/docs"
    echo "   CalDAV   : http://localhost/caldav/"
    echo ""
    echo "   Logs : $DC logs -f"

elif [ "$MODE" = "stop" ]; then
    echo -e "${YELLOW}→ Arrêt des services...${NC}"
    $DC down
    echo -e "${GREEN}✅ Services arrêtés${NC}"

elif [ "$MODE" = "reset" ]; then
    echo -e "${RED}⚠  Suppression de toutes les données !${NC}"
    read -p "Confirmer ? (oui/non) : " confirm
    if [ "$confirm" = "oui" ]; then
        $DC down -v
        echo -e "${GREEN}✅ Reset complet effectué${NC}"
    fi

else
    echo "Usage: ./start.sh [dev|prod|stop|reset]"
fi
