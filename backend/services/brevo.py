"""KAHLO CAFÉ — Service Brevo (emails transactionnels + marketing)"""

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import os
import logging
import asyncio
from functools import partial

logger = logging.getLogger(__name__)

# Configuration lue à chaque appel : les valeurs saisies dans la page
# Paramètres s'appliquent sans redémarrage du backend.

def _configuration():
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = os.getenv("BREVO_API_KEY", "")
    return configuration


def _get_contacts_api():
    return sib_api_v3_sdk.ContactsApi(sib_api_v3_sdk.ApiClient(_configuration()))

def _get_transac_api():
    return sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(_configuration()))


def _int_env(key: str, default: str) -> int:
    try:
        return int(os.getenv(key, default) or default)
    except ValueError:
        return int(default)

def _liste_clients():     return _int_env("BREVO_LIST_CLIENTS", "3")
def _liste_relance():     return _int_env("BREVO_LIST_RELANCE", "7")
def _tpl_anniversaire():  return _int_env("BREVO_TPL_ANNIVERSAIRE", "1")
def _tpl_confirmation():  return _int_env("BREVO_TPL_CONFIRMATION", "2")
def _tpl_prete():         return _int_env("BREVO_TPL_PRETE", "3")
def _expediteur():
    return {"email": os.getenv("BREVO_FROM_EMAIL", "bonjour@kahlocafe.fr"),
            "name": os.getenv("BREVO_FROM_NAME", "Kahlo Café")}


async def _run_sync(func, *args, **kwargs):
    """Exécute une fonction synchrone dans un thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


async def sync_client_brevo(client) -> str:
    """Crée ou met à jour un contact dans Brevo"""
    if not client.email:
        logger.warning("sync_client_brevo: pas d'email, abandon")
        return ""
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
            list_ids=[_liste_clients()],
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
            template_id=_tpl_anniversaire(),
            params={
                "PRENOM": client.prenom,
                "PROFIL": client.profil or "cliente fidèle",
            },
            sender=_expediteur()
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
            template_id=_tpl_confirmation(),
            params={
                "PRENOM": commande.client.prenom,
                "NUMERO": commande.numero,
                "MONTANT": f"{commande.montant_total:.2f}",
                "MARCHE": "votre prochain marché",
            },
            sender=_expediteur()
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
            template_id=_tpl_prete(),
            params={
                "PRENOM": commande.client.prenom,
                "MARCHE": commande.marche.nom if commande.marche else "notre prochain marché",
                "NUMERO": commande.numero,
            },
            sender=_expediteur()
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
            list_id=_liste_relance(),
            contacts_emails={"emails": [client.email]}
        )
        logger.info(f"Workflow relance déclenché: {client.email}")
    except ApiException as e:
        logger.error(f"Erreur workflow relance: {e}")
