#!/bin/sh
set -eu
# Crée le fichier htpasswd au premier démarrage de Radicale
# si aucun utilisateur n'existe encore.

HTPASSWD_FILE="/data/users"

if [ ! -f "$HTPASSWD_FILE" ]; then
    echo "Initialisation du fichier htpasswd pour Radicale..."
    CALDAV_USER="${CALDAV_USER:-kahlo}"
    CALDAV_PASSWORD="${CALDAV_PASSWORD:-changeme}"
    # htpasswd avec bcrypt (-B) — password via stdin pour éviter fuite /proc
    echo "$CALDAV_PASSWORD" | htpasswd -Bci "$HTPASSWD_FILE" "$CALDAV_USER"
    chmod 600 "$HTPASSWD_FILE"
    echo "Utilisateur CalDAV '$CALDAV_USER' créé."
fi

# Lancer Radicale normalement
exec python3 -m radicale --config /etc/radicale/config
