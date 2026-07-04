"""KAHLO CAFÉ — Router Calendrier"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import os
import uuid
import plistlib
import logging

from jose import jwt, JWTError

from database import get_db
from models import Evenement, TypeEvenement
from services.calendrier import (
    creer_evenement_caldav, sync_caldav_vers_db,
    creer_evenement_google, sync_google_vers_db
)
from services import caldav_admin
from routers.auth import verifier_token, require_admin, SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
#  CONNEXION DES APPAREILS (CalDAV zéro-config)
#  L'ERP gère le serveur et les identifiants tout seul :
#  l'utilisateur copie l'URL/identifiants ou scanne un QR code.
# ============================================================

def _base_publique(request: Request) -> str:
    """URL de base vue par les appareils : PUBLIC_BASE_URL si configurée,
    sinon l'adresse par laquelle l'utilisateur accède à l'ERP."""
    configuree = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configuree:
        return configuree
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}"


def _infos_connexion(request: Request) -> dict:
    user, password = caldav_admin.identifiants_caldav()
    base = _base_publique(request)
    return {
        "url": f"{base}/caldav/{user}/",
        "username": user,
        "password": password,
        "base": base,
    }


@router.get("/connexion")
async def connexion_appareils(request: Request, admin: dict = Depends(require_admin)):
    """Tout ce qu'il faut pour connecter un appareil (admin uniquement —
    le mot de passe est retourné en clair car il est nécessaire à la
    configuration de l'appareil ; il est géré/généré par l'ERP)."""
    infos = _infos_connexion(request)
    return {
        "url": infos["url"],
        "username": infos["username"],
        "password": infos["password"],
        "gestion_auto": caldav_admin.gestion_auto_possible(),
        "frequence_secondes": int(os.getenv("CALDAV_INTERVAL_SECONDS", "0") or 0)
        or int(os.getenv("CALDAV_INTERVAL", "5") or 5) * 60,
    }


@router.post("/connexion/regenerer")
async def regenerer_mot_de_passe(request: Request, admin: dict = Depends(require_admin)):
    """Nouveau mot de passe CalDAV (les appareils déjà connectés devront
    être reconfigurés)."""
    try:
        nouveau = caldav_admin.regenerer_mot_de_passe()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    infos = _infos_connexion(request)
    return {"password": nouveau, "url": infos["url"], "username": infos["username"]}


@router.post("/connexion/lien-apple")
async def generer_lien_apple(request: Request, admin: dict = Depends(require_admin)):
    """Lien signé temporaire (15 min) vers le profil Apple .mobileconfig.
    Encodé en QR côté interface : scanner → le compte calendrier s'installe
    tout seul sur iPhone/iPad/Mac."""
    token = jwt.encode(
        {
            "typ": "caldav-profile",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
        SECRET_KEY, algorithm=ALGORITHM,
    )
    base = _base_publique(request)
    return {
        "url": f"{base}/api/calendrier/profil-apple?token={token}",
        "expire_minutes": 15,
    }


@router.get("/profil-apple")
async def profil_apple(request: Request, token: str = Query(...)):
    """Profil de configuration Apple (.mobileconfig) avec le compte CalDAV
    pré-rempli. Accessible sans session (le téléphone qui scanne le QR n'en
    a pas) mais protégé par un jeton signé à durée courte."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("typ") != "caldav-profile":
            raise JWTError("mauvais type de jeton")
    except JWTError:
        raise HTTPException(status_code=403, detail="Lien expiré ou invalide — régénérez le QR code")

    infos = _infos_connexion(request)
    base = urlparse(infos["base"])
    use_ssl = base.scheme == "https"
    port = base.port or (443 if use_ssl else 80)

    compte = {
        "CalDAVAccountDescription": "Kahlo Café — Calendrier",
        "CalDAVHostName": base.hostname or "",
        "CalDAVPort": port,
        "CalDAVUseSSL": use_ssl,
        "CalDAVUsername": infos["username"],
        "CalDAVPassword": infos["password"],
        "CalDAVPrincipalURL": f"/caldav/{infos['username']}/",
        "PayloadDescription": "Compte calendrier Kahlo Café (CalDAV)",
        "PayloadDisplayName": "Calendrier Kahlo Café",
        "PayloadIdentifier": "fr.kahlocafe.erp.caldav.account",
        "PayloadType": "com.apple.caldav.account",
        "PayloadUUID": str(uuid.uuid4()),
        "PayloadVersion": 1,
    }
    profil = {
        "PayloadContent": [compte],
        "PayloadDescription": "Ajoute le calendrier Kahlo Café à cet appareil",
        "PayloadDisplayName": "Kahlo Café — Calendrier",
        "PayloadIdentifier": "fr.kahlocafe.erp.caldav",
        "PayloadRemovalDisallowed": False,
        "PayloadType": "Configuration",
        "PayloadUUID": str(uuid.uuid4()),
        "PayloadVersion": 1,
    }
    return Response(
        content=plistlib.dumps(profil),
        media_type="application/x-apple-aspen-config",
        headers={"Content-Disposition": 'attachment; filename="kahlo-calendrier.mobileconfig"'},
    )


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
    debut: Optional[datetime] = None,
    fin: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token)
):
    """Liste les événements. Filtrable par mois/annee OU par plage debut/fin."""
    query = select(Evenement).order_by(Evenement.date_debut)
    if mois and annee:
        from sqlalchemy import extract
        query = query.where(
            extract("month", Evenement.date_debut) == mois,
            extract("year", Evenement.date_debut) == annee,
        )
    else:
        if debut:
            query = query.where(Evenement.date_debut >= debut)
        if fin:
            # Inclure toute la journée de fin
            query = query.where(Evenement.date_debut < fin + timedelta(days=1))
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
