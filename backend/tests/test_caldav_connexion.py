"""Tests — CalDAV zéro-config : connexion appareils, profil Apple, rotation"""

import os
import pytest
from unittest.mock import patch
from httpx import AsyncClient

from services.caldav_admin import ecrire_htpasswd, regenerer_mot_de_passe
from services import caldav_admin


class TestConnexion:
    async def test_infos_connexion(self, client: AsyncClient, auth_headers):
        with patch.dict(os.environ, {"CALDAV_USER": "kahlo", "CALDAV_PASSWORD": "motdepasse-genere"}):
            resp = await client.get("/api/calendrier/connexion", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "kahlo"
        assert data["password"] == "motdepasse-genere"
        assert data["url"].endswith("/caldav/kahlo/")
        assert "frequence_secondes" in data

    async def test_url_derivee_de_public_base_url(self, client: AsyncClient, auth_headers):
        with patch.dict(os.environ, {"PUBLIC_BASE_URL": "https://erp.kahlo.fr"}):
            resp = await client.get("/api/calendrier/connexion", headers=auth_headers)
        assert resp.json()["url"] == "https://erp.kahlo.fr/caldav/kahlo/"

    async def test_reserve_admin(self, client: AsyncClient):
        resp = await client.get("/api/calendrier/connexion")
        assert resp.status_code in (401, 403)


class TestProfilApple:
    async def test_flux_complet_qr(self, client: AsyncClient, auth_headers):
        """Génération du lien signé → téléchargement du .mobileconfig sans session."""
        with patch.dict(os.environ, {"CALDAV_USER": "kahlo", "CALDAV_PASSWORD": "secret-caldav",
                                     "PUBLIC_BASE_URL": "https://erp.kahlo.fr"}):
            r = await client.post("/api/calendrier/connexion/lien-apple", headers=auth_headers)
            assert r.status_code == 200
            url = r.json()["url"]
            assert "/api/calendrier/profil-apple?token=" in url

            token = url.split("token=")[1]
            # Le téléphone qui scanne n'a PAS de session : pas de header auth
            r2 = await client.get(f"/api/calendrier/profil-apple?token={token}")
        assert r2.status_code == 200
        assert r2.headers["content-type"].startswith("application/x-apple-aspen-config")
        corps = r2.content.decode()
        assert "com.apple.caldav.account" in corps
        assert "kahlo" in corps
        assert "secret-caldav" in corps
        assert "erp.kahlo.fr" in corps

    async def test_token_invalide_refuse(self, client: AsyncClient):
        resp = await client.get("/api/calendrier/profil-apple?token=nimporte-quoi")
        assert resp.status_code == 403

    async def test_token_de_session_refuse(self, client: AsyncClient, admin_token):
        """Un JWT de session (type différent) ne doit pas donner le profil."""
        resp = await client.get(f"/api/calendrier/profil-apple?token={admin_token}")
        assert resp.status_code == 403


class TestGestionMotDePasse:
    def test_ecrire_htpasswd(self, tmp_path):
        with patch.object(caldav_admin, "_HTPASSWD_PATH", tmp_path / "users"):
            assert ecrire_htpasswd("kahlo", "monmotdepasse") is True
            contenu = (tmp_path / "users").read_text()
            assert contenu.startswith("kahlo:$2b$")

    async def test_regeneration(self, client: AsyncClient, auth_headers, tmp_path, monkeypatch):
        monkeypatch.setenv("ENV_FILE_PATH", "/app/tests-inexistant/config.env")
        with (
            patch.object(caldav_admin, "_HTPASSWD_PATH", tmp_path / "users"),
            patch.object(caldav_admin, "_persister_config",
                         lambda cle, val: os.environ.__setitem__(cle, val)),
        ):
            resp = await client.post("/api/calendrier/connexion/regenerer", headers=auth_headers)
            assert resp.status_code == 200
            nouveau = resp.json()["password"]
            assert len(nouveau) >= 12
            assert os.environ["CALDAV_PASSWORD"] == nouveau
            assert (tmp_path / "users").read_text().startswith("kahlo:$2b$")

    async def test_regeneration_echec_volume(self, client: AsyncClient, auth_headers):
        with patch.object(caldav_admin, "ecrire_htpasswd", return_value=False):
            resp = await client.post("/api/calendrier/connexion/regenerer", headers=auth_headers)
        assert resp.status_code == 500
        assert "volume" in resp.json()["detail"].lower() or "caldav_data" in resp.json()["detail"]

    def test_assurer_identifiants_genere_si_faible(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CALDAV_PASSWORD", "changeme")
        genere = {}
        with (
            patch.object(caldav_admin, "_HTPASSWD_PATH", tmp_path / "users"),
            patch.object(caldav_admin, "_persister_config",
                         lambda cle, val: genere.update({cle: val}) or os.environ.__setitem__(cle, val)),
        ):
            caldav_admin.assurer_identifiants()
        assert genere.get("CALDAV_PASSWORD") and genere["CALDAV_PASSWORD"] != "changeme"
        assert (tmp_path / "users").exists()


class TestFrequenceSync:
    async def test_frequence_1_seconde_acceptee(self, client: AsyncClient, auth_headers, monkeypatch):
        monkeypatch.setenv("ENV_FILE_PATH", str("/app/tests-inexistant/config.env"))
        import routers.parametres as rp
        with patch.object(rp, "_ecrire_cle", lambda k, v: os.environ.__setitem__(k, v)):
            resp = await client.post("/api/parametres/", headers=auth_headers, json={
                "calendrier": {"caldav_interval": "1"},
            })
        assert resp.status_code == 200
        assert os.environ["CALDAV_INTERVAL_SECONDS"] == "1"

    async def test_frequence_invalide_refusee(self, client: AsyncClient, auth_headers):
        import routers.parametres as rp
        with patch.object(rp, "_ecrire_cle", lambda k, v: None):
            resp = await client.post("/api/parametres/", headers=auth_headers, json={
                "calendrier": {"caldav_interval": "0"},
            })
        assert resp.status_code == 400
