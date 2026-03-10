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

    # Tous les matins à 8h
    scheduler.add_job(
        check_stocks_critiques,
        CronTrigger(hour=8, minute=0),
        id="check_stocks",
        name="Vérification stocks critiques"
    )

    # Tous les matins à 8h30 — anniversaires
    scheduler.add_job(
        check_anniversaires,
        CronTrigger(hour=8, minute=30),
        id="check_anniversaires",
        name="Anniversaires clients J+14"
    )

    # Chaque dimanche à 9h — clients inactifs
    scheduler.add_job(
        check_clients_inactifs,
        CronTrigger(day_of_week="sun", hour=9),
        id="check_inactifs",
        name="Relance clients inactifs"
    )

    # Chaque lundi à 7h — prévision de la semaine
    scheduler.add_job(
        prevision_semaine,
        CronTrigger(day_of_week="mon", hour=7),
        id="prevision_semaine",
        name="Prévision hebdo"
    )

    # Sync CalDAV toutes les 30 minutes
    scheduler.add_job(
        sync_caldav,
        "interval",
        minutes=30,
        id="sync_caldav",
        name="Sync CalDAV bidirectionnel"
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

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Lot).where(Lot.actif == True)
        )
        lots = result.scalars().all()

        for lot in lots:
            if lot.est_critique:
                logger.warning(f"⚠ Stock critique: {lot.origine} ({lot.stock_kg} kg)")
                # TODO: créer événement rappel dans calendrier
                # TODO: notifier via Brevo si marché dans < 7 jours


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
            anniv = client.anniversaire.replace(year=today.year).date()
            if anniv < today:
                anniv = anniv.replace(year=today.year + 1)

            jours = (anniv - today).days
            if jours == 7:  # Email 1 semaine avant
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
    from datetime import datetime, timedelta

    logger.info("Vérification des clients inactifs...")
    seuil = datetime.now() - timedelta(days=45)

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


async def sync_caldav():
    """Sync bidirectionnelle CalDAV toutes les 30 minutes"""
    from database import AsyncSessionLocal
    from services.calendrier import sync_caldav_vers_db

    async with AsyncSessionLocal() as db:
        nouveaux = await sync_caldav_vers_db(db)
        if nouveaux:
            logger.info(f"CalDAV sync: {len(nouveaux)} nouveaux événements importés")
