"""
KAHLO CAFÉ — Synchronisation des ventes SumUp
Importe l'historique des transactions (terminal + checkouts en ligne)
dans la table transactions_sumup, et décrémente automatiquement le stock
des lots quand un produit vendu correspond à une origine de l'ERP.

Convention de nommage côté SumUp : inclure le poids dans le nom de
l'article du catalogue (ex: « Mélange Expresso 250g », « Moka Bio 1kg »)
et reprendre le nom de l'origine ERP. Sans poids détectable, la vente est
importée pour les stats mais le stock n'est pas modifié.
"""

import re
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import TransactionSumUp, Lot
from services import sumup as sumup_api
from services.stock import decrementer_stock

logger = logging.getLogger(__name__)

_POIDS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kg|g)\b", re.IGNORECASE)

# Statuts qui comptent comme une vente encaissée
_STATUTS_VENTE = {"SUCCESSFUL", "PAID_OUT", "REFUND_PENDING"}
_STATUTS_ANNULATION = {"REFUNDED", "CHARGEBACK", "CANCELLED", "FAILED"}


def extraire_poids_kg(nom_produit: str) -> float | None:
    """Extrait le poids d'un nom d'article (« Moka 250g » → 0.25)."""
    m = _POIDS_RE.search(nom_produit or "")
    if not m:
        return None
    valeur = float(m.group(1).replace(",", "."))
    return valeur if m.group(2).lower() == "kg" else valeur / 1000


async def _associer_stock(db: AsyncSession, produits: list) -> tuple[bool, list]:
    """Fait correspondre chaque produit vendu à un lot ERP et décrémente le stock.

    Correspondance : l'origine du lot (insensible à la casse) doit apparaître
    dans le nom de l'article SumUp, et un poids doit être détectable dans le nom.
    """
    result = await db.execute(select(Lot).where(Lot.actif == True))
    lots = result.scalars().all()
    # Origines les plus longues d'abord (évite qu'un nom court capture tout)
    lots_tries = sorted(lots, key=lambda l: len(l.origine or ""), reverse=True)

    details = []
    au_moins_un = False
    for produit in produits or []:
        nom = (produit.get("name") or "").strip()
        quantite = float(produit.get("quantity") or 1)
        if not nom:
            continue

        lot = next((l for l in lots_tries if l.origine and l.origine.lower() in nom.lower()), None)
        poids_kg = extraire_poids_kg(nom)

        if lot and poids_kg:
            kg = round(poids_kg * quantite, 3)
            await decrementer_stock(db, lot.id, kg)
            details.append({"produit": nom, "lot_id": lot.id, "origine": lot.origine, "kg": kg})
            au_moins_un = True
        else:
            raison = "poids introuvable dans le nom" if lot else "aucun lot correspondant"
            details.append({"produit": nom, "non_associe": raison})

    return au_moins_un, details


async def _recrediter_stock(db: AsyncSession, stock_details: list):
    """Recrédite le stock d'une vente remboursée/annulée déjà traitée."""
    for d in stock_details or []:
        lot_id, kg = d.get("lot_id"), d.get("kg")
        if not lot_id or not kg:
            continue
        result = await db.execute(select(Lot).where(Lot.id == lot_id))
        lot = result.scalar_one_or_none()
        if lot:
            lot.stock_kg = (lot.stock_kg or 0) + kg
            logger.info("Stock recrédité (%s) : +%.3f kg sur %s", "remboursement SumUp", kg, lot.origine)


def _parse_timestamp(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return None


async def synchroniser(db: AsyncSession, jours_historique: int = 90) -> dict:
    """Importe les transactions SumUp depuis la dernière sync (idempotent).

    - Nouvelle vente encaissée → enregistrée + décrément de stock si les
      produits correspondent à des lots.
    - Vente déjà connue passée en remboursée → stock recrédité.
    """
    # Reprendre 24h avant la dernière transaction connue (chevauchement de sécurité)
    result = await db.execute(select(func.max(TransactionSumUp.date_transaction)))
    derniere = result.scalar()
    if derniere:
        oldest = (derniere - timedelta(days=1))
    else:
        oldest = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=jours_historique)
    oldest_iso = oldest.strftime("%Y-%m-%dT%H:%M:%SZ")

    items = await sumup_api.lister_transactions(oldest_time=oldest_iso)

    importees = 0
    stock_maj = 0
    rembourses = 0

    for item in items:
        code = item.get("transaction_code") or item.get("id")
        if not code:
            continue
        statut = (item.get("status") or "").upper()

        result = await db.execute(
            select(TransactionSumUp).where(TransactionSumUp.transaction_code == code)
        )
        existante = result.scalar_one_or_none()

        if existante:
            # Passage vente → remboursée : recréditer le stock une seule fois
            if statut in _STATUTS_ANNULATION and existante.statut not in _STATUTS_ANNULATION:
                if existante.stock_traite:
                    await _recrediter_stock(db, existante.stock_details)
                    existante.stock_traite = False
                existante.statut = statut
                rembourses += 1
            continue

        produits = item.get("products") or []
        tx = TransactionSumUp(
            transaction_code=code,
            montant=float(item.get("amount") or 0),
            devise=item.get("currency") or "EUR",
            frais=float(item.get("fee_amount") or 0),
            statut=statut,
            payment_type=item.get("payment_type"),
            entry_mode=item.get("entry_mode"),
            produits=[
                {"name": p.get("name"), "quantity": p.get("quantity"), "price": p.get("price")}
                for p in produits
            ],
            date_transaction=_parse_timestamp(item.get("timestamp")),
        )

        if statut in _STATUTS_VENTE and produits:
            traite, details = await _associer_stock(db, produits)
            tx.stock_traite = traite
            tx.stock_details = details
            if traite:
                stock_maj += 1

        db.add(tx)
        importees += 1

    await db.commit()
    logger.info("Sync SumUp : %d importées, %d stocks mis à jour, %d remboursements", importees, stock_maj, rembourses)
    return {
        "importees": importees,
        "stock_maj": stock_maj,
        "remboursements": rembourses,
        "depuis": oldest_iso,
    }
