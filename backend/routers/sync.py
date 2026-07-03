"""
KAHLO CAFÉ — Router Sync Offline
Expose la queue Redis du mode terrain (ventes hors connexion).
Le frontend poll GET /status et déclenche POST / au retour de connexion.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from database import get_db
from services.offline_sync import sync_queue, get_sync_status, enqueue_vente
from routers.auth import verifier_token
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)

router = APIRouter()


class LigneVenteOffline(BaseModel):
    lot_id: int
    poids_g: int
    prix: float


class VenteOffline(BaseModel):
    type: str = "vente"
    montant: float
    paiement: str = "especes"
    client_id: Optional[int] = None
    marche_id: Optional[int] = None
    lignes: List[LigneVenteOffline] = []


@router.get("/status")
async def statut_sync(token: str = Depends(verifier_token)):
    """État de la queue offline. Ne doit jamais échouer : si Redis est
    indisponible, on répond en mode dégradé plutôt qu'en erreur (le frontend
    interprète une erreur comme « backend injoignable » = hors ligne)."""
    try:
        return await get_sync_status()
    except Exception:
        logger.exception("Erreur lecture statut sync")
        return {"status": "redis_unavailable", "queue_size": 0}


@router.post("/")
async def lancer_sync(db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    """Rejoue toutes les opérations en attente dans la queue offline."""
    try:
        return await sync_queue(db)
    except Exception:
        logger.exception("Erreur lors de la sync offline")
        return {"synced": 0, "errors": 0, "detail": "Redis indisponible — rien à synchroniser"}


@router.post("/enqueue")
async def enqueue(vente: VenteOffline, token: str = Depends(verifier_token)):
    """Met une vente terrain en file d'attente (utilisée en mode dégradé)."""
    op_id = await enqueue_vente(vente.model_dump())
    return {"queued": True, "id": op_id}
