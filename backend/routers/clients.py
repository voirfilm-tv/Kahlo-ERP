"""
KAHLO CAFÉ — Router Clients / CRM
CRUD complet + tampons fidélité + alertes + sync Brevo
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta

from database import get_db
from models import Client, Commande, StatutCommande, ProfilKahlo, Mouture
from services.brevo import sync_client_brevo

router = APIRouter()


# ============================================================
#  SCHEMAS
# ============================================================

class ClientCreate(BaseModel):
    prenom: str
    nom: str
    email: Optional[str] = None
    telephone: Optional[str] = None
    ville: Optional[str] = None
    anniversaire: Optional[datetime] = None
    profil: Optional[ProfilKahlo] = None
    mouture_pref: Optional[str] = None
    quantite_hab_g: int = 250
    notes: Optional[str] = None

class ClientUpdate(BaseModel):
    prenom: Optional[str] = None
    nom: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    ville: Optional[str] = None
    anniversaire: Optional[datetime] = None
    profil: Optional[ProfilKahlo] = None
    mouture_pref: Optional[str] = None
    quantite_hab_g: Optional[int] = None
    notes: Optional[str] = None
    vip: Optional[bool] = None


def _serialise_client(c: Client, inclure_commandes: bool = False) -> dict:
    commandes = c.commandes if inclure_commandes else []
    total = sum(cmd.montant_total for cmd in commandes if cmd.statut != StatutCommande.annulee)
    nb    = len([cmd for cmd in commandes if cmd.statut == StatutCommande.remise])
    derniere = None
    if commandes:
        dates = [cmd.date_commande for cmd in commandes if cmd.date_commande]
        derniere = max(dates).isoformat() if dates else None

    return {
        "id":              c.id,
        "prenom":          c.prenom,
        "nom":             c.nom,
        "email":           c.email,
        "telephone":       c.telephone,
        "ville":           c.ville,
        "anniversaire":    c.anniversaire.isoformat() if c.anniversaire else None,
        "profil":          c.profil,
        "mouture_pref":    c.mouture_pref,
        "quantite_hab_g":  c.quantite_hab_g,
        "tampons":         c.tampons,
        "vip":             c.vip,
        "notes":           c.notes,
        "total_achats":    round(total, 2),
        "nb_achats":       nb,
        "derniere_commande": derniere,
        "created_at":      c.created_at.isoformat() if c.created_at else None,
    }


# ============================================================
#  ROUTES
# ============================================================

@router.get("/")
async def get_clients(
    search: Optional[str] = Query(None),
    vip: Optional[bool] = Query(None),
    profil: Optional[ProfilKahlo] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Client)
        .options(selectinload(Client.commandes))
        .order_by(Client.nom)
    )
    if search:
        q = f"%{search}%"
        query = query.where(
            (Client.prenom.ilike(q)) |
            (Client.nom.ilike(q)) |
            (Client.email.ilike(q)) |
            (Client.ville.ilike(q))
        )
    if vip is not None:
        query = query.where(Client.vip == vip)
    if profil:
        query = query.where(Client.profil == profil)

    result = await db.execute(query)
    clients = result.scalars().all()
    return [_serialise_client(c, inclure_commandes=True) for c in clients]


@router.get("/alertes")
async def get_alertes(db: AsyncSession = Depends(get_db)):
    """
    Retourne :
    - clients dont l'anniversaire est dans les 14 prochains jours
    - clients inactifs depuis plus de 45 jours
    """
    result = await db.execute(
        select(Client).options(selectinload(Client.commandes))
    )
    clients = result.scalars().all()

    aujourd_hui = datetime.now()
    dans_14j     = aujourd_hui + timedelta(days=14)

    anniversaires = []
    for c in clients:
        if not c.anniversaire:
            continue
        anniv = c.anniversaire.replace(year=aujourd_hui.year)
        # Si déjà passé cette année, on prend l'année suivante
        if anniv < aujourd_hui:
            anniv = anniv.replace(year=aujourd_hui.year + 1)
        if aujourd_hui <= anniv <= dans_14j:
            jours = (anniv - aujourd_hui).days
            anniversaires.append({
                **_serialise_client(c),
                "jours_avant_anniversaire": jours,
                "date_anniversaire": anniv.isoformat(),
            })

    inactifs = []
    seuil_inactivite = aujourd_hui - timedelta(days=45)
    for c in clients:
        if not c.commandes:
            continue
        dates = [cmd.date_commande for cmd in c.commandes if cmd.date_commande]
        if not dates:
            continue
        derniere = max(dates)
        if derniere < seuil_inactivite:
            inactifs.append({
                **_serialise_client(c, inclure_commandes=True),
                "jours_inactif": (aujourd_hui - derniere).days,
            })

    return {
        "anniversaires": anniversaires,
        "inactifs": inactifs,
        "total_alertes": len(anniversaires) + len(inactifs),
    }


@router.get("/{client_id}")
async def get_client(client_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Client)
        .options(selectinload(Client.commandes))
        .where(Client.id == client_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Client introuvable")
    return _serialise_client(c, inclure_commandes=True)


@router.post("/", status_code=201)
async def creer_client(data: ClientCreate, db: AsyncSession = Depends(get_db)):
    # Vérifier unicité email
    if data.email:
        existe = await db.execute(select(Client).where(Client.email == data.email))
        if existe.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email déjà utilisé")

    client = Client(**data.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)

    # Sync Brevo en arrière-plan (ne bloque pas si Brevo est down)
    try:
        await sync_client_brevo(client)
        await db.commit()
    except Exception:
        pass

    return _serialise_client(client)


@router.patch("/{client_id}")
async def modifier_client(
    client_id: int,
    data: ClientUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    for key, value in data.model_dump(exclude_none=True).items():
        setattr(client, key, value)

    await db.commit()
    await db.refresh(client)

    try:
        await sync_client_brevo(client)
    except Exception:
        pass

    return _serialise_client(client)


@router.post("/{client_id}/tampon")
async def ajouter_tampon(client_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    client.tampons = (client.tampons or 0) + 1

    # Passage automatique VIP si 5 achats remis
    result_cmds = await db.execute(
        select(func.count()).where(
            Commande.client_id == client_id,
            Commande.statut == StatutCommande.remise
        )
    )
    nb_achats = result_cmds.scalar()
    if nb_achats >= 5:
        client.vip = True

    await db.commit()
    return {"tampons": client.tampons, "vip": client.vip}


@router.post("/{client_id}/tampon/reset")
async def reset_tampons(client_id: int, db: AsyncSession = Depends(get_db)):
    """Remet les tampons à 0 après une récompense distribuée"""
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    client.tampons = 0
    await db.commit()
    return {"message": "Tampons réinitialisés", "tampons": 0}


@router.delete("/{client_id}", status_code=204)
async def supprimer_client(client_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")
    await db.delete(client)
    await db.commit()
