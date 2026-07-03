"""Tests — Investissements, scénarios de prix et calculatrice"""

import pytest
from httpx import AsyncClient


class TestInvestissementsCRUD:
    async def test_liste_vide(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/investissements/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_creation_et_calculs(self, client: AsyncClient, auth_headers):
        """Reproduit la ligne « imprimante » de l'Excel :
        73.46€ / 1 unité / amortie sur 300 ventes / 84 vendues."""
        resp = await client.post("/api/investissements/", headers=auth_headers, json={
            "nom": "imprimante",
            "categorie": "materiel",
            "valeur_totale": 73.46,
            "quantite": 1,
            "amortissement_unites": 300,
            "unites_vendues": 84,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["cout_unitaire"] == pytest.approx(73.46)
        assert data["cout_par_produit"] == pytest.approx(0.2449, abs=1e-4)
        assert data["somme_remboursee"] == pytest.approx(20.57, abs=0.01)
        assert data["restant"] == pytest.approx(52.89, abs=0.01)
        assert 0 < data["progression_pct"] < 100

    async def test_creation_consommable(self, client: AsyncClient, auth_headers):
        """Ligne « rouleau etiquette » : 22.59€ / 500 unités / amortie en 1 vente."""
        resp = await client.post("/api/investissements/", headers=auth_headers, json={
            "nom": "rouleau etiquette",
            "categorie": "consommable",
            "valeur_totale": 22.59,
            "quantite": 500,
            "amortissement_unites": 1,
            "unites_vendues": 84,
        })
        assert resp.status_code == 201
        data = resp.json()
        # Le serializer arrondit à 4 décimales (0.04518 → 0.0452)
        assert data["cout_par_produit"] == pytest.approx(0.04518, abs=1e-4)
        assert data["somme_remboursee"] == pytest.approx(3.80, abs=0.01)

    async def test_sur_amortissement_negatif(self, client: AsyncClient, auth_headers):
        """Ligne « sac kraft » : le restant peut être négatif (sur-amorti)."""
        resp = await client.post("/api/investissements/", headers=auth_headers, json={
            "nom": "sac kraft",
            "categorie": "consommable",
            "valeur_totale": 6.02,
            "quantite": 50,
            "amortissement_unites": 1,
            "unites_vendues": 75,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["restant"] == pytest.approx(-3.01, abs=0.01)
        assert data["progression_pct"] == 100

    async def test_modification(self, client: AsyncClient, auth_headers):
        create = await client.post("/api/investissements/", headers=auth_headers, json={
            "nom": "kakemono", "valeur_totale": 60.47, "amortissement_unites": 300,
        })
        inv_id = create.json()["id"]

        resp = await client.patch(f"/api/investissements/{inv_id}", headers=auth_headers, json={
            "unites_vendues": 84,
        })
        assert resp.status_code == 200
        assert resp.json()["somme_remboursee"] == pytest.approx(16.93, abs=0.01)

    async def test_enregistrer_vente(self, client: AsyncClient, auth_headers):
        create = await client.post("/api/investissements/", headers=auth_headers, json={
            "nom": "chocolat", "valeur_totale": 34.53, "quantite": 240, "unites_vendues": 10,
        })
        inv_id = create.json()["id"]

        resp = await client.post(f"/api/investissements/{inv_id}/vente", headers=auth_headers, json={
            "quantite": 5,
        })
        assert resp.status_code == 200
        assert resp.json()["unites_vendues"] == 15

    async def test_suppression(self, client: AsyncClient, auth_headers):
        create = await client.post("/api/investissements/", headers=auth_headers, json={
            "nom": "test", "valeur_totale": 10,
        })
        inv_id = create.json()["id"]

        resp = await client.delete(f"/api/investissements/{inv_id}", headers=auth_headers)
        assert resp.status_code == 204

        resp = await client.get(f"/api/investissements/{inv_id}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_validation_valeur_negative(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/investissements/", headers=auth_headers, json={
            "nom": "invalide", "valeur_totale": -5,
        })
        assert resp.status_code == 422

    async def test_auth_requise(self, client: AsyncClient):
        resp = await client.get("/api/investissements/")
        assert resp.status_code in (401, 403)


class TestStats:
    async def test_stats_vides(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/investissements/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_investi"] == 0
        assert data["progression_pct"] == 100

    async def test_stats_globales(self, client: AsyncClient, auth_headers):
        await client.post("/api/investissements/", headers=auth_headers, json={
            "nom": "a", "valeur_totale": 100, "amortissement_unites": 10, "unites_vendues": 5,
        })
        await client.post("/api/investissements/", headers=auth_headers, json={
            "nom": "b", "valeur_totale": 50, "amortissement_unites": 1, "unites_vendues": 60,
        })
        resp = await client.get("/api/investissements/stats", headers=auth_headers)
        data = resp.json()
        assert data["nb_investissements"] == 2
        assert data["total_investi"] == 150
        # a : 5 ventes × 10€/produit = 50€ remboursés ; b : sur-amorti, plafonné à 50€
        assert data["total_rembourse"] == pytest.approx(100, abs=0.01)
        assert data["nb_amortis"] == 1


class TestCalculatrice:
    async def test_formule_excel_pdv_expresso(self, client: AsyncClient, auth_headers):
        """Reproduit la feuille « PDV expresso » 250g de l'Excel :
        coûts 5.409947€, marge 42.7%, impôts 12.5%, sumup 1.75% → PV ≈ 9.00€."""
        resp = await client.post("/api/investissements/calculatrice", headers=auth_headers, json={
            "composants": [
                {"libelle": "prix d'achat+livraison", "valeur": 5.0},
                {"libelle": "emballage", "valeur": 0.13},
                {"libelle": "sticker", "valeur": 0.03508},
                {"libelle": "imprimante", "valeur": 0.2448666667},
            ],
            "marge_pct": 42.7,
            "taux_impots": 12.5,
            "taux_sumup": 1.75,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["prix_vente"] == pytest.approx(9.00, abs=0.01)
        assert data["marge_valeur"] == pytest.approx(2.31, abs=0.01)

    async def test_taux_cumules_invalides(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/investissements/calculatrice", headers=auth_headers, json={
            "composants": [{"libelle": "x", "valeur": 10}],
            "marge_pct": 30,
            "taux_impots": 60,
            "taux_sumup": 45,
        })
        assert resp.status_code == 422


class TestScenarios:
    async def test_cycle_de_vie_scenario(self, client: AsyncClient, auth_headers):
        # Création
        resp = await client.post("/api/investissements/scenarios", headers=auth_headers, json={
            "nom": "PDV expresso 250g",
            "composants": [
                {"libelle": "prix d'achat+livraison", "valeur": 5.0},
                {"libelle": "emballage", "valeur": 0.13},
            ],
            "marge_pct": 42.7,
            "taux_impots": 12.5,
            "taux_sumup": 1.75,
            "unites_vendues": 7,
        })
        assert resp.status_code == 201
        scenario = resp.json()
        assert scenario["prix_vente"] > 0
        assert scenario["marge_totale"] == pytest.approx(scenario["marge_valeur"] * 7, abs=0.01)

        # Liste
        resp = await client.get("/api/investissements/scenarios", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Modification (rentabilité : mise à jour des unités vendues)
        resp = await client.patch(
            f"/api/investissements/scenarios/{scenario['id']}",
            headers=auth_headers,
            json={"unites_vendues": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["unites_vendues"] == 10

        # Suppression
        resp = await client.delete(
            f"/api/investissements/scenarios/{scenario['id']}", headers=auth_headers
        )
        assert resp.status_code == 204

    async def test_scenario_taux_invalides(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/investissements/scenarios", headers=auth_headers, json={
            "nom": "invalide",
            "composants": [{"libelle": "x", "valeur": 1}],
            "taux_impots": 70,
            "taux_sumup": 40,
        })
        assert resp.status_code == 422
