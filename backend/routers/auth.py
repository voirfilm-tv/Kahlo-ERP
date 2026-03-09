"""KAHLO CAFÉ — Auth JWT"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os
import logging

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

# Utilisateur unique — identifiants via variables d'environnement
ADMIN_USERNAME = os.getenv("APP_USERNAME", "kahlo")
_password_hash_env = os.getenv("APP_PASSWORD_HASH", "")
if _password_hash_env:
    ADMIN_PASSWORD_HASH = _password_hash_env
else:
    ADMIN_PASSWORD_HASH = pwd_context.hash(os.getenv("APP_DEFAULT_PASSWORD", "kahlo2026"))
    logger.warning(
        "APP_PASSWORD_HASH non configure — mot de passe par defaut actif. "
        "Changez le mot de passe via Parametres > Securite."
    )

# Durée de session : 8h par défaut (au lieu de 30 jours)
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "8"))


class LoginData(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(data: LoginData):
    if data.username != ADMIN_USERNAME or not pwd_context.verify(data.password, ADMIN_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    token = jwt.encode(
        {"sub": data.username, "exp": datetime.utcnow() + timedelta(hours=SESSION_HOURS)},
        SECRET_KEY, algorithm=ALGORITHM
    )
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

# Alias utilisé par les routers qui ont besoin de vérifier le token
verifier_token = get_current_user
