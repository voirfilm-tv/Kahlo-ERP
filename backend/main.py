"""
KAHLO CAFÉ — ERP Backend
FastAPI — Point d'entrée principal
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine, Base
from routers import (
    auth, stock, fournisseurs, clients, commandes,
    marches, calendrier, analytics, webhooks, ia, parametres
)
from services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://erp.kahlocafe.fr"],
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


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "kahlo-erp"}
