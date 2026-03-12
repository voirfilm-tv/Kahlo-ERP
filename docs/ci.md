# CI GitHub Actions (Kahlo-ERP)

Ce projet utilise un workflow unique `.github/workflows/ci.yml` déclenché sur chaque `push` et `pull_request`.

## Objectif

Détecter rapidement les régressions critiques :
- backend qui ne s’installe plus,
- tests backend cassés,
- migrations Alembic invalides sur PostgreSQL vierge,
- frontend qui ne build plus.

## Jobs exécutés

### 1) `backend` — Build backend + tests
Depuis `backend/` :
1. Installation des dépendances Python (`pip install -r requirements.txt`)
2. Smoke test simple (`python -c "from main import app"`)
3. Exécution des tests backend (`pytest -q`)
4. Build image Docker backend (`docker build -f Dockerfile .`)

Variables d’environnement minimales injectées pour CI :
- `DATABASE_URL=sqlite+aiosqlite://` (tests isolés, rapides)
- `SECRET_KEY=ci-secret-key`
- `APP_DEFAULT_PASSWORD=changeme`
- `REDIS_URL=redis://localhost:6379/0`

### 2) `migrations` — Alembic sur PostgreSQL vierge
Depuis `backend/` :
1. Démarrage d’un service GitHub Actions `postgres:16`
2. Installation des dépendances Python
3. `alembic upgrade head`
4. `alembic current` pour vérifier que le head est atteint

Variable clé :
- `DATABASE_URL=postgresql://kahlo:kahlo@localhost:5432/kahlo_ci`

### 3) `frontend` — Install + build Vite
Depuis `frontend/` :
1. Installation dépendances (`npm ci`)
2. Build production (`npm run build`)

## Reproduire localement les mêmes vérifications

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite+aiosqlite:// SECRET_KEY=ci-secret-key APP_DEFAULT_PASSWORD=changeme REDIS_URL=redis://localhost:6379/0 python -c "from main import app; print(app.title)"
DATABASE_URL=sqlite+aiosqlite:// SECRET_KEY=ci-secret-key APP_DEFAULT_PASSWORD=changeme REDIS_URL=redis://localhost:6379/0 pytest -q
docker build -t kahlo-backend-ci -f Dockerfile .
```

### Migrations Alembic (PostgreSQL vierge)
```bash
# Exemple avec Docker local

docker run --rm --name kahlo-pg-ci \
  -e POSTGRES_DB=kahlo_ci \
  -e POSTGRES_USER=kahlo \
  -e POSTGRES_PASSWORD=kahlo \
  -p 5432:5432 -d postgres:16

cd backend
source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=postgresql://kahlo:kahlo@localhost:5432/kahlo_ci alembic upgrade head
DATABASE_URL=postgresql://kahlo:kahlo@localhost:5432/kahlo_ci alembic current

docker stop kahlo-pg-ci
```

### Frontend
```bash
cd frontend
npm ci
npm run build
```
