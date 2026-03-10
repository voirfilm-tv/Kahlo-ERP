"""
KAHLO CAFÉ — Router Commandes
CRUD complet + SumUp checkout + notifications Brevo + factures PDF
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import random
import string
import os

from database import get_db
from models import Commande, LigneCommande, StatutCommande, Client, Lot
from services.stock import decrementer_stock
from services.brevo import notifier_commande_prete, notifier_client_paiement_recu
from services.factures import generer_facture_pdf
from services.sumup import creer_checkout, get_checkout
from routers.auth import verifier_token

router = APIRouter()


# ============================================================
#  SCHEMAS
# ============================================================

class LigneCreate(BaseModel):
    lot_id: int
    poids_g: int
    mouture: str
    prix_unitaire: float

class CommandeCreate(BaseModel):
    client_id: int
    marche_id: Optional[int] = None
    lignes: List[LigneCreate]
    date_remise_prev: Optional[datetime] = None
    paiement_mode: str = "sumup"
    notes: Optional[str] = None

class ChangerStatut(BaseModel):
    statut: StatutCommande
    notes: Optional[str] = None


# ============================================================
#  HELPERS
# ============================================================

def generer_numero() -> str:
    seq = ''.join(random.choices(string.digits, k=4))
    return f"CMD-{seq}"

def _serialise_commande(c: Commande, avec_lignes: bool = False) -> dict:
    d = {
        "id":               c.id,
        "numero":           c.numero,
        "client_id":        c.client_id,
        "marche_id":        c.marche_id,
        "statut":           c.statut,
        "montant_total":    c.montant_total,
        "paiement_mode":    c.paiement_mode,
        "sumup_checkout_id": c.sumup_checkout_id,
        "sumup_transaction_code": c.sumup_transaction_code,
        "sumup_paid":       c.sumup_paid,
        "facture_generee":  c.facture_generee,
        "date_commande":    c.date_commande.isoformat() if c.date_commande else None,
        "date_remise_prev": c.date_remise_prev.isoformat() if c.date_remise_prev else None,
        "date_remise_reelle": c.date_remise_reelle.isoformat() if c.date_remise_reelle else None,
        "notes":            c.notes,
    }
    if avec_lignes:
        d["lignes"] = [
            {
                "id": l.id,
                "lot_id": l.lot_id,
                "poids_g": l.poids_g,
                "mouture": l.mouture,
                "prix_unitaire": l.prix_unitaire,
            }
            for l in c.lignes
        ]
    return d


# ============================================================
#  ROUTES LECTURE
# ============================================================

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    result = await db.execute(select(Commande))
    commandes = result.scalars().all()
    actives = [c for c in commandes if c.statut != StatutCommande.annulee]
    return {
        "total":          len(actives),
        "en_attente":     len([c for c in actives if c.statut == StatutCommande.en_attente]),
        "pretes":         len([c for c in actives if c.statut == StatutCommande.prete]),
        "remises":        len([c for c in actives if c.statut == StatutCommande.remise]),
        "ca_engage":      round(sum(c.montant_total for c in actives), 2),
    }


@router.get("/")
async def get_commandes(
    statut: Optional[StatutCommande] = None,
    marche_id: Optional[int] = None,
    client_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token)
):
    query = (
        select(Commande)
        .options(selectinload(Commande.lignes))
        .order_by(Commande.date_commande.desc())
    )
    if statut:
        query = query.where(Commande.statut == statut)
    if marche_id:
        query = query.where(Commande.marche_id == marche_id)
    if client_id:
        query = query.where(Commande.client_id == client_id)

    result = await db.execute(query)
    return [_serialise_commande(c, avec_lignes=True) for c in result.scalars().all()]


@router.get("/{commande_id}")
async def get_commande(commande_id: int, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    result = await db.execute(
        select(Commande)
        .options(selectinload(Commande.lignes))
        .where(Commande.id == commande_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return _serialise_commande(c, avec_lignes=True)


# ============================================================
#  CRÉATION
# ============================================================

@router.post("/", status_code=201)
async def creer_commande(data: CommandeCreate, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    # Vérifier client
    client = await db.get(Client, data.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable")

    # Vérifier les lots et le stock disponible (avec verrouillage pour éviter les race conditions)
    for ligne in data.lignes:
        result_lot = await db.execute(
            select(Lot).where(Lot.id == ligne.lot_id).with_for_update()
        )
        lot = result_lot.scalar_one_or_none()
        if not lot:
            raise HTTPException(status_code=404, detail=f"Lot {ligne.lot_id} introuvable")
        if not lot.actif:
            raise HTTPException(status_code=400, detail=f"Le lot {lot.origine} est inactif")
        poids_kg = ligne.poids_g / 1000
        if lot.stock_kg < poids_kg:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuffisant pour {lot.origine} : {lot.stock_kg}kg disponible, {poids_kg}kg demandé"
            )

    # Calculer total
    total = round(sum(l.prix_unitaire for l in data.lignes), 2)

    # Créer la commande
    commande = Commande(
        numero=generer_numero(),
        client_id=data.client_id,
        marche_id=data.marche_id,
        montant_total=total,
        paiement_mode=data.paiement_mode,
        date_remise_prev=data.date_remise_prev,
        notes=data.notes,
    )
    db.add(commande)
    await db.flush()  # obtenir l'ID

    # Ajouter les lignes
    for ligne_data in data.lignes:
        ligne = LigneCommande(
            commande_id=commande.id,
            lot_id=ligne_data.lot_id,
            poids_g=ligne_data.poids_g,
            mouture=ligne_data.mouture,
            prix_unitaire=ligne_data.prix_unitaire,
        )
        db.add(ligne)

    # Si paiement en espèces : décrémenter stock immédiatement
    if data.paiement_mode == "especes":
        for ligne_data in data.lignes:
            await decrementer_stock(db, ligne_data.lot_id, ligne_data.poids_g / 1000)

    # Si SumUp : créer le checkout (lien de paiement)
    if data.paiement_mode == "sumup":
        try:
            checkout = await creer_checkout(
                commande_id=commande.id,
                montant=total,
                description=f"Commande {commande.numero} — Kahlo Café",
                email_client=client.email,
            )
            commande.sumup_checkout_id = checkout["checkout_id"]
        except Exception:
            # On crée la commande même si le checkout SumUp échoue
            pass

    await db.commit()
    await db.refresh(commande)

    return {
        "id": commande.id,
        "numero": commande.numero,
        "montant_total": total,
        "sumup_checkout_id": commande.sumup_checkout_id,
        "statut": commande.statut,
    }


# ============================================================
#  CHANGEMENT DE STATUT
# ============================================================

@router.patch("/{commande_id}/statut")
async def changer_statut(
    commande_id: int,
    data: ChangerStatut,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(verifier_token)
):
    result = await db.execute(
        select(Commande)
        .options(selectinload(Commande.lignes))
        .where(Commande.id == commande_id)
    )
    commande = result.scalar_one_or_none()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    ancien_statut = commande.statut
    commande.statut = data.statut

    # En attente → Prête : notifier le client
    if data.statut == StatutCommande.prete and ancien_statut == StatutCommande.en_attente:
        try:
            await notifier_commande_prete(commande)
        except Exception:
            pass

    # → Remise : date réelle + facture PDF + tampon fidélité
    elif data.statut == StatutCommande.remise:
        commande.date_remise_reelle = datetime.now()

        # Générer la facture PDF
        try:
            await generer_facture_pdf(db, commande)
            commande.facture_generee = True
        except Exception:
            pass

        # Décrémenter stock si paiement espèces (SumUp le fait via webhook)
        if commande.paiement_mode == "especes":
            for ligne in commande.lignes:
                await decrementer_stock(db, ligne.lot_id, ligne.poids_g / 1000)

        # Tampon fidélité
        client = await db.get(Client, commande.client_id)
        if client:
            client.tampons = (client.tampons or 0) + 1
            # Auto-VIP à 5 achats
            nb_achats = len([c for c in client.commandes if c.statut == StatutCommande.remise])
            if nb_achats >= 5:
                client.vip = True

    # → Annulée : recréditer stock si déjà décrémenté
    elif data.statut == StatutCommande.annulee:
        if commande.sumup_paid or commande.paiement_mode == "especes":
            for ligne in commande.lignes:
                await decrementer_stock(db, ligne.lot_id, -(ligne.poids_g / 1000))

    await db.commit()
    return {"message": "Statut mis à jour", "statut": data.statut}


# ============================================================
#  ACTIONS SPÉCIALES
# ============================================================

@router.post("/{commande_id}/notifier-prete")
async def notifier_prete(commande_id: int, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    """Envoie (ou renvoie) la notification Brevo 'commande prête'"""
    result = await db.execute(
        select(Commande)
        .options(selectinload(Commande.lignes))
        .where(Commande.id == commande_id)
    )
    commande = result.scalar_one_or_none()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    try:
        await notifier_commande_prete(commande)
        return {"message": "Notification envoyée"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Brevo : {str(e)}")


@router.post("/{commande_id}/checkout-sumup")
async def creer_lien_sumup(commande_id: int, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    """Crée ou recrée un lien de paiement SumUp"""
    result = await db.execute(
        select(Commande)
        .options(selectinload(Commande.lignes))
        .where(Commande.id == commande_id)
    )
    commande = result.scalar_one_or_none()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    client = await db.get(Client, commande.client_id)

    try:
        checkout = await creer_checkout(
            commande_id=commande.id,
            montant=commande.montant_total,
            description=f"Commande {commande.numero} — Kahlo Café",
            email_client=client.email if client else None,
        )
        commande.sumup_checkout_id = checkout["checkout_id"]
        await db.commit()
        return checkout
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur SumUp : {str(e)}")


@router.get("/{commande_id}/statut-paiement")
async def statut_paiement(commande_id: int, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    """Interroge SumUp pour connaître l'état du checkout"""
    commande = await db.get(Commande, commande_id)
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    if not commande.sumup_checkout_id:
        return {"sumup_paid": commande.sumup_paid, "checkout_id": None, "statut_sumup": None}

    try:
        checkout = await get_checkout(commande.sumup_checkout_id)
        return {
            "sumup_paid":    commande.sumup_paid,
            "checkout_id":   commande.sumup_checkout_id,
            "statut_sumup":  checkout.get("status"),
        }
    except Exception:
        return {"sumup_paid": commande.sumup_paid, "checkout_id": commande.sumup_checkout_id, "statut_sumup": "inconnu"}


@router.get("/{commande_id}/facture")
async def telecharger_facture(commande_id: int, db: AsyncSession = Depends(get_db), token: str = Depends(verifier_token)):
    """Génère (si besoin) et retourne la facture PDF"""
    result = await db.execute(
        select(Commande)
        .options(selectinload(Commande.lignes))
        .where(Commande.id == commande_id)
    )
    commande = result.scalar_one_or_none()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    path = await generer_facture_pdf(db, commande)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=500, detail="Impossible de générer la facture")

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"facture-{commande.numero}.pdf"
    )
