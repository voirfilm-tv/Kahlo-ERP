"""KAHLO CAFÉ — Auth JWT"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "dev_key")
ALGORITHM = "HS256"

# Utilisateur unique (Kahlo Café = une seule personne)
ADMIN_USERNAME = "kahlo"
ADMIN_PASSWORD_HASH = pwd_context.hash("kahlo2026")  # À changer en prod


class LoginData(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(data: LoginData):
    if data.username != ADMIN_USERNAME or not pwd_context.verify(data.password, ADMIN_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    token = jwt.encode(
        {"sub": data.username, "exp": datetime.utcnow() + timedelta(days=30)},
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
