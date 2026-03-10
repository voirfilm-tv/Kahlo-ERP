"""
KAHLO CAFÉ — ERP Backend
FastAPI — Point d'entrée principal
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
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
    except Exception as e:
        logger.warning(f"Alembic indisponible ({e}), fallback sur create_all")
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
    # Startup : migrations → seed → scheduler
    await _run_migrations()
    await _seed_data()
    start_scheduler()
    yield
    # Shutdown


app = FastAPI(
    title="Kahlo Café ERP",
    description="Système de gestion interne — Kahlo Café Lyon",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — autoriser le frontend
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,https://erp.kahlocafe.fr")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "kahlo-erp"}
