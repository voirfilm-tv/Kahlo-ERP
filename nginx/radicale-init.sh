#!/bin/sh
# Crée le fichier htpasswd au premier démarrage de Radicale
# si aucun utilisateur n'existe encore.

HTPASSWD_FILE="/data/users"

if [ ! -f "$HTPASSWD_FILE" ]; then
    echo "Initialisation du fichier htpasswd pour Radicale..."
    CALDAV_USER="${CALDAV_USER:-kahlo}"
    CALDAV_PASSWORD="${CALDAV_PASSWORD:-changeme}"
    # htpasswd avec bcrypt (-B) fourni par le package apache2-utils dans l'image
    htpasswd -Bbc "$HTPASSWD_FILE" "$CALDAV_USER" "$CALDAV_PASSWORD"
    echo "Utilisateur CalDAV '$CALDAV_USER' créé."
fi

# Lancer Radicale normalement
exec python3 -m radicale --config /etc/radicale/config
