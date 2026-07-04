"""
KAHLO CAFÉ — Router SumUp (ventes réelles)
Statut de connexion, synchronisation des transactions et
statistiques de CA réel (brut, frais, net) alimentées par l'API SumUp.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
import os
import logging

from database import get_db
from models import TransactionSumUp
from services import ventes_sumup
from services.sumup import verifier_connexion
from routers.auth import verifier_token

logger = logging.getLogger(__name__)

router = APIRouter()


class SyncRequest(BaseModel):
    jours_historique: int = Field(default=90, ge=1, le=730)


@router.get("/statut")
async def statut_sumup(db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    """État de l'intégration SumUp : clé configurée, connexion, volume importé."""
    configure = bool(os.getenv("SUMUP_API_KEY"))

    r = await db.execute(select(func.count()).select_from(TransactionSumUp))
    nb_transactions = r.scalar() or 0
    r = await db.execute(select(func.max(TransactionSumUp.created_at)))
    derniere_sync = r.scalar()

    connexion_ok = None
    if configure:
        connexion_ok = await verifier_connexion()

    return {
        "configure": configure,
        "connexion_ok": connexion_ok,
        "webhook_configure": bool(os.getenv("SUMUP_WEBHOOK_SECRET")),
        "nb_transactions": nb_transactions,
        "derniere_sync": derniere_sync.isoformat() if derniere_sync else None,
    }


@router.post("/sync")
async def synchroniser_ventes(
    data: Optional[SyncRequest] = None,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token),
):
    """Importe les nouvelles transactions SumUp (idempotent) et met à jour le stock."""
    if not os.getenv("SUMUP_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="SumUp non configuré — ajoutez votre clé API dans Paramètres → SumUp"
        )
    try:
        return await ventes_sumup.synchroniser(db, (data or SyncRequest()).jours_historique)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Erreur de synchronisation SumUp")
        raise HTTPException(status_code=502, detail="Impossible de joindre l'API SumUp — vérifiez votre clé")


@router.get("/ventes")
async def lister_ventes(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    jours: int = Query(30, ge=1, le=730),
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token),
):
    """Ventes SumUp importées + statistiques agrégées sur la période."""
    depuis = datetime.now() - timedelta(days=jours)
    encaissees = list(ventes_sumup._STATUTS_VENTE)

    # Stats agrégées (ventes encaissées uniquement)
    r = await db.execute(
        select(
            func.count().label("nb"),
            func.coalesce(func.sum(TransactionSumUp.montant), 0).label("brut"),
            func.coalesce(func.sum(TransactionSumUp.frais), 0).label("frais"),
        ).where(
            TransactionSumUp.statut.in_(encaissees),
            TransactionSumUp.date_transaction >= depuis,
        )
    )
    stats = r.one()

    # Répartition par type de paiement
    r = await db.execute(
        select(TransactionSumUp.payment_type, func.count(), func.coalesce(func.sum(TransactionSumUp.montant), 0))
        .where(
            TransactionSumUp.statut.in_(encaissees),
            TransactionSumUp.date_transaction >= depuis,
        )
        .group_by(TransactionSumUp.payment_type)
    )
    par_type = [{"type": row[0] or "inconnu", "nb": row[1], "montant": round(row[2], 2)} for row in r.all()]

    # Liste paginée (tous statuts, les remboursements restent visibles)
    r = await db.execute(
        select(TransactionSumUp)
        .where(TransactionSumUp.date_transaction >= depuis)
        .order_by(TransactionSumUp.date_transaction.desc())
        .offset(offset).limit(limit)
    )
    ventes = [
        {
            "id": t.id,
            "transaction_code": t.transaction_code,
            "montant": t.montant,
            "devise": t.devise,
            "frais": t.frais,
            "montant_net": round(t.montant_net, 2),
            "statut": t.statut,
            "payment_type": t.payment_type,
            "entry_mode": t.entry_mode,
            "produits": t.produits or [],
            "stock_traite": t.stock_traite,
            "stock_details": t.stock_details or [],
            "date_transaction": t.date_transaction.isoformat() if t.date_transaction else None,
        }
        for t in r.scalars().all()
    ]

    return {
        "stats": {
            "nb_ventes": stats.nb,
            "ca_brut": round(stats.brut, 2),
            "frais": round(stats.frais, 2),
            "ca_net": round(stats.brut - stats.frais, 2),
            "par_type": par_type,
            "periode_jours": jours,
        },
        "ventes": ventes,
    }
