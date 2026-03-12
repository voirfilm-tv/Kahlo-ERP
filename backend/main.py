"""
KAHLO CAFÉ — ERP Backend
FastAPI — Point d'entrée principal
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os

from database import engine, Base, AsyncSessionLocal
from sqlalchemy import text
from routers import (
    auth, stock, fournisseurs, clients, commandes,
    marches, calendrier, analytics, webhooks, ia, parametres,
    utilisateurs, system_update
)
from services.scheduler import start_scheduler
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


async def _run_migrations():
    """Applique les migrations Alembic (upgrade head).
    Fallback sur create_all si Alembic échoue (ex: première installation).
    """
    try:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations Alembic appliquées")
    except Exception:
        logger.warning("Alembic indisponible, fallback sur create_all")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def _seed_data():
    """Insère les données initiales si la base est vierge (fournisseurs + admin)."""
    from sqlalchemy import select
    from models import Fournisseur
    from routers.auth import _init_admin_si_vide

    async with AsyncSessionLocal() as db:
        # Seed fournisseurs
        result = await db.execute(select(Fournisseur).limit(1))
        if result.scalars().first() is None:
            seed = [
                Fournisseur(nom="Café Imports Lyon", email="contact@cafeimports-lyon.fr", pays="France", delai_moyen=5, score=4.5),
                Fournisseur(nom="Origine Direct", email="hello@origine-direct.com", pays="France", delai_moyen=7, score=4.8),
                Fournisseur(nom="Terra Coffee", email="pro@terracoffee.eu", pays="Belgique", delai_moyen=10, score=4.2),
            ]
            db.add_all(seed)
            await db.commit()
            logger.info("Données initiales insérées (fournisseurs)")

        # Seed admin
        await _init_admin_si_vide(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup : persist secret → migrations → seed → scheduler
    auth.persist_secret_key_if_needed()
    await _run_migrations()
    await _seed_data()
    start_scheduler()
    yield
    # Shutdown


# Désactiver OpenAPI/docs en production (quand SECRET_KEY est configurée)
_is_prod = os.getenv("SECRET_KEY", "") not in {"", "dev_key", "dev-secret-key-change-in-production", "changeme"}

app = FastAPI(
    title="Kahlo Café ERP",
    description="Système de gestion interne — Kahlo Café Lyon",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

# CORS — autoriser le frontend uniquement
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,https://erp.kahlocafe.fr")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Routers
app.include_router(auth.router,         prefix="/api/auth",         tags=["Auth"])
app.include_router(stock.router,        prefix="/api/stock",        tags=["Stock"])
app.include_router(fournisseurs.router, prefix="/api/fournisseurs", tags=["Fournisseurs"])
app.include_router(clients.router,      prefix="/api/clients",      tags=["CRM"])
app.include_router(commandes.router,    prefix="/api/commandes",    tags=["Commandes"])
app.include_router(marches.router,      prefix="/api/marches",      tags=["Marchés"])
app.include_router(calendrier.router,   prefix="/api/calendrier",   tags=["Calendrier"])
app.include_router(analytics.router,    prefix="/api/analytics",    tags=["Analytics"])
app.include_router(webhooks.router,     prefix="/api/webhooks",     tags=["Webhooks"])
app.include_router(ia.router,           prefix="/api/ia",           tags=["IA Gemini"])
app.include_router(parametres.router,   prefix="/api/parametres",   tags=["Paramètres"])
app.include_router(utilisateurs.router, prefix="/api/utilisateurs", tags=["Utilisateurs"])
app.include_router(system_update.router, prefix="/api/system-update", tags=["Mise à jour"])


# Global exception handler — empêche les stack traces en production
@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    logger.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur"},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health/live")
async def health_live():
    return {"status": "alive"}


@app.get("/api/health/ready")
async def health_ready():
    checks = {"database": False, "redis": False}

    # DB check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        logger.exception("Readiness DB check failed")

    # Redis check
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    r = aioredis.from_url(redis_url, decode_responses=True)
    try:
        pong = await r.ping()
        checks["redis"] = bool(pong)
    except Exception:
        logger.exception("Readiness Redis check failed")
    finally:
        await r.aclose()

    if all(checks.values()):
        return {"status": "ready", "checks": checks}

    return JSONResponse(status_code=503, content={"status": "degraded", "checks": checks})
