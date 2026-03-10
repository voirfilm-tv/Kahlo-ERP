# Kahlo Café — ERP

Système de gestion interne sur-mesure pour Kahlo Café, marque de café artisanal lyonnaise.

---

## Stack technique

| Service | Techno | RAM |
|---|---|---|
| Frontend | React + Vite | ~20MB |
| Backend | FastAPI (Python) | ~120MB |
| Base de données | PostgreSQL 16 | ~80MB |
| Cache + offline | Redis 7 | ~30MB |
| Calendrier | Radicale (CalDAV) | ~30MB |
| Proxy | Nginx | ~10MB |
| **Total** | | **~520MB** |

---

## Modules

- **Dashboard** — Vue d'ensemble temps réel
- **Stock** — Lots par origine, alertes, marges
- **Fournisseurs** — Contacts, scores, commandes
- **CRM** — Clients, profils Kahlo, fidélité
- **Commandes** — Suivi, statuts, notifications
- **Calendrier** — Marchés, remises, fournisseurs
- **Analytics** — CA, origines, clients, saisonnalité

---

## Intégrations

| Service | Usage |
|---|---|
| **SumUp** | Paiements + webhooks temps réel |
| **Gemini API** | IA gratuite (analyses, suggestions, fiches produit) |
| **Brevo** | Emails (anniversaires, relances, notifications) |
| **Google Calendar** | Sync bidirectionnelle |
| **Apple Calendar** | Sync bidirectionnelle via CalDAV |

---

## Installation

### Prérequis
- Docker + Docker Compose
- 2GB RAM minimum (4GB recommandé)
- Linux / macOS / Windows WSL2

### Démarrage rapide

```bash
# 1. Cloner le projet
git clone https://github.com/kahlocafe/erp.git
cd erp

# 2. Configurer les variables
cp .env.example .env
nano .env   # Remplir les clés API

# 3. Démarrer
./start.sh dev
```

L'app est disponible sur **http://localhost**

### Clés API nécessaires

| Service | Où trouver | Gratuit ? |
|---|---|---|
| SumUp | developer.sumup.com | Oui (frais sur transactions) |
| Gemini | aistudio.google.com/app/apikey | Oui |
| Brevo | app.brevo.com/settings/keys | Oui (300 emails/jour) |
| Google Calendar | console.cloud.google.com | Oui |

---

## Sync Calendrier

### Apple Calendar (CalDAV)
Dans iPhone/Mac → Calendriers → Ajouter un compte → Autre → CalDAV :
- Serveur : `http://VOTRE_IP/caldav/`
- Identifiant : `kahlo`
- Mot de passe : (défini dans .env)

### Google Calendar
Cliquer sur "Connecter Google Calendar" dans l'app → OAuth automatique.

---

## Mode offline (terrain)

L'app fonctionne sans internet sur le stand. Les ventes sont mises en queue Redis et synchronisées automatiquement à la reconnexion dans l'ordre :
1. Décrémentation stock
2. Création commandes
3. Mise à jour CRM
4. Sync calendrier

Indicateur de sync visible en haut de l'interface.

---

## Commandes utiles

```bash
# Démarrer en dev (avec logs)
./start.sh dev

# Démarrer en prod (arrière-plan)
./start.sh prod

# Arrêter
./start.sh stop

# Voir les logs
docker compose logs -f backend

# Accéder à la base de données
docker exec -it kahlo_db psql -U kahlo -d kahlo

# Reset complet (⚠ supprime les données)
./start.sh reset
```

---

## Structure du projet

```
kahlo-erp/
├── docker-compose.yml
├── .env.example
├── start.sh
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py              # Point d'entrée FastAPI
│   ├── models.py            # Modèles SQLAlchemy
│   ├── database.py          # Connexion DB
│   ├── routers/             # Routes API par module
│   │   ├── auth.py
│   │   ├── stock.py
│   │   ├── clients.py
│   │   ├── commandes.py
│   │   ├── marches.py
│   │   ├── calendrier.py
│   │   ├── analytics.py
│   │   ├── webhooks.py      # SumUp webhooks
│   │   └── ia.py            # Endpoints Gemini
│   ├── services/
│   │   ├── ia.py            # Gemini API
│   │   ├── calendrier.py    # CalDAV + Google Calendar
│   │   ├── offline_sync.py  # Mode terrain
│   │   ├── scheduler.py     # Tâches automatiques
│   │   ├── brevo.py         # Emails
│   │   └── stock.py         # Logique stock
│   └── sql/
│       └── init.sql         # Données initiales
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── pages/           # Modules (Dashboard, Stock, CRM...)
│   │   ├── components/      # Composants réutilisables
│   │   ├── services/        # Appels API
│   │   ├── hooks/           # useOfflineSync, useSumUp...
│   │   └── stores/          # État global (Zustand)
│   └── vite.config.js
└── nginx/
    └── nginx.conf
```

---

*Kahlo Café · Lyon · 2026*
