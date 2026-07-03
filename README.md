# Kahlo ERP

ERP interne Kahlo Café (FastAPI + PostgreSQL + Redis + React/Vite + Nginx + Docker Compose).

---

## Stack technique

| Service | Techno | RAM |
|---|---|---|
| Frontend | React + Vite + Nginx | ~20 Mo |
| Backend | FastAPI (Python 3.12) | ~120 Mo |
| Base de données | PostgreSQL 16 | ~80 Mo |
| Cache + offline | Redis 7 | ~30 Mo |
| Calendrier | Radicale (CalDAV) | ~30 Mo |
| Proxy | Nginx 1.27 | ~10 Mo |
| **Total** | | **~290 Mo** |

## Modules

- **Dashboard** — Vue d'ensemble temps réel
- **Stock** — Lots par origine, alertes seuils, marges
- **Fournisseurs** — Contacts, scores, commandes d'achat
- **CRM** — Clients, profils Kahlo, fidélité par tampons
- **Commandes** — Suivi, statuts, paiement SumUp, factures PDF
- **Investissements** — Suivi des achats, amortissement par produit vendu, calculatrice de prix de vente (marge, impôts, SumUp), rentabilité par produit
- **Calendrier** — Marchés, événements, sync CalDAV + Google
- **Analytics** — CA mensuel, top origines, tendances, saisonnalité

## Intégrations

| Service | Usage | Requis ? |
|---|---|---|
| **SumUp** | Paiements + webhooks temps réel | Non (mode espèces) |
| **Google Gemini** | IA : analyses, suggestions, fiches produit | Non (fonctionnel sans) |
| **Brevo** | Emails : anniversaires, relances, notifications | Non |
| **Google Calendar** | Sync bidirectionnelle | Non |
| **Apple Calendar** | Sync bidirectionnelle via CalDAV (Radicale) | Inclus |

---

## Installation locale

### Prérequis

- Docker >= 24.0 + Docker Compose >= 2.20
- 2 Go RAM minimum (4 Go recommandé)
- Linux / macOS / Windows WSL2
- Ports 80 et 443 disponibles (ou configurables via `HTTP_PORT` / `HTTPS_PORT`)

### Démarrage rapide

```bash
# 1. Cloner le projet
git clone <url-du-repo> Kahlo-ERP
cd Kahlo-ERP

# 2. Copier la configuration
cp .env.example .env

# 3. Construire et lancer (première exécution : ~2-3 min)
docker compose up --build
```

C'est tout. L'application est disponible sur **http://localhost**.

Services démarrés:
- **nginx** — point d'entrée / reverse proxy
- **frontend** — React build statique (Vite)
- **backend** — FastAPI
- **db** — PostgreSQL
- **redis**
- **caldav** — Radicale

Accès:
- Interface web : http://localhost
- API docs (dev uniquement) : http://localhost/api/docs
- CalDAV : http://localhost/caldav/
- Health check : http://localhost/api/health

> Le script `start.sh` est conservé pour la commodité locale, mais la commande de référence pour la livraison reste `docker compose up --build`.

### Connexion initiale

- **Utilisateur** : `kahlo` (configurable via `APP_USERNAME`)
- **Mot de passe** : `changeme` (configurable via `APP_DEFAULT_PASSWORD`)

> Changez le mot de passe immédiatement après le premier login.

---

## Variables d'environnement

La référence exhaustive et documentée est `./.env.example`. Voici les groupes principaux :

### Obligatoires

| Variable | Description | Valeur dev par défaut |
|---|---|---|
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL | `kahlo_dev_2024` |
| `SECRET_KEY` | Clé de signature JWT | Auto-générée si absente |

### Authentification

| Variable | Description | Valeur par défaut |
|---|---|---|
| `APP_USERNAME` | Nom d'utilisateur admin initial | `kahlo` |
| `APP_DEFAULT_PASSWORD` | Mot de passe admin initial (clair) | `changeme` |
| `ADMIN_FORCE_RESET` | Forcer le reset admin au redémarrage | `false` |
| `SESSION_HOURS` | Durée de session JWT (heures) | `8` |
| `LOGIN_MAX_ATTEMPTS` | Tentatives de login avant blocage | `5` |
| `LOGIN_WINDOW_SECONDS` | Fenêtre de rate limiting (secondes) | `300` |

### Intégrations (optionnelles)

| Variable | Description |
|---|---|
| `SUMUP_API_KEY` | Clé API SumUp (paiements) |
| `SUMUP_CLIENT_ID` | Client ID OAuth SumUp |
| `SUMUP_CLIENT_SECRET` | Secret OAuth SumUp |
| `SUMUP_WEBHOOK_SECRET` | Secret de vérification des webhooks SumUp (HMAC) |
| `GEMINI_API_KEY` | Clé API Google Gemini (IA) |
| `BREVO_API_KEY` | Clé API Brevo (emails transactionnels) |
| `BREVO_FROM_EMAIL` | Email expéditeur Brevo (`bonjour@kahlocafe.fr`) |
| `BREVO_FROM_NAME` | Nom expéditeur Brevo (`Kahlo Café`) |
| `BREVO_LIST_CLIENTS` | ID liste Brevo clients (`3`) |
| `BREVO_LIST_RELANCE` | ID liste Brevo relances (`7`) |
| `BREVO_TPL_ANNIVERSAIRE` | ID template anniversaire (`1`) |
| `BREVO_TPL_CONFIRMATION` | ID template confirmation (`2`) |
| `BREVO_TPL_PRETE` | ID template commande prête (`3`) |
| `GOOGLE_CLIENT_ID` | Client ID Google OAuth (Calendar) |
| `GOOGLE_CLIENT_SECRET` | Secret Google OAuth |
| `CALDAV_USER` | Utilisateur Radicale CalDAV (`kahlo`) |
| `CALDAV_PASSWORD` | Mot de passe Radicale CalDAV (`changeme`) |

### Réseau

| Variable | Description | Valeur par défaut |
|---|---|---|
| `CORS_ORIGINS` | Origines CORS autorisées (séparées par `,`) | `http://localhost:3000,https://erp.kahlocafe.fr` |
| `HTTP_PORT` | Port HTTP exposé | `80` |
| `HTTPS_PORT` | Port HTTPS exposé | `443` |

Variables minimales à adapter avant production:
- `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY`, `APP_DEFAULT_PASSWORD`, `CALDAV_PASSWORD`, `CORS_ORIGINS`
- `BIND_HOST` (laisser `127.0.0.1` derrière un reverse proxy externe)
- Secrets API non vides seulement si intégration activée

---

## Admin

### Création de l'admin initial

Au premier démarrage, si la table `utilisateurs` est vide :
- création auto de l'admin `APP_USERNAME`
- mot de passe `APP_DEFAULT_PASSWORD` (ou `APP_PASSWORD_HASH`)

### Reset du mot de passe admin

Si vous avez perdu l'accès admin :

```bash
# 1. Modifier .env
APP_DEFAULT_PASSWORD=nouveau_mot_de_passe
ADMIN_FORCE_RESET=true

# 2. Redémarrer le backend
docker compose restart backend

# 3. IMPORTANT : désactiver le reset après connexion
# Remettre dans .env :
ADMIN_FORCE_RESET=false
```

Alternativement, via la base de données :

```bash
docker compose exec db psql -U kahlo -d kahlo -c \
  "UPDATE utilisateurs SET password_hash = 'NOUVEAU_HASH' WHERE username = 'kahlo';"
```

Pour générer un hash bcrypt :
```bash
docker compose exec backend python -c \
  "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('votre_mot_de_passe'))"
```

---

## Migrations et seed

- Le backend applique `alembic upgrade head` au démarrage.
- En fallback, `Base.metadata.create_all()` est utilisé si Alembic échoue.
- Seed initial: fournisseurs + admin bootstrap.

### Créer une nouvelle migration

```bash
# Entrer dans le conteneur backend
docker compose exec backend bash

# Générer une migration à partir des changements de models.py
alembic revision --autogenerate -m "description_du_changement"

# Appliquer
alembic upgrade head

# Rollback d'une migration
alembic downgrade -1
```

Le fichier `backend/alembic/versions/e657bae136a6_initial_schema.py` contient le schéma complet.

---

## Tests

Les tests utilisent **pytest** avec une base SQLite en mémoire. Les services externes (Gemini, Brevo, SumUp, CalDAV, Redis) sont mockés automatiquement.

### Exécuter les tests

Backend:
```bash
# Depuis l'hôte
docker compose exec backend pytest -v

# Avec couverture
docker compose exec backend pytest --cov=. --cov-report=term-missing

# Un fichier spécifique
docker compose exec backend pytest tests/test_auth.py -v

# Sans Docker
cd backend
pytest -v
```

Frontend:
```bash
cd frontend
npm run build
```

### Suites de tests disponibles

| Fichier | Couverture |
|---|---|
| `test_auth.py` | Login, JWT, cookies HttpOnly, CSRF, logout, rate limiting |
| `test_stock.py` | CRUD lots, alertes, marges |
| `test_clients.py` | CRM, profils, fidélité |
| `test_commandes.py` | Commandes, lignes, statuts |
| `test_marches_calendrier_analytics.py` | Marchés, événements, KPIs |
| `test_investissements.py` | Investissements, amortissement, calculatrice de prix, scénarios |

---

## CI (GitHub Actions)

Une CI minimale et robuste est définie dans `.github/workflows/ci.yml` (push + pull request).

Elle vérifie automatiquement :
- installation backend + tests `pytest`,
- migrations Alembic sur PostgreSQL vierge,
- build frontend Vite,
- build de l'image Docker backend.

Voir la documentation détaillée et la reproduction locale : `docs/ci.md`.

---

## Déploiement production

### ZimaOS / CasaOS / NAS (auto-hébergé)

L'installation manuelle « une image Docker » de ZimaOS ne convient pas : Kahlo ERP est une stack de 5 conteneurs construite depuis les sources. Passez par le terminal (SSH) :

```bash
# 1. Récupérer les sources (dans le stockage persistant de ZimaOS)
cd /DATA/AppData
curl -L https://github.com/voirfilm-tv/Kahlo-ERP/archive/refs/heads/main.tar.gz | tar xz
mv Kahlo-ERP-main kahlo-erp && cd kahlo-erp

# 2. Configurer les secrets
cp .env.example .env
nano .env   # changez POSTGRES_PASSWORD, REDIS_PASSWORD, SECRET_KEY,
            # APP_DEFAULT_PASSWORD et CALDAV_PASSWORD

# 3. Lancer la stack (publie l'ERP sur le port 8087 de la machine)
docker compose -f docker-compose.yml -f docker-compose.selfhost.yml up -d --build
```

L'ERP est accessible sur `http://IP-du-NAS:8087` (port modifiable via `KAHLO_HTTP_PORT` dans le `.env`). Connexion initiale : `APP_USERNAME` / `APP_DEFAULT_PASSWORD` du `.env`.

Pour un accès HTTPS avec votre domaine, créez un proxy host dans Nginx Proxy Manager vers `IP-du-NAS:8087` et ajoutez le domaine dans `CORS_ORIGINS`. Mise à jour : re-télécharger les sources puis relancer la commande du point 3.

### Derrière un reverse proxy existant

Si vous avez déjà un reverse proxy (Nginx, Traefik, Caddy), vous pouvez retirer le service `nginx` du compose et exposer directement le backend et le frontend :

```yaml
# docker-compose.override.yml
services:
  nginx:
    profiles: ["disabled"]  # Désactiver le nginx intégré

  backend:
    ports:
      - "127.0.0.1:8000:8000"

  frontend:
    ports:
      - "127.0.0.1:3000:80"
```

Configuration du reverse proxy existant :

```nginx
# Exemple pour Nginx existant
server {
    listen 443 ssl;
    server_name erp.kahlocafe.fr;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # API Backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # CalDAV
    location /caldav/ {
        proxy_pass http://127.0.0.1:5232/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Script-Name /caldav;
        proxy_pass_header Authorization;
    }

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Avec le reverse proxy intégré (SSL)

1. Placer les certificats dans `nginx/ssl/` :
   ```bash
   cp cert.pem nginx/ssl/cert.pem
   cp key.pem nginx/ssl/key.pem
   ```

2. Dans `nginx/nginx.conf`, décommenter la redirection HTTP → HTTPS :
   ```nginx
   return 301 https://$host$request_uri;
   ```

3. Ajouter un bloc `server` HTTPS (port 443) avec les mêmes `location` que le bloc HTTP.

### Check-list production

```bash
# 1. Générer une SECRET_KEY forte
python3 -c "import secrets; print(secrets.token_hex(32))"

# 2. Générer un mot de passe PostgreSQL fort
openssl rand -base64 24

# 3. Mettre à jour .env
SECRET_KEY=<clé_générée>
POSTGRES_PASSWORD=<mot_de_passe_fort>
APP_DEFAULT_PASSWORD=<mot_de_passe_admin_fort>
CALDAV_PASSWORD=<mot_de_passe_caldav_fort>
CORS_ORIGINS=https://erp.kahlocafe.fr

# 4. Lancer en production
docker compose up -d --build
```

---

## Mise à jour logicielle (admin)

Une section **Paramètres > Mise à jour** permet de :
- vérifier la version installée vs la dernière release GitHub,
- lancer une mise à jour si l'environnement serveur le permet,
- sinon afficher un mode semi-automatique avec commandes sûres.

Documentation complète : `docs/software-update.md`.

---

## Sécurité

### Mesures en place

- **Authentification JWT via cookie HttpOnly** (protège contre XSS) + **CSRF double-submit cookie** sur toutes les routes `/api/*` (sauf `/api/health` et `/api/webhooks/sumup`)
- **Rate limiting** : 5 tentatives de login / 5 minutes par utilisateur, protection contre les noms d'utilisateur aléatoires (cap à 10 000 clés)
- **Webhooks SumUp** : vérification HMAC-SHA256 de la signature
- **Backend non-root** : le conteneur tourne avec l'utilisateur `appuser`
- **Nginx hardened** : `server_tokens off`, headers de sécurité (X-Frame-Options, CSP, HSTS, etc.)
- **Upload limité** : `client_max_body_size 10m`
- **Ports internes** : seul Nginx expose les ports 80/443. PostgreSQL, Redis, backend ne sont pas exposés sur l'hôte
- **Docs API désactivées en prod** : `/docs`, `/redoc`, `/openapi.json` masqués quand `SECRET_KEY` est configurée
- **Rate limiting Nginx** : zones séparées pour webhooks (10 req/s) et CalDAV (5 req/s)
- **Gestion d'erreurs globale** : les stack traces ne sont jamais exposées aux utilisateurs

### Points d'attention

- Changer **tous** les mots de passe par défaut avant la mise en production
- Activer HTTPS (certificats SSL dans `nginx/ssl/`)
- Configurer `CORS_ORIGINS` avec le domaine exact de production
- Sauvegarder régulièrement la base PostgreSQL
- Surveiller les logs : `docker compose logs -f backend`

---

## Exploitation

### Commandes utiles

```bash
# Démarrer en dev (avec logs)
./start.sh dev
# ou directement :
docker compose up --build

# Démarrer en prod (arrière-plan)
docker compose up -d --build

# Arrêter
docker compose down

# Voir les logs d'un service
docker compose logs -f backend
docker compose logs -f nginx
docker compose logs -f db

# Accéder à la base de données
docker compose exec db psql -U kahlo -d kahlo

# Shell dans le backend
docker compose exec backend bash

# Reconstruire un service spécifique
docker compose up -d --build backend

# Vérifier l'état des services
docker compose ps

# Reset complet (supprime toutes les données)
./start.sh reset
```

### Sauvegarde et restauration

```bash
# Sauvegarde
docker compose exec db pg_dump -U kahlo kahlo > backup_$(date +%Y%m%d).sql

# Restauration
cat backup.sql | docker compose exec -T db psql -U kahlo kahlo
```

### Rotation des secrets

1. Modifier les valeurs dans `.env`
2. Redéployer : `docker compose up -d --build`
3. Changement de `SECRET_KEY` invalide toutes les sessions actives

> Les dumps applicatifs backend sont écrits dans le volume persistant `backups_data` monté sur `/backups/kahlo`.

> `docker compose down -v` supprime **tous** les volumes nommés (`postgres_data`, `redis_data`, `uploads_data`, `factures_data`, `caldav_data`, `backups_data`).

---

## Dépannage

| Problème | Solution |
|---|---|
| Le backend ne démarre pas | Vérifier les logs : `docker compose logs backend`. La DB est-elle prête ? |
| Erreur 502 Bad Gateway | Le backend n'est pas encore prêt. Attendre 15-30s et réessayer |
| Page blanche sur le frontend | Reconstruire : `docker compose up -d --build frontend` |
| Erreurs CORS | Accéder via Nginx (http://localhost), pas directement au backend |
| Données perdues au restart | Ne pas utiliser `docker compose down -v` (supprime les volumes) |
| Login impossible | Vérifier les identifiants dans `.env`, utiliser `ADMIN_FORCE_RESET=true` |
| CalDAV non accessible | Vérifier que le service caldav est healthy : `docker compose ps` |

---

## Sync Calendrier

### Apple Calendar (CalDAV)

iPhone/Mac → Réglages → Calendriers → Ajouter un compte → Autre → CalDAV :
- **Serveur** : `https://erp.kahlocafe.fr/caldav/`
- **Identifiant** : `kahlo` (ou valeur de `CALDAV_USER`)
- **Mot de passe** : valeur de `CALDAV_PASSWORD` dans `.env`

### Google Calendar

Cliquer sur "Connecter Google Calendar" dans l'interface → OAuth automatique.
Nécessite `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` dans `.env`.

---

## Mode offline (terrain)

L'application fonctionne sans internet sur le stand de marché. Les opérations sont mises en queue Redis et synchronisées automatiquement à la reconnexion :

1. Décrémentation stock
2. Création commandes
3. Mise à jour CRM
4. Sync calendrier

Un indicateur de sync est visible en haut de l'interface.

---

## Architecture

```
Kahlo-ERP/
├── docker-compose.yml          # Stack complète (6 services)
├── .env.example                # Variables d'environnement (template)
├── start.sh                    # Script de démarrage dev/prod
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # Point d'entrée FastAPI + lifespan
│   ├── models.py               # Modèles SQLAlchemy (10 tables)
│   ├── database.py             # Connexion async PostgreSQL
│   ├── alembic.ini             # Configuration Alembic
│   ├── alembic/                # Migrations versionnées
│   ├── routers/                # Routes API (12 modules)
│   │   ├── auth.py             # JWT, login, rate limiting
│   │   ├── stock.py            # Lots, alertes, marges
│   │   ├── clients.py          # CRM, fidélité
│   │   ├── commandes.py        # Commandes, SumUp, factures
│   │   ├── fournisseurs.py     # Fournisseurs
│   │   ├── marches.py          # Marchés
│   │   ├── calendrier.py       # Événements, CalDAV, Google
│   │   ├── analytics.py        # KPIs, tendances
│   │   ├── webhooks.py         # Webhooks SumUp (HMAC)
│   │   ├── ia.py               # Endpoints Gemini
│   │   ├── parametres.py       # Configuration .env
│   │   └── utilisateurs.py     # Gestion utilisateurs/domaines
│   ├── services/               # Logique métier
│   │   ├── ia.py               # Google Gemini API
│   │   ├── calendrier.py       # CalDAV + Google Calendar
│   │   ├── brevo.py            # Emails transactionnels
│   │   ├── sumup.py            # API paiement SumUp
│   │   ├── scheduler.py        # Tâches planifiées (APScheduler)
│   │   ├── factures.py         # Génération PDF (WeasyPrint)
│   │   ├── stock.py            # Logique stock
│   │   └── offline_sync.py     # Mode terrain (Redis queue)
│   ├── sql/
│   │   └── init.sql            # Placeholder (Alembic gère le schéma)
│   └── tests/                  # Tests pytest
├── frontend/
│   ├── Dockerfile              # Build multi-stage (Node → Nginx)
│   ├── src/
│   │   ├── pages/              # Dashboard, Stock, CRM, etc.
│   │   ├── components/         # Layout
│   │   ├── services/           # Appels API (api.js)
│   │   ├── hooks/              # useOfflineSync
│   │   └── stores/             # État global (Zustand)
│   └── vite.config.js
├── nginx/
│   ├── nginx.conf              # Reverse proxy + headers sécurité
│   ├── radicale.conf           # Configuration Radicale
│   ├── radicale-init.sh        # Init script CalDAV
│   └── ssl/                    # Certificats SSL (production)
└── caldav/
    └── Dockerfile              # Fallback build local Radicale
```

---

*Kahlo Café · Lyon · 2026*
