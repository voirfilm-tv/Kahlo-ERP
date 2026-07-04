"""
KAHLO CAFÉ — Callbacks SumUp
SumUp notifie les changements de statut d'un checkout via le return_url
transmis à la création du checkout (pas de webhook global côté dashboard).

Sécurité : le corps du POST n'est JAMAIS considéré comme fiable — on ne
lit que l'identifiant du checkout, puis on re-vérifie son statut réel
auprès de l'API SumUp avant de marquer la commande payée. Un attaquant
qui poste un faux événement ne peut donc rien déclencher.
Compat : si SUMUP_WEBHOOK_SECRET est configuré, la signature HMAC
x-sumup-signature est en plus exigée.
"""

from fastapi import APIRouter, Request, HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import hmac
import hashlib
import json
import os
import logging

from database import get_db
from models import Commande
from services.stock import decrementer_stock
from services.brevo import notifier_client_paiement_recu
from services.calendrier import creer_evenement_remise
from services.sumup import get_checkout

router = APIRouter()
logger = logging.getLogger(__name__)


def _webhook_secret() -> str:
    # Lu à chaque appel : configurable à chaud via la page Paramètres
    return os.getenv("SUMUP_WEBHOOK_SECRET", "")


def _verifier_signature(payload: bytes, signature: str) -> bool:
    """Signature HMAC-SHA256 optionnelle (défense en profondeur)."""
    secret = _webhook_secret()
    if not secret or not signature:
        return False
    sig = signature.replace("sha256=", "")
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


@router.post("/sumup")
async def sumup_webhook(
    request: Request,
    x_sumup_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    payload = await request.body()

    # Signature exigée seulement si un secret est configuré (optionnel :
    # la sécurité réelle vient de la re-vérification API ci-dessous)
    if _webhook_secret() and not _verifier_signature(payload, x_sumup_signature or ""):
        raise HTTPException(status_code=400, detail="Signature invalide")

    try:
        event = json.loads(payload)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Corps JSON invalide")

    # Formats possibles : {id, status...} ou {event_type, payload: {...}}
    body = event.get("payload") if isinstance(event.get("payload"), dict) else event
    checkout_id = body.get("checkout_id") or body.get("id")
    logger.info("Callback SumUp reçu pour checkout %s", checkout_id)

    if not checkout_id:
        return {"received": True}

    # La commande doit exister chez nous — sinon rien à faire
    result = await db.execute(
        select(Commande)
        .options(selectinload(Commande.lignes), selectinload(Commande.client), selectinload(Commande.marche))
        .where(Commande.sumup_checkout_id == str(checkout_id))
    )
    commande = result.scalar_one_or_none()
    if not commande:
        logger.warning("Commande introuvable pour SumUp checkout: %s", checkout_id)
        return {"received": True}

    # ⚠ Ne jamais faire confiance au statut du POST : re-vérifier via l'API
    try:
        checkout = await get_checkout(str(checkout_id))
    except Exception:
        logger.exception("Impossible de vérifier le checkout %s auprès de SumUp", checkout_id)
        return {"received": True, "verified": False}

    statut = (checkout.get("status") or "").upper()

    if statut == "PAID":
        await _traiter_paiement_confirme(commande, checkout, db)
    else:
        logger.info("Checkout %s en statut %s — aucune action", checkout_id, statut)

    return {"received": True}


async def _traiter_paiement_confirme(commande: Commande, checkout: dict, db: AsyncSession):
    """Marque la commande payée, décrémente le stock, notifie le client."""
    # Idempotence : si déjà traité, ignorer
    if commande.sumup_paid:
        logger.info("Paiement déjà traité pour la commande %s, ignoré", commande.numero)
        return

    commande.sumup_paid = True
    transactions = checkout.get("transactions") or []
    commande.sumup_transaction_code = (
        checkout.get("transaction_code")
        or (transactions[0].get("transaction_code") if transactions else "")
        or ""
    )

    for ligne in commande.lignes:
        await decrementer_stock(db, ligne.lot_id, ligne.poids_g / 1000)

    if commande.marche_id:
        await creer_evenement_remise(db, commande)

    await db.commit()

    # Notification après commit pour ne pas risquer de perdre le paiement
    try:
        await notifier_client_paiement_recu(commande)
    except Exception:
        logger.exception("Erreur notification après paiement commande %s", commande.numero)
    logger.info("Commande %s payée via SumUp (vérifié API)", commande.numero)
