"""KAHLO CAFÉ — Auth JWT multi-utilisateurs"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import os
import logging
import time
import secrets as _secrets

from database import get_db
from models import Utilisateur, RoleUtilisateur

logger = logging.getLogger(__name__)

# ============================================================
#  RATE LIMITING
# ============================================================

_login_attempts: dict[str, list[float]] = defaultdict(list)
_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "300"))
_MAX_TRACKED_KEYS = 10_000  # Empêcher le memory leak si attaque par usernames aléatoires


def _check_rate_limit(key: str):
    """Lève HTTPException si trop de tentatives."""
    now = time.time()

    # Nettoyage périodique : si trop de clés trackées, purger les anciennes
    if len(_login_attempts) > _MAX_TRACKED_KEYS:
        stale_keys = [
            k for k, v in _login_attempts.items()
            if not v or (now - max(v)) > _WINDOW_SECONDS
        ]
        for k in stale_keys:
            del _login_attempts[k]

    _login_attempts[key] = [t for t in _login_attempts[key] if now - t < _WINDOW_SECONDS]
    if len(_login_attempts[key]) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Trop de tentatives de connexion. Réessayez dans quelques minutes."
        )
    _login_attempts[key].append(now)


# ============================================================
#  CRYPTO & SECRETS
# ============================================================

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# SECRET_KEY : utilisée pour signer les JWT
# En dev sans .env → clé auto-générée et persistée dans .env
# En prod → DOIT être dans .env
SECRET_KEY = os.getenv("SECRET_KEY", "")
_INSECURE_SECRETS = {"", "dev_key", "dev-secret-key-change-in-production", "changeme"}
_SECRET_KEY_WAS_GENERATED = False
if SECRET_KEY in _INSECURE_SECRETS:
    SECRET_KEY = _secrets.token_hex(32)
    _SECRET_KEY_WAS_GENERATED = True
    logger.warning(
        "SECRET_KEY non configuree ou insecure — cle generee automatiquement. "
        "Elle sera persistee dans .env au demarrage."
    )

ALGORITHM = "HS256"
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "8"))


# ============================================================
#  ADMIN BOOTSTRAP
# ============================================================

# Docker Compose interpole les $ dans les valeurs .env, ce qui casse les hashes bcrypt.
# Solution : utiliser APP_DEFAULT_PASSWORD (mot de passe en clair) au lieu de APP_PASSWORD_HASH.
# APP_PASSWORD_HASH reste supporté pour les déploiements hors Docker.

_ADMIN_USERNAME = os.getenv("APP_USERNAME", "kahlo")
_MIN_PASSWORD_LENGTH = 8


def _resolve_admin_password_hash() -> str:
    """Résout le hash admin depuis les variables d'environnement.

    Priorité :
    1. APP_PASSWORD_HASH (hash bcrypt pré-calculé, attention aux $ dans Docker)
    2. APP_DEFAULT_PASSWORD (mot de passe en clair, hashé au démarrage)
    3. Fallback "changeme" avec warning
    """
    hash_env = os.getenv("APP_PASSWORD_HASH", "")
    if hash_env:
        # Valider que c'est un vrai hash bcrypt ($2b$ ou $2a$)
        if hash_env.startswith(("$2b$", "$2a$", "$2y$")):
            return hash_env
        logger.warning(
            "APP_PASSWORD_HASH ne ressemble pas a un hash bcrypt valide "
            "(doit commencer par $2b$, $2a$ ou $2y$). Ignoré."
        )

    default_pw = os.getenv("APP_DEFAULT_PASSWORD", "")
    if default_pw:
        return pwd_context.hash(default_pw)

    logger.warning(
        "Ni APP_PASSWORD_HASH ni APP_DEFAULT_PASSWORD ne sont définis. "
        "L'admin sera créé avec le mot de passe 'changeme'. "
        "Changez-le immédiatement après le premier login."
    )
    return pwd_context.hash("changeme")


_ADMIN_HASH = _resolve_admin_password_hash()

# Détection du mot de passe par défaut "changeme"
_USING_DEFAULT_PASSWORD = (
    not os.getenv("APP_PASSWORD_HASH", "")
    and os.getenv("APP_DEFAULT_PASSWORD", "changeme") == "changeme"
)
if _USING_DEFAULT_PASSWORD:
    logger.warning(
        "SECURITE: Le mot de passe admin est toujours 'changeme'. "
        "Changez-le via l'interface ou dans .env (APP_DEFAULT_PASSWORD)."
    )


def persist_secret_key_if_needed():
    """Persiste la SECRET_KEY auto-générée dans le fichier .env.

    Appelée au startup depuis main.py pour éviter de perdre les sessions au restart.
    """
    if not _SECRET_KEY_WAS_GENERATED:
        return

    from pathlib import Path
    env_path = Path(os.getenv("ENV_FILE_PATH", "/app/.env"))
    try:
        if not env_path.exists():
            env_path.touch(mode=0o600)

        from dotenv import set_key
        set_key(str(env_path), "SECRET_KEY", SECRET_KEY)
        logger.info("SECRET_KEY generee et persistee dans %s", env_path)
    except Exception:
        logger.warning(
            "Impossible de persister SECRET_KEY dans %s. "
            "Les sessions seront perdues au redemarrage.", env_path
        )


async def _init_admin_si_vide(db: AsyncSession):
    """Crée ou réinitialise l'admin initial.

    - Si la table est vide → crée l'admin
    - Si ADMIN_FORCE_RESET=true → met à jour le mot de passe de l'admin existant
    """
    force_reset = os.getenv("ADMIN_FORCE_RESET", "").lower() in ("true", "1", "yes")

    result = await db.execute(select(Utilisateur).limit(1))
    if result.scalars().first() is None:
        # Table vide : créer l'admin
        admin = Utilisateur(
            username=_ADMIN_USERNAME,
            nom="Administrateur",
            password_hash=_ADMIN_HASH,
            role=RoleUtilisateur.admin,
            actif=True,
        )
        db.add(admin)
        await db.commit()
        logger.info(f"Admin initial cree: {_ADMIN_USERNAME}")
        return

    if force_reset:
        # Reset du mot de passe de l'admin
        result = await db.execute(
            select(Utilisateur).where(Utilisateur.username == _ADMIN_USERNAME)
        )
        admin = result.scalars().first()
        if admin:
            admin.password_hash = _ADMIN_HASH
            admin.actif = True
            await db.commit()
            logger.warning(f"Admin reset applique pour: {_ADMIN_USERNAME} (ADMIN_FORCE_RESET=true)")
        else:
            # L'admin d'origine a été supprimé, le recréer
            admin = Utilisateur(
                username=_ADMIN_USERNAME,
                nom="Administrateur",
                password_hash=_ADMIN_HASH,
                role=RoleUtilisateur.admin,
                actif=True,
            )
            db.add(admin)
            await db.commit()
            logger.warning(f"Admin recree: {_ADMIN_USERNAME} (ADMIN_FORCE_RESET=true)")


# ============================================================
#  SCHEMAS
# ============================================================

class LoginData(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Le nom d'utilisateur ne peut pas être vide")
        return v

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Le mot de passe ne peut pas être vide")
        return v


# ============================================================
#  ROUTES
# ============================================================

@router.post("/login")
async def login(data: LoginData, db: AsyncSession = Depends(get_db)):
    _check_rate_limit(data.username)

    result = await db.execute(
        select(Utilisateur).where(
            Utilisateur.username == data.username,
            Utilisateur.actif == True
        )
    )
    user = result.scalars().first()

    if not user or not pwd_context.verify(data.password, user.password_hash):
        # Message générique pour éviter l'énumération d'utilisateurs
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role.value,
            "iat": now,
            "exp": now + timedelta(hours=SESSION_HOURS),
            "jti": _secrets.token_hex(16),
        },
        SECRET_KEY, algorithm=ALGORITHM
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "username": user.username,
    }


# ============================================================
#  MIDDLEWARE D'AUTH (dependencies)
# ============================================================

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")


def get_current_user_payload(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Retourne le payload complet du JWT (sub, user_id, role)."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Vérifie que l'utilisateur est admin."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")


# Alias utilisé par les routers qui ont besoin de vérifier le token
verifier_token = get_current_user
