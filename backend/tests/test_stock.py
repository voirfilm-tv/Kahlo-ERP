"""Tests — Stock & Fournisseurs"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestLots:
    async def test_get_lots_empty(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/stock/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_lots_with_data(self, client: AsyncClient, auth_headers, sample_lot):
        resp = await client.get("/api/stock/", headers=auth_headers)
        assert resp.status_code == 200
        lots = resp.json()
        assert len(lots) >= 1
        assert lots[0]["origine"] == "Éthiopie Yirgacheffe"
        assert lots[0]["stock_kg"] == 10.0

    async def test_create_lot(self, client: AsyncClient, auth_headers, sample_fournisseur):
        resp = await client.post("/api/stock/", headers=auth_headers, json={
            "fournisseur_id": sample_fournisseur.id,
            "origine": "Kenya AA",
            "numero_lot": "LOT-TEST-002",
            "stock_kg": 5.0,
            "prix_achat_kg": 20.0,
            "prix_vente_kg": 40.0,
        })
        assert resp.status_code == 200
        assert resp.json()["numero_lot"] == "LOT-TEST-002"

    async def test_get_lot_by_id(self, client: AsyncClient, auth_headers, sample_lot):
        resp = await client.get(f"/api/stock/{sample_lot.id}", headers=auth_headers)
        assert resp.status_code == 200

    async def test_update_lot(self, client: AsyncClient, auth_headers, sample_lot):
        resp = await client.patch(f"/api/stock/{sample_lot.id}", headers=auth_headers, json={
            "prix_vente_kg": 35.0,
        })
        assert resp.status_code == 200

    async def test_archive_lot(self, client: AsyncClient, auth_headers, sample_lot):
        resp = await client.delete(f"/api/stock/{sample_lot.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert "archivé" in resp.json()["message"].lower()

    async def test_stock_stats(self, client: AsyncClient, auth_headers, sample_lot):
        resp = await client.get("/api/stock/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_kg"] == 10.0
        assert data["nb_origines"] == 1

    async def test_critique_filter(self, client: AsyncClient, auth_headers, db, sample_fournisseur):
        from models import Lot
        lot = Lot(
            fournisseur_id=sample_fournisseur.id,
            origine="Critique Test",
            numero_lot="LOT-CRIT-001",
            stock_kg=1.0,  # < seuil de 3
            seuil_alerte_kg=3.0,
            prix_achat_kg=10.0,
            prix_vente_kg=20.0,
            actif=True,
        )
        db.add(lot)
        await db.commit()

        resp = await client.get("/api/stock/?critique_only=true", headers=auth_headers)
        assert resp.status_code == 200
        assert any(l["origine"] == "Critique Test" for l in resp.json())


class TestAjustementStock:
    async def test_ajustement_positif(self, client: AsyncClient, auth_headers, sample_lot):
        resp = await client.post("/api/stock/ajustement", headers=auth_headers, json={
            "lot_id": sample_lot.id,
            "delta_kg": 5.0,
            "motif": "commande_fournisseur",
        })
        assert resp.status_code == 200
        assert resp.json()["nouveau_stock"] == 15.0

    async def test_ajustement_negatif(self, client: AsyncClient, auth_headers, sample_lot):
        resp = await client.post("/api/stock/ajustement", headers=auth_headers, json={
            "lot_id": sample_lot.id,
            "delta_kg": -2.0,
            "motif": "correction",
        })
        assert resp.status_code == 200
        assert resp.json()["nouveau_stock"] == 8.0

    async def test_ajustement_ne_descend_pas_sous_zero(self, client: AsyncClient, auth_headers, sample_lot):
        resp = await client.post("/api/stock/ajustement", headers=auth_headers, json={
            "lot_id": sample_lot.id,
            "delta_kg": -999.0,
            "motif": "correction",
        })
        assert resp.status_code == 200
        assert resp.json()["nouveau_stock"] == 0.0

    async def test_ajustement_lot_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/stock/ajustement", headers=auth_headers, json={
            "lot_id": 99999,
            "delta_kg": 1.0,
            "motif": "test",
        })
        assert resp.status_code == 404


class TestFournisseurs:
    async def test_get_fournisseurs(self, client: AsyncClient, auth_headers, sample_fournisseur):
        resp = await client.get("/api/fournisseurs/", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_create_fournisseur(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/fournisseurs/", headers=auth_headers, json={
            "nom": "Nouveau Fournisseur",
            "email": "nouveau@fournisseur.fr",
            "pays": "Belgique",
        })
        assert resp.status_code == 201

    async def test_noter_fournisseur(self, client: AsyncClient, auth_headers, sample_fournisseur):
        resp = await client.patch(
            f"/api/fournisseurs/{sample_fournisseur.id}/score?score=3.5",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["score"] == 3.5

    async def test_noter_fournisseur_clamp(self, client: AsyncClient, auth_headers, sample_fournisseur):
        resp = await client.patch(
            f"/api/fournisseurs/{sample_fournisseur.id}/score?score=10",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["score"] == 5.0  # clamped to max
