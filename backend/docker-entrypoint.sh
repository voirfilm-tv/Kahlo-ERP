#!/bin/sh
# Kahlo ERP — entrypoint backend
# Démarre en root pour garantir les permissions des volumes montés
# (Docker crée les volumes nommés en root), puis bascule sur l'utilisateur
# non privilégié appuser pour exécuter l'application.
set -e

mkdir -p /app/data /app/uploads /app/factures /backups/kahlo /app/caldav-data

# Volumes potentiellement créés root par Docker → les rendre à appuser.
# Non récursif sur les gros dossiers (backups) pour un démarrage rapide.
chown appuser:appuser /app/data /app/uploads /app/factures /backups /backups/kahlo 2>/dev/null || true
# Volume Radicale partagé : appuser doit pouvoir écrire le htpasswd (users).
# Les deux conteneurs créent leur utilisateur avec le même uid (1000).
chown appuser:appuser /app/caldav-data 2>/dev/null || true
[ -f /app/caldav-data/users ] && chown appuser:appuser /app/caldav-data/users 2>/dev/null || true
chown -R appuser:appuser /app/data 2>/dev/null || true

exec su-exec appuser "$@"
