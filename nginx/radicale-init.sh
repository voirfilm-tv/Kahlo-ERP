#!/bin/sh
set -eu
# Crée le fichier htpasswd au premier démarrage de Radicale
# si aucun utilisateur n'existe encore.

HTPASSWD_FILE="/data/users"

# Garantir les permissions sur /data (volume Docker peut être root:root)
chown -R radicale:radicale /data
mkdir -p /data/collections
chmod 750 /data /data/collections

if [ ! -f "$HTPASSWD_FILE" ]; then
    echo "Initialisation du fichier htpasswd pour Radicale..."
    CALDAV_USER="${CALDAV_USER:-kahlo}"
    CALDAV_PASSWORD="${CALDAV_PASSWORD:-changeme}"
    # htpasswd avec bcrypt (-B) — password via stdin pour éviter fuite /proc
    echo "$CALDAV_PASSWORD" | htpasswd -Bci "$HTPASSWD_FILE" "$CALDAV_USER"
    chown radicale:radicale "$HTPASSWD_FILE"
    chmod 600 "$HTPASSWD_FILE"
    echo "Utilisateur CalDAV '$CALDAV_USER' créé."
fi

# Lancer Radicale en tant que radicale (drop privileges)
echo "Démarrage de Radicale..."
exec su-exec radicale python3 -m radicale --config /etc/radicale/config
