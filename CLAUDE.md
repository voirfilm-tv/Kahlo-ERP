# Kahlo Café — ERP · Guide pour Claude

## Vue d'ensemble du projet

ERP sur mesure pour Kahlo Café, torréfaction artisanale lyonnaise. Gère les stocks, fournisseurs, clients, commandes, marchés, calendrier et analytique.

---

## Architecture

```
kahlo-erp/
├── backend/          # FastAPI (Python 3.12)
│   ├── main.py       # Point d'entrée — routeurs + lifespan
│   ├── models.py     # Modèles SQLAlchemy ORM
│   ├── database.py   # Connexion async PostgreSQL
│   ├── routers/      # Endpoints par domaine métier
│   └── services/     # Logique métier & intégrations externes
├── frontend/         # React 18 + Vite
│   └── src/
│       ├── main.jsx  # Point d'entrée React — router + providers
│       ├── pages/    # Une page par module fonctionnel
│       ├── components/
│       ├── services/ # api.js — client Axios centralisé
│       ├── stores/   # État global Zustand (auth.js)
│       └── hooks/    # useOfflineSync.js
├── nginx/            # Reverse proxy (nginx.conf)
├── docker-compose.yml
└── start.sh          # CLI dev/prod/stop/reset
```

---

## Stack technique

| Couche | Technologie |
|---|---|
| Frontend | React 18, Vite, React Router v6, Zustand, TanStack React Query, Recharts, Axios |
| Backend | FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, APScheduler |
| Base de données | PostgreSQL 16 (asyncpg) |
| Cache / Queue | Redis 7 |
| Calendrier | Radicale (CalDAV) |
| Proxy | Nginx |
| Conteneurs | Docker + Docker Compose |
| Intégrations | Google Gemini, SumUp, Brevo, Google Calendar, WeasyPrint |

---

## Commandes de développement

### Démarrage

```bash
# Développement (logs en direct)
./start.sh dev

# Production (arrière-plan)
./start.sh prod

# Arrêt
./start.sh stop

# Reset complet (⚠ supprime les données)
./start.sh reset
```

### Docker utile

```bash
# Logs backend en temps réel
docker-compose logs -f backend

# Accéder à la base de données
docker exec -it kahlo_db psql -U kahlo -d kahlo

# Rebuild un seul service
docker-compose up --build backend
```

### Frontend (sans Docker)

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
npm run build
```

### Backend (sans Docker)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## Configuration — Variables d'environnement

Créer `.env` à la racine à partir de `.env.example`. Variables requises :

| Variable | Service | Obligatoire |
|---|---|---|
| `POSTGRES_PASSWORD` | PostgreSQL | Oui |
| `SECRET_KEY` | JWT auth | Oui |
| `GEMINI_API_KEY` | Google Gemini IA | Oui |
| `SUMUP_API_KEY` | Paiements | Oui |
| `SUMUP_CLIENT_ID` | SumUp OAuth | Oui |
| `SUMUP_CLIENT_SECRET` | SumUp OAuth | Oui |
| `SUMUP_WEBHOOK_SECRET` | Webhooks SumUp | Oui |
| `BREVO_API_KEY` | Emails | Oui |
| `GOOGLE_CLIENT_ID` | Google Calendar | Optionnel |
| `GOOGLE_CLIENT_SECRET` | Google Calendar | Optionnel |

---

## Structure Backend

### Routeurs (`backend/routers/`)

| Fichier | Préfixe API | Domaine |
|---|---|---|
| `auth.py` | `/api/auth` | Authentification JWT |
| `stock.py` | `/api/stock` | Lots de café, inventaire |
| `fournisseurs.py` | `/api/fournisseurs` | Contacts fournisseurs |
| `clients.py` | `/api/clients` | CRM clients |
| `commandes.py` | `/api/commandes` | Commandes clients |
| `marches.py` | `/api/marches` | Événements marchés |
| `calendrier.py` | `/api/calendrier` | CalDAV + Google Calendar |
| `analytics.py` | `/api/analytics` | Tableaux de bord & stats |
| `webhooks.py` | `/api/webhooks` | Webhooks SumUp |
| `ia.py` | `/api/ia` | Analyse Gemini |
| `parametres.py` | `/api/parametres` | Configuration globale |

### Services (`backend/services/`)

| Fichier | Rôle |
|---|---|
| `ia.py` | Intégration Google Gemini API |
| `calendrier.py` | Sync CalDAV + Google Calendar OAuth |
| `offline_sync.py` | Queue Redis pour mode terrain sans internet |
| `scheduler.py` | Tâches planifiées (APScheduler) |
| `brevo.py` | Envoi d'emails transactionnels |
| `factures.py` | Génération PDF (WeasyPrint) |
| `stock.py` | Logique métier stock |
| `sumup.py` | Intégration paiements SumUp |

### Modèles principaux (`backend/models.py`)

- `Fournisseur` — fournisseurs de café
- `Lot` — lot de café (origine, stock_kg, prix, DLC, seuil alerte)
- `Client` — profils clients avec `ProfilKahlo` (florale/intense/douce/aventuriere)
- `Commande` + `LigneCommande` — commandes avec statuts (`en_attente`, `prete`, `remise`, `annulee`)
- `Marche` — marchés et événements avec statut (`tentative`, `confirme`, `passe`, `annule`)
- `CommandeFournisseur` — bons de commande fournisseurs

---

## Structure Frontend

### Pages (`frontend/src/pages/`)

| Page | Route | Description |
|---|---|---|
| `Login.jsx` | `/login` | Authentification |
| `Dashboard.jsx` | `/` | Vue temps réel |
| `Stock.jsx` | `/stock` | Gestion des lots |
| `Clients.jsx` | `/clients` | CRM |
| `Commandes.jsx` | `/commandes` | Suivi commandes |
| `Calendrier.jsx` | `/calendrier` | Agenda + marchés |
| `Analytics.jsx` | `/analytics` | Stats & graphiques |
| `Parametres.jsx` | `/parametres` | Configuration |

### Patterns clés

- **Auth** : token JWT dans Zustand store (`stores/auth.js`), routes protégées via `<PrivateRoute>`
- **API** : client Axios centralisé dans `services/api.js` — proxy Vite vers `http://localhost:8000` en dev
- **Données** : TanStack React Query pour le fetching/cache (`staleTime: 30s`, `retry: 1`)
- **Offline** : hook `useOfflineSync.js` — queue Redis via backend

---

## Points d'entrée principaux

- **Backend** : `backend/main.py` — app FastAPI, middleware CORS, montage des routeurs, `lifespan` (init DB + scheduler)
- **Frontend** : `frontend/src/main.jsx` — root React, BrowserRouter, QueryClientProvider, routes
- **Health check** : `GET /api/health` → `{"status": "ok"}`
- **Docs API** : `http://localhost/api/docs` (Swagger UI automatique FastAPI)

---

## URLs en développement

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| CalDAV | http://localhost/caldav/ |

---

## Réseau Docker

Tous les services sont sur le réseau `kahlo_network`. Le backend accède à la DB via `db:5432` et Redis via `redis:6379`. Nginx route :
- `/api/*` → `backend:8000`
- `/caldav/*` → `caldav:5232`
- `/*` → frontend (SPA)

---

## Tests

Aucune suite de tests n'est actuellement en place dans ce projet.

---

## Contraintes & notes importantes

- **RAM** : budget ~400MB total (machine 4GB). Ne pas dépasser les limites définies dans `docker-compose.yml`
- **Async** : le backend est entièrement async — toujours utiliser `async/await` et `asyncpg` pour les requêtes DB
- **Session DB** : injecter via `Depends(get_db)` dans chaque endpoint, ne jamais créer de session manuellement
- **SumUp** : pas de SDK officiel — intégration via API REST HTTP (httpx)
- **CalDAV** : sync bidirectionnelle Apple Calendar via Radicale ; Google Calendar via OAuth
- **Webhooks SumUp** : route `/api/webhooks/sumup` configurée en bypass SSL dans nginx (pas de redirect HTTPS)
- **Mode offline** : les ventes en terrain (sans internet) sont mises en queue Redis et synchronisées dans cet ordre : stock → commandes → CRM → calendrier
