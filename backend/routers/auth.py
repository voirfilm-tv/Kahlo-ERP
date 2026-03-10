"""KAHLO CAFÉ — Auth JWT multi-utilisateurs"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import os
import logging

from database import get_db
from models import Utilisateur, RoleUtilisateur

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY or SECRET_KEY in ("dev_key", "dev-secret-key-change-in-production"):
    import secrets as _s
    SECRET_KEY = _s.token_hex(32)
    logger.warning(
        "SECRET_KEY non configuree ou insecure — cle temporaire generee. "
        "Configurez SECRET_KEY dans .env pour la production."
    )

ALGORITHM = "HS256"
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "8"))

# Identifiants de fallback si aucun utilisateur en base
_FALLBACK_USERNAME = os.getenv("APP_USERNAME", "kahlo")
_password_hash_env = os.getenv("APP_PASSWORD_HASH", "")
if not _password_hash_env:
    _default_pw = os.getenv("APP_DEFAULT_PASSWORD", "")
    if not _default_pw:
        logger.warning(
            "APP_PASSWORD_HASH et APP_DEFAULT_PASSWORD non définis. "
            "Configurez-les dans .env pour créer l'admin initial."
        )
        _default_pw = "changeme"
    _FALLBACK_HASH = pwd_context.hash(_default_pw)
else:
    _FALLBACK_HASH = _password_hash_env


class LoginData(BaseModel):
    username: str
    password: str


async def _init_admin_si_vide(db: AsyncSession):
    """Crée l'admin initial à partir des variables d'env si la table est vide."""
    result = await db.execute(select(Utilisateur).limit(1))
    if result.scalars().first() is None:
        admin = Utilisateur(
            username=_FALLBACK_USERNAME,
            nom="Administrateur",
            password_hash=_FALLBACK_HASH,
            role=RoleUtilisateur.admin,
            actif=True,
        )
        db.add(admin)
        await db.commit()
        logger.info(f"Admin initial cree: {_FALLBACK_USERNAME}")


@router.post("/login")
async def login(data: LoginData, db: AsyncSession = Depends(get_db)):
    await _init_admin_si_vide(db)

    result = await db.execute(
        select(Utilisateur).where(
            Utilisateur.username == data.username,
            Utilisateur.actif == True
        )
    )
    user = result.scalars().first()

    if not user or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    token = jwt.encode(
        {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(hours=SESSION_HOURS),
        },
        SECRET_KEY, algorithm=ALGORITHM
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "username": user.username,
    }


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")


def get_current_user_payload(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Retourne le payload complet du JWT (sub, user_id, role)."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Vérifie que l'utilisateur est admin."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")


# Alias utilisé par les routers qui ont besoin de vérifier le token
verifier_token = get_current_user
