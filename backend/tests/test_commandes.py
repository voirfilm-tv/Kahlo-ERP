"""Tests — Commandes (création, statut, annulation, stock)"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestCommandeCreation:
    async def test_create_commande_especes(
        self, client: AsyncClient, auth_headers, sample_client, sample_lot
    ):
        resp = await client.post("/api/commandes/", headers=auth_headers, json={
            "client_id": sample_client.id,
            "lignes": [{
                "lot_id": sample_lot.id,
                "poids_g": 250,
                "mouture": "Filtre",
                "prix_unitaire": 8.5,
            }],
            "paiement_mode": "especes",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["montant_total"] == 8.5
        assert data["numero"].startswith("CMD-")

    async def test_create_commande_sumup(
        self, client: AsyncClient, auth_headers, sample_client, sample_lot
    ):
        resp = await client.post("/api/commandes/", headers=auth_headers, json={
            "client_id": sample_client.id,
            "lignes": [{
                "lot_id": sample_lot.id,
                "poids_g": 500,
                "mouture": "Expresso",
                "prix_unitaire": 16.0,
            }],
            "paiement_mode": "sumup",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["sumup_checkout_id"] == "mock-checkout-id"

    async def test_create_commande_client_not_found(
        self, client: AsyncClient, auth_headers, sample_lot
    ):
        resp = await client.post("/api/commandes/", headers=auth_headers, json={
            "client_id": 99999,
            "lignes": [{
                "lot_id": sample_lot.id,
                "poids_g": 250,
                "mouture": "Filtre",
                "prix_unitaire": 8.0,
            }],
        })
        assert resp.status_code == 404

    async def test_create_commande_lot_not_found(
        self, client: AsyncClient, auth_headers, sample_client
    ):
        resp = await client.post("/api/commandes/", headers=auth_headers, json={
            "client_id": sample_client.id,
            "lignes": [{
                "lot_id": 99999,
                "poids_g": 250,
                "mouture": "Filtre",
                "prix_unitaire": 8.0,
            }],
        })
        assert resp.status_code == 404

    async def test_create_commande_stock_insufficient(
        self, client: AsyncClient, auth_headers, sample_client, sample_lot
    ):
        resp = await client.post("/api/commandes/", headers=auth_headers, json={
            "client_id": sample_client.id,
            "lignes": [{
                "lot_id": sample_lot.id,
                "poids_g": 50000,  # 50 kg > 10 kg stock
                "mouture": "Filtre",
                "prix_unitaire": 100.0,
            }],
        })
        assert resp.status_code == 400
        assert "Stock insuffisant" in resp.json()["detail"]


class TestCommandeList:
    async def test_get_commandes_empty(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/commandes/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_commandes_with_data(
        self, client: AsyncClient, auth_headers, sample_client, sample_lot
    ):
        await client.post("/api/commandes/", headers=auth_headers, json={
            "client_id": sample_client.id,
            "lignes": [{"lot_id": sample_lot.id, "poids_g": 250, "mouture": "Filtre", "prix_unitaire": 8.0}],
            "paiement_mode": "especes",
        })
        resp = await client.get("/api/commandes/", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_filter_by_statut(
        self, client: AsyncClient, auth_headers, sample_client, sample_lot
    ):
        await client.post("/api/commandes/", headers=auth_headers, json={
            "client_id": sample_client.id,
            "lignes": [{"lot_id": sample_lot.id, "poids_g": 250, "mouture": "Filtre", "prix_unitaire": 8.0}],
            "paiement_mode": "especes",
        })
        resp = await client.get("/api/commandes/?statut=en_attente", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_commande_stats(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/commandes/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "en_attente" in data


class TestCommandeStatut:
    async def _create_cmd(self, client, auth_headers, sample_client, sample_lot):
        resp = await client.post("/api/commandes/", headers=auth_headers, json={
            "client_id": sample_client.id,
            "lignes": [{"lot_id": sample_lot.id, "poids_g": 250, "mouture": "Filtre", "prix_unitaire": 8.0}],
            "paiement_mode": "especes",
        })
        return resp.json()["id"]

    async def test_change_to_prete(
        self, client: AsyncClient, auth_headers, sample_client, sample_lot
    ):
        cmd_id = await self._create_cmd(client, auth_headers, sample_client, sample_lot)
        resp = await client.patch(f"/api/commandes/{cmd_id}/statut", headers=auth_headers, json={
            "statut": "prete",
        })
        assert resp.status_code == 200
        assert resp.json()["statut"] == "prete"

    async def test_change_to_remise(
        self, client: AsyncClient, auth_headers, sample_client, sample_lot
    ):
        cmd_id = await self._create_cmd(client, auth_headers, sample_client, sample_lot)
        # en_attente → prête → remise
        await client.patch(f"/api/commandes/{cmd_id}/statut", headers=auth_headers, json={"statut": "prete"})
        resp = await client.patch(f"/api/commandes/{cmd_id}/statut", headers=auth_headers, json={"statut": "remise"})
        assert resp.status_code == 200
        assert resp.json()["statut"] == "remise"

    async def test_cancel_commande_recredits_stock(
        self, client: AsyncClient, auth_headers, sample_client, sample_lot
    ):
        """Annuler une commande espèces doit re-créditer le stock."""
        cmd_id = await self._create_cmd(client, auth_headers, sample_client, sample_lot)

        resp = await client.patch(f"/api/commandes/{cmd_id}/statut", headers=auth_headers, json={
            "statut": "annulee",
        })
        assert resp.status_code == 200
        assert resp.json()["statut"] == "annulee"

    async def test_change_statut_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.patch("/api/commandes/99999/statut", headers=auth_headers, json={
            "statut": "prete",
        })
        assert resp.status_code == 404
