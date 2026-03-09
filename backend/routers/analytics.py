"""KAHLO CAFÉ — Router Analytics"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from database import get_db
from models import Commande, LigneCommande, Lot, Client, Marche, StatutCommande

router = APIRouter()


# ────────────────────────────────────────────────
#  DASHBOARD (KPIs temps réel)
# ────────────────────────────────────────────────

@router.get("/dashboard")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    now = datetime.now()
    debut_mois    = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    debut_semaine = now - timedelta(days=now.weekday())

    r = await db.execute(
        select(func.sum(Commande.montant_total)).where(
            Commande.statut != StatutCommande.annulee,
            Commande.date_commande >= debut_mois,
        )
    )
    ca_mois = r.scalar() or 0

    r = await db.execute(
        select(func.sum(Commande.montant_total)).where(
            Commande.statut != StatutCommande.annulee,
            Commande.date_commande >= debut_semaine,
        )
    )
    ca_semaine = r.scalar() or 0

    r = await db.execute(select(func.count()).where(Commande.statut == StatutCommande.en_attente))
    commandes_attente = r.scalar()

    r = await db.execute(select(Lot).where(Lot.actif == True))
    lots = r.scalars().all()
    stocks_critiques = sum(1 for l in lots if l.est_critique)

    import os
    objectif = float(os.getenv("OBJECTIF_CA_MENSUEL", "3500"))

    return {
        "ca_mois":           round(ca_mois, 2),
        "ca_semaine":        round(ca_semaine, 2),
        "commandes_attente": commandes_attente,
        "stocks_critiques":  stocks_critiques,
        "nb_lots_actifs":    len(lots),
        "objectif_ca":       objectif,
    }


# ────────────────────────────────────────────────
#  CA MENSUEL (graphique)
# ────────────────────────────────────────────────

@router.get("/ca-mensuel")
async def get_ca_mensuel(mois: int = 7, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(
            extract("year",  Commande.date_commande).label("annee"),
            extract("month", Commande.date_commande).label("mois"),
            func.sum(Commande.montant_total).label("ca"),
            func.count().label("nb_commandes"),
        )
        .where(
            Commande.statut != StatutCommande.annulee,
            Commande.date_commande >= datetime.now() - timedelta(days=mois * 30),
        )
        .group_by("annee", "mois")
        .order_by("annee", "mois")
    )
    return [
        {"annee": int(row.annee), "mois": int(row.mois), "ca": round(row.ca or 0, 2), "nb": row.nb_commandes}
        for row in r.all()
    ]


# ────────────────────────────────────────────────
#  GÉNÉRAL (page Analytics onglet Général)
# ────────────────────────────────────────────────

@router.get("/general")
async def get_analytics_general(mois: int = 12, db: AsyncSession = Depends(get_db)):
    depuis = datetime.now() - timedelta(days=mois * 30)

    # CA total + nb commandes
    r = await db.execute(
        select(
            func.sum(Commande.montant_total).label("ca"),
            func.count().label("nb"),
        ).where(
            Commande.statut != StatutCommande.annulee,
            Commande.date_commande >= depuis,
        )
    )
    row = r.one()
    ca_total = round(row.ca or 0, 2)
    nb_commandes = row.nb or 0
    panier_moyen = round(ca_total / nb_commandes, 2) if nb_commandes else 0

    # Clients actifs (au moins une commande sur la période)
    r = await db.execute(
        select(func.count(Commande.client_id.distinct())).where(
            Commande.statut != StatutCommande.annulee,
            Commande.date_commande >= depuis,
        )
    )
    clients_actifs = r.scalar() or 0

    # CA mensuel pour le graphique
    r = await db.execute(
        select(
            extract("year",  Commande.date_commande).label("annee"),
            extract("month", Commande.date_commande).label("mois"),
            func.sum(Commande.montant_total).label("ca"),
        )
        .where(
            Commande.statut != StatutCommande.annulee,
            Commande.date_commande >= depuis,
        )
        .group_by("annee", "mois")
        .order_by("annee", "mois")
    )
    ca_mensuel = [
        {"annee": int(row.annee), "mois": int(row.mois), "ca": round(row.ca or 0, 2)}
        for row in r.all()
    ]

    # Top origines (CA par origine via lignes de commande)
    r = await db.execute(
        select(
            Lot.origine,
            func.sum(LigneCommande.prix_unitaire).label("ca"),
        )
        .join(LigneCommande, LigneCommande.lot_id == Lot.id)
        .join(Commande, Commande.id == LigneCommande.commande_id)
        .where(
            Commande.statut != StatutCommande.annulee,
            Commande.date_commande >= depuis,
        )
        .group_by(Lot.origine)
        .order_by(func.sum(LigneCommande.prix_unitaire).desc())
        .limit(6)
    )
    top_origines = [{"origine": row.origine, "ca": round(row.ca or 0, 2)} for row in r.all()]

    return {
        "ca_total":       ca_total,
        "nb_commandes":   nb_commandes,
        "panier_moyen":   panier_moyen,
        "clients_actifs": clients_actifs,
        "ca_mensuel":     ca_mensuel,
        "top_origines":   top_origines,
    }


# ────────────────────────────────────────────────
#  MARCHÉS
# ────────────────────────────────────────────────

@router.get("/marches")
async def get_analytics_marches(db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(Marche)
        .where(Marche.ca_realise != None)
        .order_by(Marche.date.desc())
    )
    marches = r.scalars().all()

    return {
        "marches": [
            {
                "id":              m.id,
                "nom":             m.nom,
                "lieu":            m.lieu or "",
                "date":            m.date.isoformat() if m.date else None,
                "ca":              m.ca_realise or 0,
                "kg_vendus":       round((m.stock_emmene_kg or 0) - (m.stock_ramene_kg or 0), 2),
                "nb_commandes":    m.nb_clients or 0,
                "taux_ecoulement": m.taux_ecoulement or 0,
                "marge_nette":     m.marge_nette,
            }
            for m in marches
        ]
    }


# ────────────────────────────────────────────────
#  ORIGINES
# ────────────────────────────────────────────────

@router.get("/origines")
async def get_analytics_origines(db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(
            Lot.origine,
            func.sum(LigneCommande.prix_unitaire).label("ca"),
            func.sum(LigneCommande.poids_g).label("poids_total_g"),
            func.count(LigneCommande.id).label("nb_ventes"),
            func.avg(Lot.marge_pct).label("marge_pct"),
        )
        .join(LigneCommande, LigneCommande.lot_id == Lot.id)
        .join(Commande, Commande.id == LigneCommande.commande_id)
        .where(Commande.statut != StatutCommande.annulee)
        .group_by(Lot.origine)
        .order_by(func.sum(LigneCommande.prix_unitaire).desc())
    )
    rows = r.all()

    return {
        "origines": [
            {
                "origine":   row.origine,
                "ca":        round(row.ca or 0, 2),
                "kg_vendus": round((row.poids_total_g or 0) / 1000, 2),
                "nb_ventes": row.nb_ventes,
                "marge_pct": round(row.marge_pct or 0),
            }
            for row in rows
        ]
    }


# ────────────────────────────────────────────────
#  CLIENTS
# ────────────────────────────────────────────────

@router.get("/clients")
async def get_analytics_clients(db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Client).options(selectinload(Client.commandes)))
    clients = r.scalars().all()

    total = len(clients)
    now = datetime.now()
    debut_mois = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    nouveaux_mois = sum(
        1 for c in clients
        if c.created_at and c.created_at >= debut_mois
    )
    recurrents = sum(
        1 for c in clients
        if len([cmd for cmd in c.commandes if cmd.statut == StatutCommande.remise]) > 1
    )
    actifs_30j = sum(
        1 for c in clients
        if any(
            cmd.date_commande and cmd.date_commande >= now - timedelta(days=30)
            for cmd in c.commandes
        )
    )

    # Top clients par CA
    clients_ca = []
    for c in clients:
        ca = sum(
            cmd.montant_total for cmd in c.commandes
            if cmd.statut != StatutCommande.annulee
        )
        if ca > 0:
            clients_ca.append({"id": c.id, "prenom": c.prenom, "nom": c.nom, "total_achats": round(ca, 2), "nb_achats": len([cmd for cmd in c.commandes if cmd.statut == StatutCommande.remise])})

    clients_ca.sort(key=lambda x: x["total_achats"], reverse=True)

    return {
        "total":           total,
        "nouveaux_mois":   nouveaux_mois,
        "recurrents":      recurrents,
        "taux_retention":  round(actifs_30j / total * 100) if total else 0,
        "top_clients":     clients_ca[:10],
    }
