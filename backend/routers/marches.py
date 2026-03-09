"""KAHLO CAFÉ — Router Marchés"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db
from models import Marche, StatutMarche
from services.calendrier import creer_evenement_caldav, creer_evenement_google

router = APIRouter()


class MarcheCreate(BaseModel):
    nom: str
    lieu: Optional[str] = None
    date: datetime
    frais_prevus: float = 0
    km_aller_retour: Optional[float] = None
    notes: Optional[str] = None


class BilanMarche(BaseModel):
    ca_realise: float
    stock_emmene_kg: float
    stock_ramene_kg: float
    frais_reels: float
    nb_clients: Optional[int] = None
    meteo: Optional[str] = None
    notes: Optional[str] = None


@router.get("/")
async def get_marches(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Marche).order_by(Marche.date.desc()))
    return result.scalars().all()


@router.get("/a_venir")
async def get_marches_a_venir(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Marche).where(
            Marche.date >= datetime.now(),
            Marche.statut.in_([StatutMarche.confirme, StatutMarche.tentative])
        ).order_by(Marche.date)
    )
    return result.scalars().all()


@router.post("/", status_code=201)
async def creer_marche(data: MarcheCreate, db: AsyncSession = Depends(get_db)):
    marche = Marche(**data.model_dump())
    db.add(marche)
    await db.flush()

    # Sync automatique CalDAV
    uid = await creer_evenement_caldav({
        "titre": f"🏪 {marche.nom}",
        "date_debut": marche.date,
        "lieu": marche.lieu or "",
        "notes": marche.notes or "",
    })
    if uid:
        marche.caldav_event_id = uid

    await db.commit()
    await db.refresh(marche)
    return marche


@router.patch("/{mid}/statut")
async def changer_statut(mid: int, statut: StatutMarche, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Marche).where(Marche.id == mid))
    marche = result.scalar_one_or_none()
    if not marche:
        raise HTTPException(404, "Marché introuvable")
    marche.statut = statut
    await db.commit()
    return {"statut": statut}


@router.post("/{mid}/bilan")
async def saisir_bilan(mid: int, bilan: BilanMarche, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Marche).where(Marche.id == mid))
    marche = result.scalar_one_or_none()
    if not marche:
        raise HTTPException(404, "Marché introuvable")

    for field, value in bilan.model_dump(exclude_none=True).items():
        setattr(marche, field, value)
    marche.statut = StatutMarche.passe

    await db.commit()
    return {
        "ca": marche.ca_realise,
        "marge_nette": marche.marge_nette,
        "taux_ecoulement": marche.taux_ecoulement,
    }


@router.get("/{mid}/analyse-ia")
async def analyse_ia_marche(mid: int, db: AsyncSession = Depends(get_db)):
    from services.ia import analyser_marche
    result = await db.execute(select(Marche).where(Marche.id == mid))
    marche = result.scalar_one_or_none()
    if not marche or not marche.ca_realise:
        raise HTTPException(400, "Bilan non disponible pour ce marché")

    analyse = await analyser_marche({
        "nom": marche.nom,
        "date": str(marche.date.date()),
        "ca": marche.ca_realise,
        "stock_emmene": marche.stock_emmene_kg,
        "stock_ramene": marche.stock_ramene_kg,
        "taux_ecoulement": marche.taux_ecoulement,
        "frais": marche.frais_reels,
        "marge_nette": marche.marge_nette,
        "meteo": marche.meteo,
        "notes": marche.notes,
    })
    return {"analyse": analyse}
