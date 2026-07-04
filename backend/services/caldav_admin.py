"""
KAHLO CAFÉ — Gestion automatique des identifiants CalDAV
L'ERP est propriétaire du serveur Radicale : il génère le mot de passe,
écrit directement le fichier htpasswd (volume partagé avec le conteneur
Radicale, relu à chaque authentification) et le persiste dans la config.
L'utilisateur n'a plus rien à configurer : il copie l'URL/identifiants
affichés dans Paramètres → Calendrier, ou scanne le QR code.
"""

import os
import secrets
import logging
from pathlib import Path

from passlib.hash import bcrypt

logger = logging.getLogger(__name__)

# Fichier htpasswd de Radicale (volume caldav_data partagé, cf. docker-compose)
_HTPASSWD_PATH = Path(os.getenv("CALDAV_HTPASSWD_PATH", "/app/caldav-data/users"))
_MOTS_DE_PASSE_FAIBLES = {"", "changeme"}


def identifiants_caldav() -> tuple[str, str]:
    """Identifiants courants (lus à chaud — suivent la config persistée)."""
    return os.getenv("CALDAV_USER", "kahlo"), os.getenv("CALDAV_PASSWORD", "")


def gestion_auto_possible() -> bool:
    """Vrai si l'ERP peut écrire le htpasswd de Radicale (volume partagé monté)."""
    try:
        return _HTPASSWD_PATH.parent.is_dir() and os.access(_HTPASSWD_PATH.parent, os.W_OK)
    except OSError:
        return False


def _persister_config(cle: str, valeur: str):
    """Persiste dans le fichier de config géré par l'interface (comme parametres)."""
    from dotenv import set_key
    env_path = Path(os.getenv("ENV_FILE_PATH", "/app/data/config.env"))
    if not str(env_path.resolve()).startswith("/app/"):
        env_path = Path("/app/data/config.env")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.touch(exist_ok=True)
    set_key(str(env_path), cle, valeur)
    os.environ[cle] = valeur


def ecrire_htpasswd(user: str, password: str) -> bool:
    """Écrit le htpasswd bcrypt de Radicale (relu par Radicale à chaque auth)."""
    try:
        _HTPASSWD_PATH.parent.mkdir(parents=True, exist_ok=True)
        contenu = f"{user}:{bcrypt.hash(password)}\n"
        _HTPASSWD_PATH.write_text(contenu, encoding="utf-8")
        try:
            _HTPASSWD_PATH.chmod(0o600)
        except OSError:
            pass
        logger.info("htpasswd CalDAV mis à jour pour '%s'", user)
        return True
    except OSError as e:
        logger.warning("Impossible d'écrire le htpasswd CalDAV (%s) : %s", _HTPASSWD_PATH, e)
        return False


def assurer_identifiants():
    """Au démarrage : si le mot de passe CalDAV est absent ou 'changeme',
    en génère un solide, le persiste et l'applique à Radicale.
    L'utilisateur n'a jamais à choisir/configurer ce mot de passe."""
    user, password = identifiants_caldav()

    if password in _MOTS_DE_PASSE_FAIBLES:
        password = secrets.token_urlsafe(12)
        try:
            _persister_config("CALDAV_PASSWORD", password)
            logger.info("Mot de passe CalDAV auto-généré et persisté")
        except OSError as e:
            logger.warning("Impossible de persister le mot de passe CalDAV : %s", e)
            os.environ["CALDAV_PASSWORD"] = password  # au moins pour ce process

    # Aligne Radicale sur la config de l'ERP (source de vérité)
    ecrire_htpasswd(user, password)


def regenerer_mot_de_passe() -> str:
    """Rotation du mot de passe CalDAV (les appareils devront être reconfigurés)."""
    user, _ = identifiants_caldav()
    nouveau = secrets.token_urlsafe(12)

    if not ecrire_htpasswd(user, nouveau):
        raise RuntimeError(
            "Impossible d'écrire le fichier d'authentification Radicale — "
            "vérifiez que le volume caldav_data est bien monté sur le backend "
            "(docker compose up -d --build)"
        )
    _persister_config("CALDAV_PASSWORD", nouveau)
    return nouveau
