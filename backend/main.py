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


async def _seed_fournisseurs():
    """Insère les fournisseurs de départ s'il n'en existe aucun."""
    from sqlalchemy import select, text
    from models import Fournisseur

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Fournisseur).limit(1))
        if result.scalars().first() is not None:
            return

        seed = [
            Fournisseur(nom="Café Imports Lyon", email="contact@cafeimports-lyon.fr", pays="France", delai_moyen=5, score=4.5),
            Fournisseur(nom="Origine Direct", email="hello@origine-direct.com", pays="France", delai_moyen=7, score=4.8),
            Fournisseur(nom="Terra Coffee", email="pro@terracoffee.eu", pays="Belgique", delai_moyen=10, score=4.2),
        ]
        db.add_all(seed)
        await db.commit()

        # Créer les index de performance (idem init.sql mais après CREATE TABLE)
        async with engine.begin() as conn:
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_lots_origine ON lots(origine)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_lots_actif ON lots(actif)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_commandes_statut ON commandes(statut)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_commandes_date ON commandes(date_commande)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_evenements_date ON evenements(date_debut)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_marches_date ON marches(date)"))

        logger.info("Données initiales insérées (fournisseurs + index)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup : créer les tables puis seeder
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_fournisseurs()
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
