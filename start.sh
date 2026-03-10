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

# Charger les variables pour affichage des ports
set -a
source .env 2>/dev/null || true
set +a

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

HTTP_PORT="${HTTP_PORT:-80}"

# Mode
MODE=${1:-"dev"}

if [ "$MODE" = "dev" ]; then
    echo -e "${YELLOW}→ Démarrage en mode développement...${NC}"
    $DC up --build

elif [ "$MODE" = "prod" ]; then
    # Vérification des secrets en production
    if [ "$SECRET_KEY" = "dev-secret-key-change-in-production" ] || [ -z "$SECRET_KEY" ]; then
        echo -e "${RED}✗ SECRET_KEY non configurée pour la production${NC}"
        echo "  Générez une clé : python3 -c \"import secrets; print(secrets.token_hex(32))\""
        exit 1
    fi
    if [ "$POSTGRES_PASSWORD" = "kahlo_dev_2024" ]; then
        echo -e "${RED}✗ POSTGRES_PASSWORD utilise la valeur par défaut${NC}"
        exit 1
    fi

    echo -e "${YELLOW}→ Démarrage en mode production...${NC}"
    $DC up -d --build
    echo ""
    echo -e "${GREEN}✅ Kahlo ERP démarré en arrière-plan${NC}"
    echo "   Frontend : http://localhost:${HTTP_PORT}"
    echo "   API docs : http://localhost:${HTTP_PORT}/api/docs"
    echo "   CalDAV   : http://localhost:${HTTP_PORT}/caldav/"
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

elif [ "$MODE" = "logs" ]; then
    $DC logs -f "${2:-}"

else
    echo "Usage: ./start.sh [dev|prod|stop|reset|logs]"
fi
