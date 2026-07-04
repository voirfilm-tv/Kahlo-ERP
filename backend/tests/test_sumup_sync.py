"""Tests — Synchronisation des ventes SumUp (import, stock, remboursements)"""

import os
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from services.ventes_sumup import extraire_poids_kg


def _tx(code, statut="SUCCESSFUL", montant=9.0, produits=None, ts="2026-07-01T10:00:00Z", frais=0.16):
    return {
        "transaction_code": code,
        "status": statut,
        "amount": montant,
        "currency": "EUR",
        "fee_amount": frais,
        "payment_type": "POS",
        "entry_mode": "contactless",
        "timestamp": ts,
        "products": produits or [],
    }


class TestExtractionPoids:
    def test_grammes(self):
        assert extraire_poids_kg("Mélange Expresso 250g") == 0.25

    def test_kilogrammes(self):
        assert extraire_poids_kg("Moka Bio 1kg") == 1.0

    def test_decimal_virgule(self):
        assert extraire_poids_kg("Café 0,5kg") == 0.5

    def test_sans_poids(self):
        assert extraire_poids_kg("Dégustation expresso") is None


class TestSyncVentes:
    async def test_sync_sans_cle(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/sumup/sync", headers=auth_headers, json={})
        assert resp.status_code == 503

    async def test_import_et_decrement_stock(self, client: AsyncClient, auth_headers, sample_lot):
        """Une vente terminal « Éthiopie Yirgacheffe 250g » ×2 doit décrémenter 0.5 kg."""
        fausses = [_tx("TX001", produits=[
            {"name": "Éthiopie Yirgacheffe 250g", "quantity": 2, "price": 9.0},
        ])]
        with (
            patch.dict(os.environ, {"SUMUP_API_KEY": "sup_sk_test"}),
            patch("services.sumup.lister_transactions", new_callable=AsyncMock, return_value=fausses),
        ):
            resp = await client.post("/api/sumup/sync", headers=auth_headers, json={})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["importees"] == 1
        assert data["stock_maj"] == 1

        # Stock décrémenté : 10 kg − 0.5 kg
        resp = await client.get(f"/api/stock/{sample_lot.id}", headers=auth_headers)
        assert resp.json()["stock_kg"] == pytest.approx(9.5)

    async def test_sync_idempotente(self, client: AsyncClient, auth_headers, sample_lot):
        fausses = [_tx("TX002", produits=[{"name": "Éthiopie Yirgacheffe 250g", "quantity": 1}])]
        with (
            patch.dict(os.environ, {"SUMUP_API_KEY": "sup_sk_test"}),
            patch("services.sumup.lister_transactions", new_callable=AsyncMock, return_value=fausses),
        ):
            r1 = await client.post("/api/sumup/sync", headers=auth_headers, json={})
            r2 = await client.post("/api/sumup/sync", headers=auth_headers, json={})
        assert r1.json()["importees"] == 1
        assert r2.json()["importees"] == 0  # déjà connue → pas de double décrément

        resp = await client.get(f"/api/stock/{sample_lot.id}", headers=auth_headers)
        assert resp.json()["stock_kg"] == pytest.approx(9.75)

    async def test_remboursement_recredite_stock(self, client: AsyncClient, auth_headers, sample_lot):
        vente = [_tx("TX003", produits=[{"name": "Éthiopie Yirgacheffe 1kg", "quantity": 1}])]
        remboursee = [_tx("TX003", statut="REFUNDED", produits=[{"name": "Éthiopie Yirgacheffe 1kg", "quantity": 1}])]
        with patch.dict(os.environ, {"SUMUP_API_KEY": "sup_sk_test"}):
            with patch("services.sumup.lister_transactions", new_callable=AsyncMock, return_value=vente):
                await client.post("/api/sumup/sync", headers=auth_headers, json={})
            resp = await client.get(f"/api/stock/{sample_lot.id}", headers=auth_headers)
            assert resp.json()["stock_kg"] == pytest.approx(9.0)

            with patch("services.sumup.lister_transactions", new_callable=AsyncMock, return_value=remboursee):
                r = await client.post("/api/sumup/sync", headers=auth_headers, json={})
            assert r.json()["remboursements"] == 1
            resp = await client.get(f"/api/stock/{sample_lot.id}", headers=auth_headers)
            assert resp.json()["stock_kg"] == pytest.approx(10.0)

    async def test_produit_sans_poids_importe_sans_stock(self, client: AsyncClient, auth_headers, sample_lot):
        fausses = [_tx("TX004", produits=[{"name": "Dégustation expresso", "quantity": 1}])]
        with (
            patch.dict(os.environ, {"SUMUP_API_KEY": "sup_sk_test"}),
            patch("services.sumup.lister_transactions", new_callable=AsyncMock, return_value=fausses),
        ):
            resp = await client.post("/api/sumup/sync", headers=auth_headers, json={})
        assert resp.json() == {"importees": 1, "stock_maj": 0, "remboursements": 0, "depuis": resp.json()["depuis"]}

        resp = await client.get(f"/api/stock/{sample_lot.id}", headers=auth_headers)
        assert resp.json()["stock_kg"] == pytest.approx(10.0)


class TestVentesEtStats:
    async def test_stats_et_liste(self, client: AsyncClient, auth_headers):
        from datetime import datetime, timedelta, timezone
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        fausses = [
            _tx("TX010", montant=10.0, frais=0.2, ts=recent),
            _tx("TX011", montant=20.0, frais=0.4, ts=recent),
            _tx("TX012", statut="FAILED", montant=99.0, ts=recent),
        ]
        with (
            patch.dict(os.environ, {"SUMUP_API_KEY": "sup_sk_test"}),
            patch("services.sumup.lister_transactions", new_callable=AsyncMock, return_value=fausses),
        ):
            await client.post("/api/sumup/sync", headers=auth_headers, json={})

        resp = await client.get("/api/sumup/ventes", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["stats"]["nb_ventes"] == 2          # FAILED exclue des stats
        assert data["stats"]["ca_brut"] == pytest.approx(30.0)
        assert data["stats"]["frais"] == pytest.approx(0.6)
        assert data["stats"]["ca_net"] == pytest.approx(29.4)
        assert len(data["ventes"]) == 3                  # mais visible dans la liste

    async def test_statut(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/sumup/statut", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "configure" in data
        assert "nb_transactions" in data
