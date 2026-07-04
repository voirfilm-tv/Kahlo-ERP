"""
KAHLO CAFÉ — Tâches planifiées (APScheduler)
Toutes les automations qui tournent en arrière-plan
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Paris")


def start_scheduler():
    """Démarre toutes les tâches planifiées"""
    if scheduler.running:
        logger.warning("Scheduler déjà en cours, skip")
        return

    # Tous les matins à 8h
    scheduler.add_job(
        check_stocks_critiques,
        CronTrigger(hour=8, minute=0),
        id="check_stocks",
        name="Vérification stocks critiques",
        replace_existing=True,
    )

    # Tous les matins à 8h30 — anniversaires
    scheduler.add_job(
        check_anniversaires,
        CronTrigger(hour=8, minute=30),
        id="check_anniversaires",
        name="Anniversaires clients J+14",
        replace_existing=True,
    )

    # Chaque dimanche à 9h — clients inactifs
    scheduler.add_job(
        check_clients_inactifs,
        CronTrigger(day_of_week="sun", hour=9),
        id="check_inactifs",
        name="Relance clients inactifs",
        replace_existing=True,
    )

    # Chaque lundi à 7h — prévision de la semaine
    scheduler.add_job(
        prevision_semaine,
        CronTrigger(day_of_week="mon", hour=7),
        id="prevision_semaine",
        name="Prévision hebdo",
        replace_existing=True,
    )

    # Sync des ventes SumUp toutes les 15 minutes (stock temps réel)
    scheduler.add_job(
        sync_ventes_sumup,
        "interval",
        minutes=15,
        id="sync_sumup",
        name="Import ventes SumUp",
        replace_existing=True,
    )

    # Sync CalDAV : tick chaque seconde, auto-throttlé selon la fréquence
    # configurée (CALDAV_INTERVAL_SECONDS, modifiable à chaud, jusqu'à 1 s).
    # Coût quasi nul : une empreinte ctag est vérifiée avant toute vraie sync.
    scheduler.add_job(
        sync_caldav_tick,
        "interval",
        seconds=1,
        id="sync_caldav",
        name="Sync CalDAV bidirectionnel",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    logger.info("✅ Scheduler démarré — tâches planifiées actives")


# ============================================================
#  TÂCHES
# ============================================================

async def check_stocks_critiques():
    """
    Vérifie les stocks en dessous du seuil
    → Crée une alerte + suggestion de commande fournisseur
    → Ajoute un rappel dans le calendrier si marché < 7 jours
    """
    from database import AsyncSessionLocal
    from models import Lot
    from sqlalchemy import select

    logger.info("Vérification des stocks critiques...")

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Lot).where(Lot.actif == True)
            )
            lots = result.scalars().all()

            for lot in lots:
                if lot.est_critique:
                    logger.warning(f"⚠ Stock critique: {lot.origine} ({lot.stock_kg} kg)")
    except Exception as e:
        logger.error("Erreur check_stocks_critiques (DB indisponible ?): %s", e)


async def check_anniversaires():
    """
    Vérifie les anniversaires clients dans les 14 prochains jours
    → Déclenche un workflow Brevo pour envoyer un email personnalisé
    """
    from database import AsyncSessionLocal
    from models import Client
    from services.brevo import envoyer_email_anniversaire
    from sqlalchemy import select
    from datetime import date, timedelta

    logger.info("Vérification des anniversaires...")

    today = date.today()
    dans_14j = today + timedelta(days=14)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Client).where(Client.anniversaire != None))
        clients = result.scalars().all()

        for client in clients:
            if not client.anniversaire:
                continue
            try:
                anniv_dt = client.anniversaire if isinstance(client.anniversaire, datetime) else datetime.combine(client.anniversaire, datetime.min.time())
                anniv = anniv_dt.replace(year=today.year).date()
            except ValueError:
                # 29 février sur année non-bissextile
                anniv = date(today.year, 3, 1)
            if anniv < today:
                try:
                    anniv = anniv_dt.replace(year=today.year + 1).date()
                except ValueError:
                    anniv = date(today.year + 1, 3, 1)

            jours = (anniv - today).days
            if 0 <= jours <= 7:  # Email jusqu'à 1 semaine avant
                logger.info(f"🎂 Anniversaire dans 7j: {client.prenom} {client.nom}")
                await envoyer_email_anniversaire(client)


async def check_clients_inactifs():
    """
    Clients sans achat depuis 45 jours → séquence relance Brevo
    """
    from database import AsyncSessionLocal
    from models import Client, Commande, StatutCommande
    from services.brevo import declencher_workflow_relance
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload
    from datetime import datetime, timedelta, timezone

    logger.info("Vérification des clients inactifs...")
    seuil = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=45)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Client).options(selectinload(Client.commandes))
        )
        clients = result.scalars().all()

        for client in clients:
            if client.commandes:
                dates = [c.date_commande for c in client.commandes
                         if c.statut != StatutCommande.annulee and c.date_commande]
                if not dates:
                    continue
                dernier = max(dates)
                if dernier < seuil:
                    logger.info(f"Client inactif: {client.prenom} {client.nom}")
                    await declencher_workflow_relance(client)


async def prevision_semaine():
    """
    Chaque lundi : génère une prévision Gemini pour la semaine
    Basée sur les marchés à venir et le stock actuel
    """
    from database import AsyncSessionLocal
    from models import Marche, Lot, StatutMarche
    from services.ia import analyser_dashboard
    from sqlalchemy import select
    from datetime import datetime, timedelta

    logger.info("Génération de la prévision de la semaine...")

    async with AsyncSessionLocal() as db:
        # Marchés de la semaine
        fin_semaine = datetime.now() + timedelta(days=7)
        marches = await db.execute(
            select(Marche).where(
                Marche.date <= fin_semaine,
                Marche.date >= datetime.now(),
                Marche.statut == StatutMarche.confirme
            )
        )
        # TODO: générer rapport IA + envoyer par email


async def sync_ventes_sumup():
    """Importe les nouvelles ventes SumUp (terminal + en ligne) et met à
    jour le stock. Ne fait rien si la clé API n'est pas configurée —
    testée à chaque exécution pour suivre la config à chaud."""
    import os
    if not os.getenv("SUMUP_API_KEY"):
        return

    from database import AsyncSessionLocal
    from services.ventes_sumup import synchroniser

    try:
        async with AsyncSessionLocal() as db:
            resultat = await synchroniser(db)
            if resultat.get("importees"):
                logger.info("SumUp: %s vente(s) importée(s), %s stock(s) mis à jour",
                            resultat["importees"], resultat["stock_maj"])
    except Exception as e:
        logger.error("Erreur sync_ventes_sumup (API indisponible ?): %s", e)


def _caldav_interval_seconds() -> int:
    """Fréquence de sync CalDAV, lue à chaud (Paramètres → Calendrier).
    CALDAV_INTERVAL_SECONDS prime ; sinon l'ancien CALDAV_INTERVAL (minutes)."""
    import os
    try:
        brut = os.getenv("CALDAV_INTERVAL_SECONDS")
        if brut:
            return max(1, int(brut))
        legacy = os.getenv("CALDAV_INTERVAL")
        if legacy:
            return max(1, int(legacy) * 60)
    except ValueError:
        pass
    return 300


import time as _time
_derniere_sync_caldav = 0.0


async def sync_caldav_tick():
    """Tick 1 s : ne synchronise que si la fréquence configurée est écoulée
    ET que les calendriers ont réellement changé (empreinte ctag)."""
    global _derniere_sync_caldav
    if _time.monotonic() - _derniere_sync_caldav < _caldav_interval_seconds():
        return
    _derniere_sync_caldav = _time.monotonic()
    await sync_caldav()


async def sync_caldav():
    """Sync entrante CalDAV (appareils → ERP), déclenchée par le tick."""
    from database import AsyncSessionLocal
    from services.calendrier import sync_caldav_vers_db, caldav_a_change

    try:
        # Court-circuit : rien n'a bougé côté Radicale → pas de vraie sync
        change = await caldav_a_change()
        if change is False:
            return
        if change is None:
            logger.debug("CalDAV injoignable — sync sautée")
            return

        async with AsyncSessionLocal() as db:
            nouveaux = await sync_caldav_vers_db(db)
            if nouveaux:
                logger.info(f"CalDAV sync: {len(nouveaux)} nouveaux événements importés")
    except Exception as e:
        logger.error("Erreur sync_caldav (service indisponible ?): %s", e)
