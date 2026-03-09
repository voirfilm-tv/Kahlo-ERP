"""
KAHLO CAFÉ — Router Stock
CRUD lots + alertes + stats
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database import get_db
from models import Lot, Fournisseur
from services.ia import calculer_epuisement, recommander_assortiment

router = APIRouter()


# ============================================================
#  SCHEMAS
# ============================================================

class LotCreate(BaseModel):
    fournisseur_id: int
    origine: str
    numero_lot: str
    stock_kg: float
    seuil_alerte_kg: float = 3.0
    prix_achat_kg: float
    prix_vente_kg: float
    date_arrivee: Optional[datetime] = None
    dlc: Optional[datetime] = None
    notes_degustation: Optional[str] = None

class LotUpdate(BaseModel):
    stock_kg: Optional[float] = None
    seuil_alerte_kg: Optional[float] = None
    prix_vente_kg: Optional[float] = None
    notes_degustation: Optional[str] = None
    actif: Optional[bool] = None

class AjustementStock(BaseModel):
    lot_id: int
    delta_kg: float   # positif = entrée, négatif = sortie
    motif: str        # "vente", "commande_fournisseur", "correction"


# ============================================================
#  ROUTES
# ============================================================

@router.get("/")
async def get_lots(
    actif: bool = True,
    critique_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Liste tous les lots avec calculs enrichis"""
    result = await db.execute(
        select(Lot).where(Lot.actif == actif).order_by(Lot.origine)
    )
    lots = result.scalars().all()

    enriched = []
    for lot in lots:
        data = {
            "id": lot.id,
            "origine": lot.origine,
            "numero_lot": lot.numero_lot,
            "fournisseur_id": lot.fournisseur_id,
            "stock_kg": lot.stock_kg,
            "seuil_alerte_kg": lot.seuil_alerte_kg,
            "prix_achat_kg": lot.prix_achat_kg,
            "prix_vente_kg": lot.prix_vente_kg,
            "marge_pct": lot.marge_pct,
            "est_critique": lot.est_critique,
            "date_arrivee": lot.date_arrivee,
            "dlc": lot.dlc,
            "notes_degustation": lot.notes_degustation,
        }
        enriched.append(data)

    if critique_only:
        enriched = [l for l in enriched if l["est_critique"]]

    return enriched


@router.get("/stats")
async def get_stats_stock(db: AsyncSession = Depends(get_db)):
    """Stats globales du stock"""
    result = await db.execute(select(Lot).where(Lot.actif == True))
    lots = result.scalars().all()

    total_kg = sum(l.stock_kg for l in lots)
    valeur_achat = sum(l.stock_kg * l.prix_achat_kg for l in lots)
    valeur_vente = sum(l.stock_kg * l.prix_vente_kg for l in lots)
    critiques = [l for l in lots if l.est_critique]
    marge_moy = sum(l.marge_pct for l in lots) / len(lots) if lots else 0

    return {
        "total_kg": round(total_kg, 2),
        "nb_origines": len(lots),
        "valeur_achat": round(valeur_achat, 2),
        "valeur_vente": round(valeur_vente, 2),
        "nb_critiques": len(critiques),
        "origines_critiques": [l.origine for l in critiques],
        "marge_moyenne_pct": round(marge_moy),
    }


@router.get("/{lot_id}")
async def get_lot(lot_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lot).where(Lot.id == lot_id))
    lot = result.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    return lot


@router.post("/")
async def create_lot(data: LotCreate, db: AsyncSession = Depends(get_db)):
    lot = Lot(**data.model_dump())
    db.add(lot)
    await db.flush()
    return {"id": lot.id, "message": "Lot créé", "numero_lot": lot.numero_lot}


@router.patch("/{lot_id}")
async def update_lot(lot_id: int, data: LotUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lot).where(Lot.id == lot_id))
    lot = result.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(lot, field, value)
    return {"message": "Lot mis à jour"}


@router.post("/ajustement")
async def ajuster_stock(data: AjustementStock, db: AsyncSession = Depends(get_db)):
    """Ajustement manuel du stock (entrée ou sortie)"""
    result = await db.execute(select(Lot).where(Lot.id == data.lot_id))
    lot = result.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")

    lot.stock_kg = max(0, lot.stock_kg + data.delta_kg)

    return {
        "message": "Stock ajusté",
        "nouveau_stock": lot.stock_kg,
        "est_critique": lot.est_critique
    }


@router.get("/{lot_id}/prevision")
async def prevision_epuisement(
    lot_id: int,
    ventes_mois_kg: float = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Prévision d'épuisement basée sur la vitesse de vente"""
    result = await db.execute(select(Lot).where(Lot.id == lot_id))
    lot = result.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")

    prevision = calculer_epuisement(lot.stock_kg, ventes_mois_kg)
    return {
        "lot_id": lot_id,
        "origine": lot.origine,
        "stock_actuel": lot.stock_kg,
        **prevision
    }


@router.delete("/{lot_id}")
async def archive_lot(lot_id: int, db: AsyncSession = Depends(get_db)):
    """Archive un lot (soft delete)"""
    result = await db.execute(select(Lot).where(Lot.id == lot_id))
    lot = result.scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot introuvable")
    lot.actif = False
    return {"message": "Lot archivé"}
