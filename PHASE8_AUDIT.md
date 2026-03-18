# Phase 8 — Audit technique (avant corrections)

## 1) Parasites / hygiène repo
- `.venv/` présent localement et non ignoré dans `.gitignore`.
- Pas d'autres artefacts parasites versionnés détectés (`.pyc`, `.DS_Store`, logs temporaires).

## 2) Cohérence de démarrage
- README privilégiait `./start.sh dev` au lieu de la commande cible `docker compose up --build`.
- Documentation hétérogène entre README et INSTALLATION.

## 3) Docker / reproductibilité
- Healthcheck Redis incorrect: `redis-cli ping` sans auth alors que `--requirepass` est activé.
  Impact: service `redis` potentiellement `unhealthy`, bloquant le backend via `depends_on`.

## 4) Variables d'environnement
- `.env.example` incomplet vis-à-vis des variables réellement lues côté backend/compose.
  Exemples manquants: `REDIS_PASSWORD`, `SUMUP_MERCHANT_EMAIL`, `OBJECTIF_CA_MENSUEL`,
  `GEMINI_MODEL`, `BACKUP_*`, `BOUTIQUE_*`, `FACTURES_DIR`, etc.
- Certaines variables utilisées par l'écran paramètres non documentées.

## 5) Sécurité / exposition
- Endpoint webhook SumUp correctement protégé par signature HMAC + secret.
- Endpoints métier majoritairement protégés par JWT.
- Risque opérationnel: secrets de dev trop faibles si `.env.example` utilisé tel quel en production.

## 6) Migrations / seed
- Migration initiale présente (`alembic/versions/e657...`).
- Seed géré au startup backend (fournisseurs + admin).
- Pas d'incohérence critique détectée entre migration initiale et modèles sur l'audit rapide.

## 7) Validation from scratch
- Validation Docker complète non exécutable dans l'environnement courant (commande `docker` indisponible).
