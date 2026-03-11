"""
KAHLO CAFÉ — Configuration de test
Base SQLite async en mémoire, fixtures d'isolation, mocks des services externes.
"""

import sys
import os
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

# Ajouter le répertoire backend au path pour les imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Variables d'environnement AVANT tout import applicatif
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["APP_USERNAME"] = "admin"
os.environ["APP_DEFAULT_PASSWORD"] = "testpassword123"
os.environ["SESSION_HOURS"] = "1"

# ──────────────────────────────────────────────────
#  Mock des modules tiers manquants AVANT tout import
# ──────────────────────────────────────────────────

def _mock_module(name):
    """Insert a MagicMock as a module into sys.modules if not already present."""
    if name not in sys.modules:
        mock = MagicMock()
        mock.__file__ = f"<mock {name}>"
        # Make it behave like a package so sub-imports work
        mock.__path__ = []
        mock.__package__ = name
        sys.modules[name] = mock
    return sys.modules[name]

# All third-party modules that may be missing in the test environment
_MOCK_MODULES = [
    # Brevo
    "sib_api_v3_sdk", "sib_api_v3_sdk.rest",
    # Google
    "google", "google.generativeai", "google.auth", "google.auth.transport",
    "google.auth.transport.requests", "google.oauth2", "google.oauth2.credentials",
    "google.auth.exceptions", "google_auth_oauthlib", "google_auth_oauthlib.flow",
    "googleapiclient", "googleapiclient.discovery", "googleapiclient.errors",
    # CalDAV
    "caldav", "vobject",
    # PDF
    "weasyprint",
    # Scheduler
    "apscheduler", "apscheduler.schedulers", "apscheduler.schedulers.background",
    "apscheduler.schedulers.asyncio", "apscheduler.triggers",
    "apscheduler.triggers.cron", "apscheduler.triggers.interval",
    # Redis
    "redis", "redis.asyncio", "hiredis",
]

for _mod_name in _MOCK_MODULES:
    _mock_module(_mod_name)

# ──────────────────────────────────────────────────
#  Imports applicatifs (après les mocks)
# ──────────────────────────────────────────────────

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from database import Base, get_db
from models import (
    Utilisateur, RoleUtilisateur, Fournisseur, Lot, Client,
    Commande, LigneCommande, Marche, Evenement, StatutCommande,
    StatutMarche, TypeEvenement,
)
from routers.auth import pwd_context, _login_attempts


# ──────────────────────────────────────────────────
#  Engine & session factory pour les tests
# ──────────────────────────────────────────────────

_test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    echo=False,
    connect_args={"check_same_thread": False},
)

_TestSessionLocal = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ──────────────────────────────────────────────────
#  Fixtures
# ──────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Crée les tables avant chaque test, les supprime après."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Reset rate limiting entre les tests
    _login_attempts.clear()


async def _override_get_db():
    async with _TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture
async def db():
    """Session DB isolée pour manipulations directes dans les tests."""
    async with _TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    """Client HTTP HTTPX pointant vers l'app FastAPI avec DB de test."""
    import routers.clients as _rc
    import routers.commandes as _rco
    import routers.marches as _rm
    import routers.calendrier as _rcal
    import routers.stock as _rs

    with (
        patch.object(_rc, "sync_client_brevo", new_callable=AsyncMock),
        patch.object(_rco, "notifier_commande_prete", new_callable=AsyncMock),
        patch.object(_rco, "notifier_client_paiement_recu", new_callable=AsyncMock),
        patch.object(_rco, "creer_checkout", new_callable=AsyncMock, return_value={"checkout_id": "mock-checkout-id"}),
        patch.object(_rco, "get_checkout", new_callable=AsyncMock, return_value={"status": "PAID"}),
        patch.object(_rco, "generer_facture_pdf", new_callable=AsyncMock, return_value="/tmp/test.pdf"),
        patch.object(_rco, "decrementer_stock", new_callable=AsyncMock),
        patch.object(_rm, "creer_evenement_caldav", new_callable=AsyncMock, return_value=None),
        patch.object(_rm, "creer_evenement_google", new_callable=AsyncMock, return_value=None),
        patch.object(_rcal, "creer_evenement_caldav", new_callable=AsyncMock, return_value=None),
        patch.object(_rcal, "sync_caldav_vers_db", new_callable=AsyncMock, return_value=[]),
        patch.object(_rcal, "sync_google_vers_db", new_callable=AsyncMock, return_value=[]),
        patch.object(_rs, "calculer_epuisement", return_value={"jours_restants": 30, "date_estimee": "2026-04-10"}),
        patch.object(_rs, "recommander_assortiment", new_callable=AsyncMock, return_value="Recommandation test"),
    ):
        from main import app

        app.dependency_overrides[get_db] = _override_get_db

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession):
    """Crée un utilisateur admin et retourne l'objet."""
    user = Utilisateur(
        username="admin",
        nom="Admin Test",
        password_hash=pwd_context.hash("testpassword123"),
        role=RoleUtilisateur.admin,
        actif=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, admin_user) -> str:
    """Connecte l'admin et retourne le token JWT."""
    resp = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "testpassword123",
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(admin_token: str) -> dict:
    """Headers d'authentification prêts à l'emploi."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def sample_fournisseur(db: AsyncSession):
    """Crée un fournisseur de test."""
    f = Fournisseur(nom="Test Imports", email="test@imports.fr", pays="France", delai_moyen=5, score=4.5)
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return f


@pytest_asyncio.fixture
async def sample_lot(db: AsyncSession, sample_fournisseur):
    """Crée un lot de test avec du stock."""
    lot = Lot(
        fournisseur_id=sample_fournisseur.id,
        origine="Éthiopie Yirgacheffe",
        numero_lot="LOT-TEST-001",
        stock_kg=10.0,
        seuil_alerte_kg=3.0,
        prix_achat_kg=15.0,
        prix_vente_kg=30.0,
        actif=True,
    )
    db.add(lot)
    await db.commit()
    await db.refresh(lot)
    return lot


@pytest_asyncio.fixture
async def sample_client(db: AsyncSession):
    """Crée un client de test."""
    c = Client(
        prenom="Marie",
        nom="Dupont",
        email="marie@test.fr",
        telephone="0600000000",
        ville="Lyon",
        tampons=0,
        vip=False,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c
