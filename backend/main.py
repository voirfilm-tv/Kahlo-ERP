"""
KAHLO CAFÉ — ERP Backend
FastAPI — Point d'entrée principal
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import os

from database import engine, Base, AsyncSessionLocal
from routers import (
    auth, stock, fournisseurs, clients, commandes,
    marches, calendrier, analytics, webhooks, ia, parametres,
    utilisateurs
)
from services.scheduler import start_scheduler
import logging

logger = logging.getLogger(__name__)

_STARTUP_MAX_RETRIES = 10
_STARTUP_RETRY_DELAY = 3  # secondes


async def _wait_for_db():
    """Attend que PostgreSQL soit prêt (retry avec backoff)."""
    from sqlalchemy import text
    for attempt in range(1, _STARTUP_MAX_RETRIES + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("PostgreSQL prêt (tentative %d)", attempt)
            return
        except Exception as e:
            if attempt == _STARTUP_MAX_RETRIES:
                logger.error("PostgreSQL injoignable après %d tentatives", attempt)
                raise
            logger.warning("PostgreSQL non prêt (tentative %d/%d): %s", attempt, _STARTUP_MAX_RETRIES, e)
            await asyncio.sleep(_STARTUP_RETRY_DELAY)


async def _wait_for_redis():
    """Attend que Redis soit prêt (retry avec backoff). Non bloquant si Redis absent."""
    try:
        import redis.asyncio as aioredis
    except ImportError:
        logger.info("redis non installé, skip vérification Redis")
        return

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    for attempt in range(1, _STARTUP_MAX_RETRIES + 1):
        try:
            r = aioredis.from_url(redis_url, decode_responses=True)
            await r.ping()
            await r.aclose()
            logger.info("Redis prêt (tentative %d)", attempt)
            return
        except Exception as e:
            if attempt == _STARTUP_MAX_RETRIES:
                logger.warning("Redis injoignable après %d tentatives — le backend démarre sans Redis", attempt)
                return  # Non bloquant : l'app fonctionne sans Redis (mode dégradé)
            logger.warning("Redis non prêt (tentative %d/%d): %s", attempt, _STARTUP_MAX_RETRIES, e)
            await asyncio.sleep(_STARTUP_RETRY_DELAY)


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
    # Startup : persist secret → wait services → migrations → seed → scheduler
    auth.persist_secret_key_if_needed()
    await _wait_for_db()
    await _wait_for_redis()
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
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
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
