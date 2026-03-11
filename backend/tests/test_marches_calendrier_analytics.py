"""Tests — Marchés, Calendrier, Analytics"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta


class TestMarches:
    async def test_get_marches_empty(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/marches/", headers=auth_headers)
        assert resp.status_code == 200

    async def test_create_marche(self, client: AsyncClient, auth_headers):
        future = (datetime.now() + timedelta(days=7)).isoformat()
        resp = await client.post("/api/marches/", headers=auth_headers, json={
            "nom": "Marché Croix-Rousse",
            "lieu": "Place Croix-Rousse, Lyon",
            "date": future,
            "frais_prevus": 50.0,
        })
        assert resp.status_code == 201

    async def test_marches_a_venir(self, client: AsyncClient, auth_headers, db):
        from models import Marche, StatutMarche
        m = Marche(
            nom="Futur Marché",
            date=datetime.now() + timedelta(days=10),
            statut=StatutMarche.confirme,
        )
        db.add(m)
        await db.commit()

        resp = await client.get("/api/marches/a_venir", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_changer_statut_marche(self, client: AsyncClient, auth_headers, db):
        from models import Marche
        m = Marche(nom="Test Statut", date=datetime.now() + timedelta(days=5))
        db.add(m)
        await db.commit()
        await db.refresh(m)

        resp = await client.patch(
            f"/api/marches/{m.id}/statut?statut=confirme",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["statut"] == "confirme"

    async def test_saisir_bilan(self, client: AsyncClient, auth_headers, db):
        from models import Marche, StatutMarche
        m = Marche(
            nom="Marché Terminé",
            date=datetime.now() - timedelta(days=1),
            statut=StatutMarche.confirme,
        )
        db.add(m)
        await db.commit()
        await db.refresh(m)

        resp = await client.post(f"/api/marches/{m.id}/bilan", headers=auth_headers, json={
            "ca_realise": 450.0,
            "stock_emmene_kg": 10.0,
            "stock_ramene_kg": 3.0,
            "frais_reels": 60.0,
            "nb_clients": 25,
            "meteo": "ensoleillé",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ca"] == 450.0
        assert data["marge_nette"] == 390.0
        assert data["taux_ecoulement"] == 70


class TestCalendrier:
    async def test_get_evenements(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/calendrier/", headers=auth_headers)
        assert resp.status_code == 200

    async def test_create_evenement(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/calendrier/", headers=auth_headers, json={
            "type": "rappel",
            "titre": "Rappeler le fournisseur",
            "date_debut": (datetime.now() + timedelta(days=2)).isoformat(),
            "all_day": True,
        })
        assert resp.status_code == 201

    async def test_delete_evenement(self, client: AsyncClient, auth_headers, db):
        from models import Evenement, TypeEvenement
        ev = Evenement(
            type=TypeEvenement.rappel,
            titre="A supprimer",
            date_debut=datetime.now(),
        )
        db.add(ev)
        await db.commit()
        await db.refresh(ev)

        resp = await client.delete(f"/api/calendrier/{ev.id}", headers=auth_headers)
        assert resp.status_code == 200


class TestAnalytics:
    async def test_dashboard(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/analytics/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "ca_mois" in data
        assert "ca_semaine" in data
        assert "commandes_attente" in data
        assert "stocks_critiques" in data

    async def test_ca_mensuel(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/analytics/ca-mensuel?mois=3", headers=auth_headers)
        assert resp.status_code == 200

    async def test_general(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/analytics/general?mois=6", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "ca_total" in data
        assert "nb_commandes" in data
        assert "panier_moyen" in data

    async def test_analytics_marches(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/analytics/marches", headers=auth_headers)
        assert resp.status_code == 200
        assert "marches" in resp.json()

    async def test_analytics_origines(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/analytics/origines", headers=auth_headers)
        assert resp.status_code == 200
        assert "origines" in resp.json()

    async def test_analytics_clients(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/analytics/clients", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "top_clients" in data
