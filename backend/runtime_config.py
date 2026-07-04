"""
KAHLO CAFÉ — Chargement de la configuration persistante.

La page Paramètres (admin) écrit la configuration dans un fichier env
persisté sur un volume Docker (ENV_FILE_PATH, défaut /app/data/config.env).
Ce module recharge ce fichier PAR-DESSUS les variables d'environnement du
conteneur au démarrage : ce qui a été configuré dans l'interface prime sur
les valeurs par défaut du docker-compose, et survit aux redémarrages.

IMPORTANT : doit être importé avant tout module applicatif (routers,
services) car certains lisent leur configuration à l'import.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

CONFIG_PATH = Path(os.getenv("ENV_FILE_PATH", "/app/data/config.env"))

# Garde-fou : le fichier de config doit rester dans /app/ (même règle que
# routers/parametres.py qui écrit dedans).
if str(CONFIG_PATH.resolve()).startswith("/app/") and CONFIG_PATH.exists():
    load_dotenv(CONFIG_PATH, override=True)
