"""KAHLO CAFÉ — Router Fournisseurs"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import Fournisseur

router = APIRouter()


class FournisseurCreate(BaseModel):
    nom: str
    email: Optional[str] = None
    telephone: Optional[str] = None
    pays: Optional[str] = None
    delai_moyen: int = 10
    notes: Optional[str] = None


@router.get("/")
async def get_fournisseurs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fournisseur).order_by(Fournisseur.score.desc()))
    fournisseurs = result.scalars().all()
    return fournisseurs


@router.post("/", status_code=201)
async def creer_fournisseur(data: FournisseurCreate, db: AsyncSession = Depends(get_db)):
    f = Fournisseur(**data.model_dump())
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return f


@router.patch("/{fid}/score")
async def noter_fournisseur(fid: int, score: float, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fournisseur).where(Fournisseur.id == fid))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(404, "Fournisseur introuvable")
    f.score = max(0, min(5, score))
    await db.commit()
    return {"score": f.score}
