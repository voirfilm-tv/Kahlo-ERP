"""KAHLO CAFÉ — Router Calendrier"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db
from models import Evenement, TypeEvenement
from services.calendrier import (
    creer_evenement_caldav, sync_caldav_vers_db,
    creer_evenement_google, sync_google_vers_db
)
from routers.auth import verifier_token

router = APIRouter()


class EvenementCreate(BaseModel):
    type: TypeEvenement
    titre: str
    date_debut: datetime
    date_fin: Optional[datetime] = None
    all_day: bool = True
    notes: Optional[str] = None
    marche_id: Optional[int] = None
    commande_id: Optional[int] = None
    fournisseur_id: Optional[int] = None


@router.get("/")
async def get_evenements(
    mois: Optional[int] = None,
    annee: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token)
):
    query = select(Evenement).order_by(Evenement.date_debut)
    if mois and annee:
        from sqlalchemy import extract
        query = query.where(
            extract("month", Evenement.date_debut) == mois,
            extract("year", Evenement.date_debut) == annee,
        )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", status_code=201)
async def creer_evenement(data: EvenementCreate, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    ev = Evenement(**data.model_dump())
    db.add(ev)
    await db.flush()

    # Sync CalDAV automatique
    uid = await creer_evenement_caldav({
        "titre": ev.titre,
        "date_debut": ev.date_debut,
        "date_fin": ev.date_fin or ev.date_debut,
        "notes": ev.notes,
    })
    if uid:
        ev.caldav_uid = uid

    await db.commit()
    await db.refresh(ev)
    return ev


@router.delete("/{eid}")
async def supprimer_evenement(eid: int, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    from services.calendrier import supprimer_evenement_caldav
    result = await db.execute(select(Evenement).where(Evenement.id == eid))
    ev = result.scalar_one_or_none()
    if not ev:
        raise HTTPException(404, "Événement introuvable")

    if ev.caldav_uid:
        await supprimer_evenement_caldav(ev.caldav_uid)

    await db.delete(ev)
    await db.commit()
    return {"ok": True}


@router.post("/sync/caldav")
async def sync_caldav(db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    """Force une sync bidirectionnelle CalDAV"""
    nouveaux = await sync_caldav_vers_db(db)
    return {"importes": len(nouveaux), "evenements": nouveaux}


@router.post("/sync/google")
async def sync_google(credentials: dict, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    """Force une sync Google Calendar (nécessite token OAuth)"""
    nouveaux = await sync_google_vers_db(credentials, db)
    return {"importes": len(nouveaux)}
