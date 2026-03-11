"""Tests — Clients CRM (CRUD, tampons, VIP, recherche)"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestClientCRUD:
    async def test_create_client(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/clients/", headers=auth_headers, json={
            "prenom": "Jean",
            "nom": "Martin",
            "email": "jean@test.fr",
            "ville": "Lyon",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["prenom"] == "Jean"
        assert data["nom"] == "Martin"
        assert data["email"] == "jean@test.fr"
        assert data["tampons"] == 0
        assert data["vip"] is False

    async def test_create_client_duplicate_email(self, client: AsyncClient, auth_headers, sample_client):
        resp = await client.post("/api/clients/", headers=auth_headers, json={
            "prenom": "Autre",
            "nom": "Personne",
            "email": "marie@test.fr",  # same as sample_client
        })
        assert resp.status_code == 409

    async def test_create_client_without_email(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/clients/", headers=auth_headers, json={
            "prenom": "Sans",
            "nom": "Email",
        })
        assert resp.status_code == 201

    async def test_get_clients(self, client: AsyncClient, auth_headers, sample_client):
        resp = await client.get("/api/clients/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(c["prenom"] == "Marie" for c in data)

    async def test_get_client_by_id(self, client: AsyncClient, auth_headers, sample_client):
        resp = await client.get(f"/api/clients/{sample_client.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["prenom"] == "Marie"

    async def test_get_client_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/clients/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_update_client(self, client: AsyncClient, auth_headers, sample_client):
        resp = await client.patch(f"/api/clients/{sample_client.id}", headers=auth_headers, json={
            "ville": "Paris",
            "telephone": "0611111111",
        })
        assert resp.status_code == 200
        assert resp.json()["ville"] == "Paris"
        assert resp.json()["telephone"] == "0611111111"
        # Unchanged fields preserved
        assert resp.json()["prenom"] == "Marie"

    async def test_delete_client(self, client: AsyncClient, auth_headers, sample_client):
        resp = await client.delete(f"/api/clients/{sample_client.id}", headers=auth_headers)
        assert resp.status_code == 204

        # Verify deleted
        resp = await client.get(f"/api/clients/{sample_client.id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_search_clients(self, client: AsyncClient, auth_headers, sample_client):
        resp = await client.get("/api/clients/?search=Marie", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_search_no_results(self, client: AsyncClient, auth_headers, sample_client):
        resp = await client.get("/api/clients/?search=Zzzzzzz", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 0


class TestTamponsVIP:
    async def test_add_tampon(self, client: AsyncClient, auth_headers, sample_client):
        resp = await client.post(f"/api/clients/{sample_client.id}/tampon", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["tampons"] == 1

    async def test_add_multiple_tampons(self, client: AsyncClient, auth_headers, sample_client):
        for _ in range(3):
            resp = await client.post(f"/api/clients/{sample_client.id}/tampon", headers=auth_headers)
        assert resp.json()["tampons"] == 3

    async def test_reset_tampons(self, client: AsyncClient, auth_headers, sample_client):
        # Add some tampons first
        await client.post(f"/api/clients/{sample_client.id}/tampon", headers=auth_headers)
        await client.post(f"/api/clients/{sample_client.id}/tampon", headers=auth_headers)

        resp = await client.post(f"/api/clients/{sample_client.id}/tampon/reset", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["tampons"] == 0

    async def test_vip_upgrade(self, client: AsyncClient, auth_headers, sample_client, db):
        """VIP auto-upgrade quand le client a >= 5 commandes remises."""
        from models import Commande, StatutCommande
        # Create 5 delivered orders
        for i in range(5):
            cmd = Commande(
                numero=f"CMD-VIP-{i:03d}",
                client_id=sample_client.id,
                statut=StatutCommande.remise,
                montant_total=10.0,
            )
            db.add(cmd)
        await db.commit()

        resp = await client.post(f"/api/clients/{sample_client.id}/tampon", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["vip"] is True


class TestAlertes:
    async def test_alertes_endpoint(self, client: AsyncClient, auth_headers, sample_client):
        resp = await client.get("/api/clients/alertes", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "anniversaires" in data
        assert "inactifs" in data
        assert "total_alertes" in data
