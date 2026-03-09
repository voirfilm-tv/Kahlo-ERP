"""
KAHLO CAFÉ — Service SumUp
API REST SumUp pour créer des checkouts (liens de paiement)
Doc : https://developer.sumup.com/api
"""

import httpx
import os
import logging

logger = logging.getLogger(__name__)

SUMUP_API_KEY = os.getenv("SUMUP_API_KEY", "")
SUMUP_BASE = "https://api.sumup.com/v0.1"

def _headers():
    return {
        "Authorization": f"Bearer {SUMUP_API_KEY}",
        "Content-Type": "application/json",
    }


async def creer_checkout(commande_id: int, montant: float, description: str, email_client: str = None) -> dict:
    """
    Crée un SumUp Checkout (lien de paiement en ligne).
    Retourne checkout_id et pay_to_email (URL de paiement).
    """
    payload = {
        "checkout_reference": f"KAHLO-{commande_id}",
        "amount": montant,
        "currency": "EUR",
        "pay_to_email": os.getenv("SUMUP_MERCHANT_EMAIL", "bonjour@kahlocafe.fr"),
        "description": description,
    }
    if email_client:
        payload["customer_email"] = email_client

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUMUP_BASE}/checkouts",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"SumUp Checkout créé: {data.get('id')}")
        return {
            "checkout_id": data.get("id"),
            "checkout_url": f"https://pay.sumup.com/b2c/KAHLO{commande_id}",
            "status": data.get("status"),
        }


async def get_checkout(checkout_id: str) -> dict:
    """Récupère le statut d'un checkout SumUp"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUMUP_BASE}/checkouts/{checkout_id}",
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


async def rembourser_transaction(transaction_code: str) -> bool:
    """Lance un remboursement complet"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUMUP_BASE}/me/refund/{transaction_code}",
            headers=_headers(),
            timeout=10,
        )
        return resp.status_code == 204


async def get_transactions_recentes(limit: int = 20) -> list:
    """Récupère les dernières transactions pour le dashboard"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUMUP_BASE}/me/transactions/history",
            params={"limit": limit, "order": "descending"},
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])


async def verifier_connexion() -> bool:
    """Vérifie que la clé API SumUp est valide"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUMUP_BASE}/me",
                headers=_headers(),
                timeout=5,
            )
            return resp.status_code == 200
    except Exception:
        return False
