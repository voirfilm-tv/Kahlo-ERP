"""Tests — Callbacks SumUp (return_url) : re-vérification API, anti-spoofing"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


async def _commande_avec_checkout(client: AsyncClient, auth_headers, sample_client, sample_lot):
    """Crée une commande SumUp (checkout mocké par conftest → mock-checkout-id)."""
    resp = await client.post("/api/commandes/", headers=auth_headers, json={
        "client_id": sample_client.id,
        "lignes": [{"lot_id": sample_lot.id, "poids_g": 250, "mouture": "Grains entiers", "prix_unitaire": 7.5}],
        "paiement_mode": "sumup",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCallbackSumUp:
    async def test_paiement_confirme_apres_verification_api(
        self, client: AsyncClient, auth_headers, sample_client, sample_lot
    ):
        """Un callback dont le checkout est réellement PAID (vérifié via l'API)
        marque la commande payée et décrémente le stock."""
        commande = await _commande_avec_checkout(client, auth_headers, sample_client, sample_lot)

        with (
            patch("routers.webhooks.get_checkout", new_callable=AsyncMock,
                  return_value={"status": "PAID", "transaction_code": "TXABC"}),
            patch("routers.webhooks.notifier_client_paiement_recu", new_callable=AsyncMock),
            patch("routers.webhooks.creer_evenement_remise", new_callable=AsyncMock),
        ):
            resp = await client.post("/api/webhooks/sumup", json={
                "id": "mock-checkout-id", "status": "PAID",
            })
        assert resp.status_code == 200

        detail = await client.get(f"/api/commandes/{commande['id']}", headers=auth_headers)
        assert detail.json()["sumup_paid"] is True
        assert detail.json()["sumup_transaction_code"] == "TXABC"

        # Stock décrémenté de 0.25 kg
        lot = await client.get(f"/api/stock/{sample_lot.id}", headers=auth_headers)
        assert lot.json()["stock_kg"] == pytest.approx(9.75)

    async def test_spoofing_rejete(self, client: AsyncClient, auth_headers, sample_client, sample_lot):
        """Un POST qui PRÉTEND que le paiement est fait, alors que l'API SumUp
        dit PENDING, ne doit rien déclencher (le corps n'est jamais cru)."""
        commande = await _commande_avec_checkout(client, auth_headers, sample_client, sample_lot)

        with patch("routers.webhooks.get_checkout", new_callable=AsyncMock,
                   return_value={"status": "PENDING"}):
            resp = await client.post("/api/webhooks/sumup", json={
                "id": "mock-checkout-id", "status": "PAID",  # ← mensonge de l'attaquant
            })
        assert resp.status_code == 200  # accusé de réception, mais...

        detail = await client.get(f"/api/commandes/{commande['id']}", headers=auth_headers)
        assert detail.json()["sumup_paid"] is False  # ...rien n'a été validé

        lot = await client.get(f"/api/stock/{sample_lot.id}", headers=auth_headers)
        assert lot.json()["stock_kg"] == pytest.approx(10.0)  # stock intact

    async def test_idempotence(self, client: AsyncClient, auth_headers, sample_client, sample_lot):
        """Deux callbacks pour le même paiement ne décrémentent le stock qu'une fois."""
        await _commande_avec_checkout(client, auth_headers, sample_client, sample_lot)

        with (
            patch("routers.webhooks.get_checkout", new_callable=AsyncMock,
                  return_value={"status": "PAID", "transaction_code": "TX1"}),
            patch("routers.webhooks.notifier_client_paiement_recu", new_callable=AsyncMock),
            patch("routers.webhooks.creer_evenement_remise", new_callable=AsyncMock),
        ):
            await client.post("/api/webhooks/sumup", json={"id": "mock-checkout-id"})
            await client.post("/api/webhooks/sumup", json={"id": "mock-checkout-id"})

        lot = await client.get(f"/api/stock/{sample_lot.id}", headers=auth_headers)
        assert lot.json()["stock_kg"] == pytest.approx(9.75)

    async def test_checkout_inconnu_ignore(self, client: AsyncClient):
        resp = await client.post("/api/webhooks/sumup", json={"id": "inexistant-999"})
        assert resp.status_code == 200
        assert resp.json()["received"] is True

    async def test_json_invalide(self, client: AsyncClient):
        resp = await client.post(
            "/api/webhooks/sumup",
            content=b"pas du json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 400


class TestTesteurCle:
    async def test_teste_la_cle_saisie(self, client: AsyncClient, auth_headers):
        """Le testeur doit tester la clé envoyée dans le corps, sans exiger
        qu'elle soit enregistrée au préalable."""
        with patch("services.sumup.verifier_connexion", new_callable=AsyncMock, return_value=True) as mock_v:
            resp = await client.post("/api/parametres/tester-sumup", headers=auth_headers,
                                     json={"api_key": "sup_sk_nouvelle_cle"})
        assert resp.status_code == 200
        mock_v.assert_awaited_once_with("sup_sk_nouvelle_cle")

    async def test_sans_cle_ni_config(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/parametres/tester-sumup", headers=auth_headers, json={})
        assert resp.status_code == 400
        assert "saisissez" in resp.json()["detail"].lower()

    async def test_cle_masquee_ignoree(self, client: AsyncClient, auth_headers):
        """Une valeur masquée (••••••••) ne doit pas être testée comme une clé."""
        resp = await client.post("/api/parametres/tester-sumup", headers=auth_headers,
                                 json={"api_key": "••••••••"})
        assert resp.status_code == 400  # pas de clé configurée en test
