"""KAHLO CAFÉ — Service Brevo (emails transactionnels + marketing)"""

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import os
import logging
import asyncio
from functools import partial

logger = logging.getLogger(__name__)

configuration = sib_api_v3_sdk.Configuration()
configuration.api_key["api-key"] = os.getenv("BREVO_API_KEY", "")


def _get_contacts_api():
    return sib_api_v3_sdk.ContactsApi(sib_api_v3_sdk.ApiClient(configuration))

def _get_transac_api():
    return sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))


_BREVO_LIST_CLIENTS = int(os.getenv("BREVO_LIST_CLIENTS", "3"))
_BREVO_LIST_RELANCE = int(os.getenv("BREVO_LIST_RELANCE", "7"))
_BREVO_TPL_ANNIVERSAIRE = int(os.getenv("BREVO_TPL_ANNIVERSAIRE", "1"))
_BREVO_TPL_CONFIRMATION = int(os.getenv("BREVO_TPL_CONFIRMATION", "2"))
_BREVO_TPL_PRETE = int(os.getenv("BREVO_TPL_PRETE", "3"))
_BREVO_FROM_EMAIL = os.getenv("BREVO_FROM_EMAIL", "bonjour@kahlocafe.fr")
_BREVO_FROM_NAME = os.getenv("BREVO_FROM_NAME", "Kahlo Café")


async def _run_sync(func, *args, **kwargs):
    """Exécute une fonction synchrone dans un thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


async def sync_client_brevo(client) -> str:
    """Crée ou met à jour un contact dans Brevo"""
    api = _get_contacts_api()
    try:
        contact = sib_api_v3_sdk.CreateContact(
            email=client.email,
            attributes={
                "PRENOM": client.prenom,
                "NOM": client.nom,
                "TELEPHONE": client.telephone or "",
                "VILLE": client.ville or "",
                "PROFIL_KAHLO": client.profil or "",
                "ANNIVERSAIRE": str(client.anniversaire.date()) if client.anniversaire else "",
                "TAMPONS": client.tampons,
                "VIP": str(client.vip),
            },
            list_ids=[_BREVO_LIST_CLIENTS],
            update_enabled=True
        )
        result = await _run_sync(api.create_contact, contact)
        logger.info(f"Contact Brevo sync: {client.email}")
        return str(result.id) if hasattr(result, "id") else ""
    except ApiException as e:
        logger.error(f"Erreur Brevo sync: {e}")
        return ""


async def envoyer_email_anniversaire(client):
    """Envoie un email d'anniversaire personnalisé"""
    api = _get_transac_api()
    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": client.email, "name": f"{client.prenom} {client.nom}"}],
            template_id=_BREVO_TPL_ANNIVERSAIRE,
            params={
                "PRENOM": client.prenom,
                "PROFIL": client.profil or "cliente fidèle",
            },
            sender={"email": _BREVO_FROM_EMAIL, "name": _BREVO_FROM_NAME}
        )
        await _run_sync(api.send_transac_email, email)
        logger.info(f"Email anniversaire envoyé à {client.email}")
    except ApiException as e:
        logger.error(f"Erreur envoi anniversaire: {e}")


async def notifier_client_paiement_recu(commande):
    """Email de confirmation quand le paiement sumup arrive"""
    if not commande.client or not commande.client.email:
        return
    api = _get_transac_api()
    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": commande.client.email, "name": f"{commande.client.prenom}"}],
            template_id=_BREVO_TPL_CONFIRMATION,
            params={
                "PRENOM": commande.client.prenom,
                "NUMERO": commande.numero,
                "MONTANT": commande.montant_total,
                "MARCHE": "votre prochain marché",
            },
            sender={"email": _BREVO_FROM_EMAIL, "name": _BREVO_FROM_NAME}
        )
        await _run_sync(api.send_transac_email, email)
        logger.info(f"Confirmation commande envoyée: {commande.numero}")
    except ApiException as e:
        logger.error(f"Erreur notification paiement: {e}")


async def notifier_commande_prete(commande):
    """Notifie le client que sa commande est prête pour la remise"""
    if not commande.client or not commande.client.email:
        return
    api = _get_transac_api()
    try:
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": commande.client.email}],
            template_id=_BREVO_TPL_PRETE,
            params={
                "PRENOM": commande.client.prenom,
                "MARCHE": commande.marche.nom if commande.marche else "notre prochain marché",
                "NUMERO": commande.numero,
            },
            sender={"email": _BREVO_FROM_EMAIL, "name": _BREVO_FROM_NAME}
        )
        await _run_sync(api.send_transac_email, email)
    except ApiException as e:
        logger.error(f"Erreur notification prête: {e}")


async def declencher_workflow_relance(client):
    """Lance le workflow de relance client inactif dans Brevo"""
    api = _get_contacts_api()
    try:
        await _run_sync(
            api.add_contact_to_list,
            list_id=_BREVO_LIST_RELANCE,
            contacts_emails={"emails": [client.email]}
        )
        logger.info(f"Workflow relance déclenché: {client.email}")
    except ApiException as e:
        logger.error(f"Erreur workflow relance: {e}")
