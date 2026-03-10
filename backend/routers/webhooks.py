"""
KAHLO CAFÉ — SumUp Webhooks
Traitement des événements SumUp en temps réel
Doc : https://developer.sumup.com/api/webhooks
"""

from fastapi import APIRouter, Request, HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import hmac
import hashlib
import os
import logging

from database import get_db
from models import Commande, StatutCommande
from services.stock import decrementer_stock
from services.brevo import notifier_client_paiement_recu
from services.calendrier import creer_evenement_remise

router = APIRouter()
logger = logging.getLogger(__name__)

SUMUP_WEBHOOK_SECRET = os.getenv("SUMUP_WEBHOOK_SECRET", "")


def _verifier_signature(payload: bytes, signature: str) -> bool:
    """SumUp signe les webhooks avec HMAC-SHA256."""
    if not SUMUP_WEBHOOK_SECRET or not signature:
        return False
    sig = signature.replace("sha256=", "")
    expected = hmac.new(SUMUP_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


@router.post("/sumup")
async def sumup_webhook(
    request: Request,
    x_sumup_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    payload = await request.body()

    # Bloquer si le secret webhook n'est pas configuré (évite le contournement)
    if not SUMUP_WEBHOOK_SECRET:
        logger.error("SUMUP_WEBHOOK_SECRET non configure — webhook rejete")
        raise HTTPException(status_code=403, detail="Webhook non configure")

    if not _verifier_signature(payload, x_sumup_signature or ""):
        raise HTTPException(status_code=400, detail="Signature invalide")

    event = await request.json()
    event_type = event.get("event_type") or event.get("type")
    logger.info(f"SumUp webhook reçu: {event_type}")

    if event_type == "PAYMENT_STATUS_CHANGED":
        transaction = event.get("payload", {})
        statut = transaction.get("status")
        checkout_id = transaction.get("checkout_id") or transaction.get("id")

        if statut == "SUCCESSFUL":
            await handle_paiement_reussi(checkout_id, transaction, db)
        elif statut == "FAILED":
            logger.warning(f"Paiement SumUp échoué: {checkout_id}")
        elif statut in ("REFUNDED", "CANCELLED"):
            await handle_remboursement(checkout_id, db)

    elif event_type == "transaction.successful":
        await handle_vente_terminal(event.get("payload", {}), db)

    return {"received": True}


async def handle_paiement_reussi(checkout_id: str, transaction: dict, db: AsyncSession):
    result = await db.execute(
        select(Commande)
        .options(selectinload(Commande.lignes), selectinload(Commande.client), selectinload(Commande.marche))
        .where(Commande.sumup_checkout_id == checkout_id)
    )
    commande = result.scalar_one_or_none()
    if not commande:
        logger.warning(f"Commande introuvable pour SumUp checkout: {checkout_id}")
        return

    commande.sumup_paid = True
    commande.sumup_transaction_code = transaction.get("transaction_code", "")
    commande.statut = StatutCommande.en_attente

    for ligne in commande.lignes:
        await decrementer_stock(db, ligne.lot_id, ligne.poids_g / 1000)

    if commande.marche_id:
        await creer_evenement_remise(db, commande)

    await notifier_client_paiement_recu(commande)
    await db.commit()
    logger.info(f"Commande {commande.numero} payée via SumUp")


async def handle_remboursement(checkout_id: str, db: AsyncSession):
    result = await db.execute(
        select(Commande)
        .options(selectinload(Commande.lignes))
        .where(Commande.sumup_checkout_id == checkout_id)
    )
    commande = result.scalar_one_or_none()
    if not commande:
        return
    commande.statut = StatutCommande.annulee
    for ligne in commande.lignes:
        await decrementer_stock(db, ligne.lot_id, -(ligne.poids_g / 1000))
    await db.commit()
    logger.info(f"Commande {commande.numero} remboursée")


async def handle_vente_terminal(transaction: dict, db: AsyncSession):
    """Vente directe terminal SumUp sur le stand."""
    montant = transaction.get("amount", 0)
    code = transaction.get("transaction_code", "")
    logger.info(f"Vente terminal SumUp: {montant}€ [{code}]")
