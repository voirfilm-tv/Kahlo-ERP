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

_PROPFIND_PRINCIPAL = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<propfind xmlns="DAV:"><prop><resourcetype/></prop></propfind>'
)


def identifiants_caldav() -> tuple[str, str]:
    """Identifiants courants (lus à chaud — suivent la config persistée)."""
    return os.getenv("CALDAV_USER", "kahlo"), os.getenv("CALDAV_PASSWORD", "")


def gestion_auto_possible() -> bool:
    """Vrai si l'ERP peut écrire le htpasswd de Radicale (volume partagé monté)."""
    try:
        return _HTPASSWD_PATH.parent.is_dir() and os.access(_HTPASSWD_PATH.parent, os.W_OK)
    except OSError:
        return False


def etat_volume_htpasswd() -> dict:
    """État lisible du volume htpasswd partagé avec Radicale."""
    parent = _HTPASSWD_PATH.parent
    try:
        dossier_existe = parent.is_dir()
        dossier_writable = dossier_existe and os.access(parent, os.W_OK)
        fichier_existe = _HTPASSWD_PATH.exists()
        fichier_writable = os.access(_HTPASSWD_PATH, os.W_OK) if fichier_existe else dossier_writable
        return {
            "ok": bool(dossier_existe and dossier_writable and fichier_writable),
            "path": str(_HTPASSWD_PATH),
            "dossier_existe": dossier_existe,
            "dossier_writable": dossier_writable,
            "fichier_existe": fichier_existe,
            "fichier_writable": fichier_writable,
        }
    except OSError as e:
        return {
            "ok": False,
            "path": str(_HTPASSWD_PATH),
            "erreur": str(e),
            "dossier_existe": False,
            "dossier_writable": False,
            "fichier_existe": False,
            "fichier_writable": False,
        }


def verifier_mot_de_passe_htpasswd(user: str, password: str) -> dict:
    """Vérifie que le mot de passe ERP correspond au hash écrit pour Radicale."""
    if not _HTPASSWD_PATH.exists():
        return {
            "ok": False,
            "code": "htpasswd_absent",
            "message": f"Fichier htpasswd absent : {_HTPASSWD_PATH}",
        }

    try:
        lignes = _HTPASSWD_PATH.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        return {
            "ok": False,
            "code": "htpasswd_illisible",
            "message": f"Impossible de lire le htpasswd Radicale : {e}",
        }

    prefix = f"{user}:"
    for ligne in lignes:
        if not ligne.startswith(prefix):
            continue
        hash_bcrypt = ligne[len(prefix):].strip()
        try:
            ok = bcrypt.verify(password, hash_bcrypt)
            return {
                "ok": ok,
                "code": "ok" if ok else "mauvais_identifiants",
                "message": (
                    "Le mot de passe affiché par l'ERP correspond au htpasswd Radicale"
                    if ok
                    else "Le mot de passe affiché par l'ERP ne correspond pas au htpasswd Radicale"
                ),
            }
        except ValueError as e:
            return {
                "ok": False,
                "code": "hash_invalide",
                "message": f"Hash htpasswd invalide pour l'utilisateur CalDAV : {e}",
            }

    return {
        "ok": False,
        "code": "utilisateur_absent",
        "message": f"L'utilisateur CalDAV '{user}' est absent du htpasswd Radicale",
    }


def url_interne_caldav(user: str | None = None) -> str:
    """URL CalDAV interne Docker, utilisée par le backend pour tester Radicale."""
    caldav_user = user or identifiants_caldav()[0]
    base = os.getenv("CALDAV_BASE_URL", "http://caldav:5232").rstrip("/")
    return f"{base}/{caldav_user}/"


async def tester_auth_caldav(url: str, user: str, password: str, timeout: float = 5) -> dict:
    """Teste réellement une authentification Basic CalDAV via PROPFIND."""
    import httpx

    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
            resp = await client.request(
                "PROPFIND",
                url,
                content=_PROPFIND_PRINCIPAL,
                headers={"Depth": "0", "Content-Type": "application/xml"},
                auth=(user, password),
            )
    except httpx.InvalidURL as e:
        return {"ok": False, "code": "url_invalide", "message": f"URL CalDAV invalide : {e}"}
    except httpx.RequestError as e:
        return {
            "ok": False,
            "code": "injoignable",
            "message": f"Radicale injoignable sur {url} : {e}",
        }

    if resp.status_code in (200, 207):
        return {
            "ok": True,
            "code": "ok",
            "status_code": resp.status_code,
            "message": f"Authentification CalDAV OK sur {url}",
        }
    if resp.status_code in (401, 403):
        return {
            "ok": False,
            "code": "mauvais_identifiants",
            "status_code": resp.status_code,
            "message": "Mauvais identifiants : Radicale refuse l'identifiant ou le mot de passe affiché",
        }
    if resp.status_code in (301, 302, 307, 308):
        return {
            "ok": False,
            "code": "redirection",
            "status_code": resp.status_code,
            "message": f"L'URL CalDAV redirige au lieu de répondre directement ({resp.status_code})",
        }
    return {
        "ok": False,
        "code": "statut_inattendu",
        "status_code": resp.status_code,
        "message": f"Réponse CalDAV inattendue ({resp.status_code}) sur {url}",
    }


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
