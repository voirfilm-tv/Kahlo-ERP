"""
KAHLO CAFÉ — Offline Sync
Mode terrain : ventes enregistrées sans internet → sync au retour
Utilise Redis (asyncio) comme queue locale
"""

import json
import redis.asyncio as aioredis
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
QUEUE_KEY = "kahlo:offline:queue"
SYNC_STATUS_KEY = "kahlo:sync:status"


def _get_redis() -> aioredis.Redis:
    """Crée un client Redis async (lazy, une connexion par appel)."""
    return aioredis.from_url(REDIS_URL, decode_responses=True)


# ============================================================
#  ENQUEUE — Côté frontend (en offline)
# ============================================================

async def enqueue_vente(vente: dict) -> str:
    """
    Met une vente en file d'attente pour sync ultérieure
    Appelé quand le frontend détecte qu'il est offline
    """
    vente["_queued_at"] = datetime.now().isoformat()
    vente["_id"] = f"offline_{datetime.now().timestamp()}"

    r = _get_redis()
    try:
        await r.rpush(QUEUE_KEY, json.dumps(vente))
    finally:
        await r.aclose()

    logger.info(f"Vente mise en queue offline: {vente['_id']}")
    return vente["_id"]


async def get_queue_size() -> int:
    """Retourne le nombre d'opérations en attente de sync"""
    r = _get_redis()
    try:
        return await r.llen(QUEUE_KEY)
    finally:
        await r.aclose()


# ============================================================
#  SYNC — Au retour de connexion
# ============================================================

async def sync_queue(db) -> dict:
    """
    Traite toutes les ventes en attente dans la bonne ordre :
    1. Stock
    2. Commandes
    3. SumUp (si paiement CB)
    4. CRM
    5. Calendrier
    """
    r = _get_redis()
    try:
        total = await r.llen(QUEUE_KEY)
        if total == 0:
            return {"synced": 0, "errors": 0}

        synced = 0
        errors = 0
        erreur_details = []

        await r.set(SYNC_STATUS_KEY, json.dumps({"status": "syncing", "total": total, "done": 0}))

        while await r.llen(QUEUE_KEY) > 0:
            raw = await r.lindex(QUEUE_KEY, 0)  # Peek sans supprimer
            try:
                op = json.loads(raw)
                await _process_operation(op, db)
                await r.lpop(QUEUE_KEY)  # Supprimer seulement si succès
                synced += 1

                # Mettre à jour le statut de sync
                await r.set(SYNC_STATUS_KEY, json.dumps({
                    "status": "syncing",
                    "total": total,
                    "done": synced
                }))

            except Exception as e:
                logger.error(f"Erreur sync opération: {e}")
                errors += 1
                erreur_details.append({"op": str(op.get("type")), "error": str(e)})

                # En cas d'erreur : déplacer en dead-letter queue
                await r.lpop(QUEUE_KEY)
                await r.rpush("kahlo:offline:failed", raw)

        await r.set(SYNC_STATUS_KEY, json.dumps({"status": "done", "synced": synced, "errors": errors}))

        logger.info(f"Sync terminée: {synced} OK, {errors} erreurs")
        return {"synced": synced, "errors": errors, "details": erreur_details}
    finally:
        await r.aclose()


async def _process_operation(op: dict, db):
    """Traite une opération offline selon son type"""
    op_type = op.get("type")

    if op_type == "vente":
        await _sync_vente(op, db)
    elif op_type == "commande_remise":
        await _sync_remise(op, db)
    elif op_type == "nouveau_client":
        await _sync_client(op, db)
    else:
        logger.warning(f"Type d'opération inconnu: {op_type}")


async def _sync_vente(op: dict, db):
    """Sync une vente terrain : décrémente stock + crée commande"""
    from services.stock import decrementer_stock
    from models import Commande, LigneCommande, StatutCommande

    commande = Commande(
        numero=f"CMD-OFFLINE-{op['_id'][-6:]}",
        client_id=op.get("client_id"),
        statut=StatutCommande.remise,
        montant_total=op["montant"],
        paiement_mode=op.get("paiement", "especes"),
        date_commande=datetime.fromisoformat(op["_queued_at"]),
        date_remise_reelle=datetime.fromisoformat(op["_queued_at"]),
        marche_id=op.get("marche_id"),
    )
    db.add(commande)
    await db.flush()

    for ligne in op.get("lignes", []):
        db.add(LigneCommande(
            commande_id=commande.id,
            lot_id=ligne["lot_id"],
            poids_g=ligne["poids_g"],
            prix_unitaire=ligne["prix"],
        ))
        await decrementer_stock(db, ligne["lot_id"], ligne["poids_g"] / 1000)


async def _sync_remise(op: dict, db):
    """Marque une commande existante comme remise"""
    from models import Commande, StatutCommande
    from sqlalchemy import select

    result = await db.execute(
        select(Commande).where(Commande.id == op["commande_id"])
    )
    commande = result.scalar_one_or_none()
    if commande:
        commande.statut = StatutCommande.remise
        commande.date_remise_reelle = datetime.fromisoformat(op["_queued_at"])


async def _sync_client(op: dict, db):
    """Crée un nouveau client depuis une saisie offline"""
    from models import Client
    client = Client(**op["data"])
    db.add(client)


# ============================================================
#  STATUT SYNC (pour l'UI)
# ============================================================

async def get_sync_status() -> dict:
    r = _get_redis()
    try:
        raw = await r.get(SYNC_STATUS_KEY)
        if not raw:
            queue_size = await r.llen(QUEUE_KEY)
            return {"status": "idle", "queue_size": queue_size}
        status = json.loads(raw)
        status["queue_size"] = await r.llen(QUEUE_KEY)
        return status
    finally:
        await r.aclose()
