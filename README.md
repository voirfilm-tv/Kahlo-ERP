# Kahlo ERP

ERP interne Kahlo Café (FastAPI + PostgreSQL + Redis + React/Vite + Nginx + Docker Compose).

## Démarrage reproductible (from scratch)

```bash
git clone <repo>
cd Kahlo-ERP
cp .env.example .env
docker compose up --build
```

Services démarrés:
- **nginx** — point d'entrée / reverse proxy
- **frontend** — React build statique (Vite)
- **backend** — FastAPI
- **db** — PostgreSQL
- **redis**
- **caldav** — Radicale

Application:
- Frontend: `http://localhost`
- API: `http://localhost/api`
- Health backend: `http://localhost/api/health`

> Le script `start.sh` est conservé pour la commodité locale, mais la commande de référence pour la livraison reste `docker compose up --build`.

## Variables `.env`

La référence exhaustive et documentée est `./.env.example`.

Groupes de variables:
- **Infrastructure**: `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `HTTP_PORT`, `HTTPS_PORT`
- **Sécurité**: `SECRET_KEY`, `APP_USERNAME`, `APP_DEFAULT_PASSWORD`, `ADMIN_FORCE_RESET`, `SESSION_HOURS`, `LOGIN_MAX_ATTEMPTS`, `LOGIN_WINDOW_SECONDS`
- **CORS/API**: `CORS_ORIGINS`, `DATABASE_URL`, `REDIS_URL`
- **Intégrations**: `SUMUP_*`, `BREVO_*`, `GEMINI_*`, `GOOGLE_*`, `CALDAV_*`
- **Métier**: `BOUTIQUE_*`, `OBJECTIF_CA_MENSUEL`, `STOCK_*`, `CRM_*`
- **Exploitation**: `BACKUP_*`, `FACTURES_DIR`

Variables minimales à adapter avant production:
- `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY`, `APP_DEFAULT_PASSWORD`, `CALDAV_PASSWORD`, `CORS_ORIGINS`
- `BIND_HOST` (laisser `127.0.0.1` derrière un reverse proxy externe)
- `CORS_ORIGINS` limité aux domaines front réels
- Secrets API non vides seulement si intégration activée

## Admin

Au premier démarrage, si la table `utilisateurs` est vide:
- création auto de l'admin `APP_USERNAME`
- mot de passe `APP_DEFAULT_PASSWORD` (ou `APP_PASSWORD_HASH`)

Reset forcé admin:
1. définir `ADMIN_FORCE_RESET=true`
2. redémarrer le backend
3. remettre `ADMIN_FORCE_RESET=false`

## Migrations et seed

- Le backend applique `alembic upgrade head` au démarrage.
- En fallback, `Base.metadata.create_all()` est utilisé si Alembic échoue.
- Seed initial: fournisseurs + admin bootstrap.

## Tests

Backend:
```bash
.venv/bin/python -m pytest backend/tests -q
```

Frontend:
```bash
cd frontend
npm run build
```

## CI (GitHub Actions)

Une CI minimale et robuste est définie dans `.github/workflows/ci.yml` (push + pull request).

Elle vérifie automatiquement :
- installation backend + tests `pytest`,
- migrations Alembic sur PostgreSQL vierge,
- build frontend Vite,
- build de l'image Docker backend.

Voir la documentation détaillée et la reproduction locale : `docs/ci.md`.

## Production (résumé)

- Nginx sert de reverse proxy (service `nginx`).
- Ajuster `CORS_ORIGINS` à vos domaines réels.
- Monter vos certificats dans `nginx/ssl/`.
- Faire tourner la stack en arrière-plan:
  ```bash
  docker compose up -d --build
  ```


## Mise à jour logicielle (admin)

Une section **Paramètres > Mise à jour** permet de :
- vérifier la version installée vs la dernière release GitHub,
- lancer une mise à jour si l'environnement serveur le permet,
- sinon afficher un mode semi-automatique avec commandes sûres.

Documentation complète : `docs/software-update.md`.

## Exploitation

Logs:
```bash
docker compose logs -f backend
docker compose logs -f nginx
docker compose logs -f db
```

Sauvegarde DB:
```bash
docker compose exec db pg_dump -U kahlo kahlo > backup.sql
```

Restauration:
```bash
cat backup.sql | docker compose exec -T db psql -U kahlo kahlo
```

Rotation secrets:
1. Modifier les valeurs dans `.env`
2. Redéployer: `docker compose up -d --build`
3. Changement de `SECRET_KEY` invalide toutes les sessions actives

⚠️ Les dumps applicatifs backend sont écrits dans le volume persistant `backups_data` monté sur `/backups/kahlo`.

⚠️ `docker compose down -v` supprime **tous** les volumes nommés (`postgres_data`, `redis_data`, `uploads_data`, `factures_data`, `caldav_data`, `backups_data`).
