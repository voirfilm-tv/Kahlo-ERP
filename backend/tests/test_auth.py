"""Tests — Authentification, JWT, rate limiting"""

import pytest
from httpx import AsyncClient


class TestLogin:
    async def test_login_success(self, client: AsyncClient, admin_user):
        resp = await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "testpassword123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "admin"
        assert data["username"] == "admin"

    async def test_login_wrong_password(self, client: AsyncClient, admin_user):
        resp = await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        assert "Identifiants incorrects" in resp.json()["detail"]

    async def test_login_unknown_user(self, client: AsyncClient, admin_user):
        resp = await client.post("/api/auth/login", json={
            "username": "inconnu",
            "password": "whatever",
        })
        assert resp.status_code == 401

    async def test_login_empty_username(self, client: AsyncClient):
        resp = await client.post("/api/auth/login", json={
            "username": "   ",
            "password": "test",
        })
        assert resp.status_code == 422

    async def test_login_empty_password(self, client: AsyncClient):
        resp = await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "",
        })
        assert resp.status_code == 422

    async def test_login_inactive_user(self, client: AsyncClient, db):
        from models import Utilisateur, RoleUtilisateur
        from routers.auth import pwd_context
        user = Utilisateur(
            username="inactif",
            nom="Inactif",
            password_hash=pwd_context.hash("test12345"),
            role=RoleUtilisateur.utilisateur,
            actif=False,
        )
        db.add(user)
        await db.commit()

        resp = await client.post("/api/auth/login", json={
            "username": "inactif",
            "password": "test12345",
        })
        assert resp.status_code == 401


class TestRateLimiting:
    async def test_rate_limit_after_max_attempts(self, client: AsyncClient, admin_user):
        for _ in range(5):
            await client.post("/api/auth/login", json={
                "username": "admin",
                "password": "wrong",
            })

        resp = await client.post("/api/auth/login", json={
            "username": "admin",
            "password": "testpassword123",
        })
        assert resp.status_code == 429
        assert "Trop de tentatives" in resp.json()["detail"]


class TestTokenValidation:
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        resp = await client.get("/api/clients/")
        assert resp.status_code in (401, 403)

    async def test_protected_endpoint_with_invalid_token(self, client: AsyncClient):
        resp = await client.get("/api/clients/", headers={
            "Authorization": "Bearer invalid-token-here",
        })
        assert resp.status_code == 401

    async def test_protected_endpoint_with_valid_token(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/clients/", headers=auth_headers)
        assert resp.status_code == 200


class TestHealthCheck:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
