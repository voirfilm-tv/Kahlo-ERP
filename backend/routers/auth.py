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


def _check_rate_limit(key: str):
    """Lève HTTPException si trop de tentatives."""
    now = time.time()
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
# En dev sans .env → clé temporaire (sessions perdues au restart, mais pas de crash)
# En prod → DOIT être dans .env
SECRET_KEY = os.getenv("SECRET_KEY", "")
_INSECURE_SECRETS = {"", "dev_key", "dev-secret-key-change-in-production", "changeme"}
if SECRET_KEY in _INSECURE_SECRETS:
    SECRET_KEY = _secrets.token_hex(32)
    logger.warning(
        "SECRET_KEY non configuree ou insecure — cle temporaire generee. "
        "Les sessions seront perdues au redemarrage. "
        "Configurez SECRET_KEY dans .env pour la production."
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

    token = jwt.encode(
        {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role.value,
            "exp": datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS),
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
