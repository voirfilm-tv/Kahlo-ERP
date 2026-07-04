"""Tests — CalDAV zéro-config : connexion appareils, profil Apple, rotation"""

import os
import plistlib
import pytest
from unittest.mock import AsyncMock, patch
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

    async def test_url_selfhost_conserve_le_port_du_host(self, client: AsyncClient, auth_headers):
        headers = {**auth_headers, "host": "192.168.1.50:8087"}
        with patch.dict(os.environ, {"PUBLIC_BASE_URL": "", "CALDAV_USER": "kahlo"}):
            resp = await client.get("/api/calendrier/connexion", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["url"] == "http://192.168.1.50:8087/caldav/kahlo/"

    async def test_url_reverse_proxy_https_utilise_headers_forwarded(self, client: AsyncClient, auth_headers):
        headers = {
            **auth_headers,
            "host": "backend-interne",
            "x-forwarded-proto": "https",
            "x-forwarded-host": "erp.kahlo.fr",
        }
        with patch.dict(os.environ, {"PUBLIC_BASE_URL": "", "CALDAV_USER": "kahlo"}):
            resp = await client.get("/api/calendrier/connexion", headers=headers)
        assert resp.status_code == 200
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
            assert r.json()["download_url"].endswith("&download=1")

            token = url.split("token=")[1]
            # Le téléphone qui scanne n'a PAS de session : pas de header auth
            r2 = await client.get(f"/api/calendrier/profil-apple?token={token}")
        assert r2.status_code == 200
        assert r2.headers["content-type"].startswith("application/x-apple-aspen-config")
        assert r2.headers["content-disposition"] == 'inline; filename="kahlo-calendrier.mobileconfig"'
        profil = plistlib.loads(r2.content)
        compte = profil["PayloadContent"][0]
        assert compte["PayloadType"] == "com.apple.caldav.account"
        assert compte["CalDAVHostName"] == "erp.kahlo.fr"
        assert compte["CalDAVPort"] == 443
        assert compte["CalDAVUseSSL"] is True
        assert compte["CalDAVUsername"] == "kahlo"
        assert compte["CalDAVPassword"] == "secret-caldav"
        assert compte["CalDAVPrincipalURL"] == "/caldav/kahlo/"

    async def test_profil_apple_http_local_affiche_page_aide_et_telechargement_direct(self, client: AsyncClient, auth_headers):
        with patch.dict(os.environ, {"CALDAV_USER": "kahlo", "CALDAV_PASSWORD": "secret-caldav",
                                     "PUBLIC_BASE_URL": "http://192.168.1.50:8087"}):
            r = await client.post("/api/calendrier/connexion/lien-apple", headers=auth_headers)
            token = r.json()["url"].split("token=")[1]

            page = await client.get(
                f"/api/calendrier/profil-apple?token={token}",
                headers={"accept": "text/html"},
            )
            direct = await client.get(f"/api/calendrier/profil-apple?token={token}&download=1")

        assert page.status_code == 200
        assert page.headers["content-type"].startswith("text/html")
        assert "l'installation automatique peut nécessiter HTTPS" in page.text
        assert "Réglages → Apps → Calendrier" in page.text
        assert "http://192.168.1.50:8087/caldav/kahlo/" in page.text

        assert direct.status_code == 200
        assert direct.headers["content-type"].startswith("application/x-apple-aspen-config")
        assert direct.headers["content-disposition"] == 'inline; filename="kahlo-calendrier.mobileconfig"'
        compte = plistlib.loads(direct.content)["PayloadContent"][0]
        assert compte["CalDAVHostName"] == "192.168.1.50"
        assert compte["CalDAVPort"] == 8087
        assert compte["CalDAVUseSSL"] is False

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

    def test_mot_de_passe_affiche_correspond_au_htpasswd(self, tmp_path):
        with patch.object(caldav_admin, "_HTPASSWD_PATH", tmp_path / "users"):
            assert ecrire_htpasswd("kahlo", "motdepasse-erp") is True
            assert caldav_admin.verifier_mot_de_passe_htpasswd("kahlo", "motdepasse-erp")["ok"] is True
            assert caldav_admin.verifier_mot_de_passe_htpasswd("kahlo", "autre")["ok"] is False

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


class TestDiagnosticCalDAV:
    async def test_diagnostic_ok_avec_identifiants_affiches(self, client: AsyncClient, auth_headers, tmp_path):
        fake_propfind = AsyncMock(return_value={
            "ok": True,
            "code": "ok",
            "status_code": 207,
            "message": "Authentification CalDAV OK",
        })
        with (
            patch.object(caldav_admin, "_HTPASSWD_PATH", tmp_path / "users"),
            patch.object(caldav_admin, "tester_auth_caldav", fake_propfind),
            patch.dict(os.environ, {
                "CALDAV_USER": "kahlo",
                "CALDAV_PASSWORD": "motdepasse-erp",
                "CALDAV_BASE_URL": "http://caldav:5232",
                "PUBLIC_BASE_URL": "http://192.168.1.50:8087",
            }),
        ):
            assert ecrire_htpasswd("kahlo", "motdepasse-erp") is True
            resp = await client.post("/api/calendrier/connexion/verifier", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["niveau"] == "attention"
        assert data["url"] == "http://192.168.1.50:8087/caldav/kahlo/"
        assert any(c["code"] == "htpasswd_password" and c["ok"] for c in data["checks"])
        assert any(c["code"] == "radicale_interne" and c["ok"] for c in data["checks"])
        assert any(c["code"] == "url_externe" and c["ok"] for c in data["checks"])
        assert any(c["code"] == "apple_https" and c["niveau"] == "attention" for c in data["checks"])

    async def test_diagnostic_signale_mauvais_mot_de_passe_htpasswd(self, client: AsyncClient, auth_headers, tmp_path):
        fake_propfind = AsyncMock(return_value={
            "ok": False,
            "code": "mauvais_identifiants",
            "status_code": 401,
            "message": "Mauvais identifiants",
        })
        with (
            patch.object(caldav_admin, "_HTPASSWD_PATH", tmp_path / "users"),
            patch.object(caldav_admin, "tester_auth_caldav", fake_propfind),
            patch.dict(os.environ, {
                "CALDAV_USER": "kahlo",
                "CALDAV_PASSWORD": "motdepasse-erp",
                "PUBLIC_BASE_URL": "https://erp.kahlo.fr",
            }),
        ):
            assert ecrire_htpasswd("kahlo", "autre-motdepasse") is True
            resp = await client.post("/api/calendrier/connexion/verifier", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is False
        assert data["niveau"] == "erreur"
        assert "ne correspond pas" in data["message"]
        assert any(c["code"] == "htpasswd_password" and not c["ok"] for c in data["checks"])
