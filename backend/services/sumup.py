"""
KAHLO CAFÉ — Service SumUp
API REST SumUp pour créer des checkouts (liens de paiement)
Doc : https://developer.sumup.com/api
"""

import httpx
import os
import logging

logger = logging.getLogger(__name__)

SUMUP_BASE = "https://api.sumup.com/v0.1"

def _headers(api_key: str | None = None):
    # Clé lue à chaque appel : configurable à chaud via la page Paramètres.
    # api_key permet de tester une clé saisie avant enregistrement.
    return {
        "Authorization": f"Bearer {api_key or os.getenv('SUMUP_API_KEY', '')}",
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

    # SumUp notifie les changements de statut par checkout via return_url
    # (pas de webhook global côté dashboard). Nécessite une URL publique.
    base_publique = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if base_publique:
        payload["return_url"] = f"{base_publique}/api/webhooks/sumup"

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


async def get_merchant_code() -> str | None:
    """Récupère le merchant_code du compte (nécessaire pour l'API v2.1)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUMUP_BASE}/me", headers=_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return (data.get("merchant_profile") or {}).get("merchant_code")


async def lister_transactions(oldest_time: str | None = None, limit: int = 100, max_pages: int = 20) -> list:
    """Liste l'historique des transactions (API v2.1, paginée).

    Retourne les items bruts SumUp : transaction_code, amount, currency,
    status, payment_type, entry_mode, timestamp, products, fee_amount...
    """
    merchant_code = await get_merchant_code()
    if not merchant_code:
        return []

    base_url = f"https://api.sumup.com/v2.1/merchants/{merchant_code}/transactions/history"
    params = {"limit": limit, "order": "ascending"}
    if oldest_time:
        params["oldest_time"] = oldest_time

    items: list = []
    async with httpx.AsyncClient() as client:
        url, query = base_url, params
        for _ in range(max_pages):
            resp = await client.get(url, params=query, headers=_headers(), timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items.extend(data.get("items", []))

            # Pagination hypermedia : suivre le lien rel=next
            next_link = next((l for l in data.get("links", []) if l.get("rel") == "next"), None)
            if not next_link or not next_link.get("href"):
                break
            href = next_link["href"]
            url = href if href.startswith("http") else f"{base_url}?{href.split('?', 1)[-1]}"
            query = None
    return items


async def get_transaction_detail(transaction_code: str) -> dict:
    """Détail complet d'une transaction (produits, frais, événements)."""
    merchant_code = await get_merchant_code()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.sumup.com/v2.1/merchants/{merchant_code}/transactions",
            params={"transaction_code": transaction_code},
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


async def verifier_connexion(api_key: str | None = None) -> bool:
    """Vérifie qu'une clé API SumUp est valide (celle fournie, sinon la configurée)."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUMUP_BASE}/me",
                headers=_headers(api_key),
                timeout=8,
            )
            return resp.status_code == 200
    except Exception:
        return False
