"""
KAHLO CAFÉ — Génération de factures PDF
WeasyPrint : HTML → PDF avec style Kahlo
"""

import os
import asyncio
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

FACTURES_DIR = Path(os.getenv("FACTURES_DIR", "/app/factures"))
FACTURES_DIR.mkdir(parents=True, exist_ok=True)

MARQUE = {
    "nom":     os.getenv("BOUTIQUE_NOM", "Kahlo Café"),
    "email":   os.getenv("BOUTIQUE_EMAIL", "bonjour@kahlocafe.fr"),
    "tel":     os.getenv("BOUTIQUE_TEL", ""),
    "ville":   os.getenv("BOUTIQUE_VILLE", "Lyon, France"),
    "siret":   os.getenv("BOUTIQUE_SIRET", ""),
}

MOUTURES_LABELS = {
    "Grains entiers": "Grains entiers",
    "Filtre": "Filtre",
    "Expresso": "Expresso",
    "Cafetière italienne": "Cafetière italienne",
    "Chemex": "Chemex",
}


def _html_facture(commande, client, lignes_enrichies: list) -> str:
    date_fmt = commande.date_commande.strftime("%d/%m/%Y") if commande.date_commande else "—"
    remise_fmt = commande.date_remise_reelle.strftime("%d/%m/%Y") if commande.date_remise_reelle else "—"

    lignes_html = ""
    for l in lignes_enrichies:
        poids_label = f"{l['poids_g']}g"
        mouture_label = MOUTURES_LABELS.get(l['mouture'], l['mouture'])
        lignes_html += f"""
        <tr>
            <td>{l['origine']}</td>
            <td>{poids_label}</td>
            <td>{mouture_label}</td>
            <td style="text-align:right;">{l['prix_unitaire']:.2f} €</td>
        </tr>"""

    client_nom = f"{client.prenom} {client.nom}" if client else "Client"
    client_info = ""
    if client:
        if client.email:    client_info += f"<div>{client.email}</div>"
        if client.telephone: client_info += f"<div>{client.telephone}</div>"
        if client.ville:    client_info += f"<div>{client.ville}</div>"

    siret_line = f"<p>SIRET : {MARQUE['siret']}</p>" if MARQUE['siret'] else ""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;700;900&family=Outfit:wght@300;400;500&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Outfit', sans-serif;
    font-size: 13px;
    color: #261810;
    background: #fff;
    padding: 40px 48px;
  }}

  /* EN-TÊTE */
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 40px;
    padding-bottom: 24px;
    border-bottom: 3px solid #261810;
  }}

  .logo-block .brand {{
    font-family: 'Raleway', sans-serif;
    font-weight: 900;
    font-size: 32px;
    color: #261810;
    letter-spacing: 2px;
  }}

  .logo-block .tagline {{
    font-family: 'Raleway', sans-serif;
    font-weight: 300;
    font-size: 11px;
    color: #B07A8B;
    letter-spacing: 5px;
    text-transform: uppercase;
    margin-top: 2px;
  }}

  .doc-info {{
    text-align: right;
  }}

  .doc-info .facture-label {{
    font-family: 'Raleway', sans-serif;
    font-weight: 700;
    font-size: 22px;
    color: #C18A4A;
    letter-spacing: 1px;
  }}

  .doc-info .numero {{
    font-size: 14px;
    font-weight: 600;
    margin-top: 4px;
  }}

  .doc-info .date {{
    font-size: 12px;
    color: #666;
    margin-top: 2px;
  }}

  /* PARTIES */
  .parties {{
    display: flex;
    justify-content: space-between;
    margin-bottom: 36px;
    gap: 32px;
  }}

  .partie {{
    flex: 1;
    padding: 20px;
    border-radius: 10px;
  }}

  .partie.emetteur {{
    background: #261810;
    color: #DFCFC4;
  }}

  .partie.destinataire {{
    background: #f8f4f0;
    color: #261810;
  }}

  .partie-label {{
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    opacity: 0.5;
    margin-bottom: 8px;
  }}

  .partie-nom {{
    font-family: 'Raleway', sans-serif;
    font-weight: 700;
    font-size: 15px;
    margin-bottom: 6px;
  }}

  .partie div {{
    font-size: 12px;
    opacity: 0.7;
    line-height: 1.6;
  }}

  /* TABLEAU */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 24px;
  }}

  thead tr {{
    background: #261810;
    color: #DFCFC4;
  }}

  thead th {{
    padding: 10px 14px;
    font-family: 'Raleway', sans-serif;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    text-align: left;
  }}

  tbody tr {{
    border-bottom: 1px solid #f0e8e0;
  }}

  tbody tr:nth-child(even) {{
    background: #fdfaf7;
  }}

  tbody td {{
    padding: 12px 14px;
    font-size: 13px;
  }}

  /* TOTAL */
  .total-bloc {{
    display: flex;
    justify-content: flex-end;
    margin-bottom: 36px;
  }}

  .total-table {{
    min-width: 280px;
    border: 2px solid #261810;
    border-radius: 10px;
    overflow: hidden;
  }}

  .total-table tr td {{
    padding: 10px 16px;
    font-size: 13px;
  }}

  .total-table tr td:last-child {{
    text-align: right;
    font-weight: 600;
  }}

  .total-table tr.total-final {{
    background: #261810;
    color: #C18A4A;
  }}

  .total-table tr.total-final td {{
    font-family: 'Raleway', sans-serif;
    font-weight: 900;
    font-size: 16px;
    letter-spacing: 0.5px;
  }}

  /* PAIEMENT */
  .paiement-bloc {{
    background: #f8f4f0;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}

  .paiement-label {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #999;
    margin-bottom: 4px;
  }}

  .paiement-val {{
    font-weight: 600;
    font-size: 14px;
  }}

  .statut-paye {{
    background: #261810;
    color: #4ade80;
    padding: 6px 18px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
  }}

  /* PIED DE PAGE */
  .footer {{
    border-top: 1px solid #e0d4c8;
    padding-top: 20px;
    text-align: center;
    font-size: 11px;
    color: #999;
    line-height: 1.8;
  }}

  .footer .merci {{
    font-family: 'Raleway', sans-serif;
    font-weight: 700;
    font-size: 14px;
    color: #C18A4A;
    letter-spacing: 1px;
    margin-bottom: 8px;
  }}

  .accent {{ color: #C18A4A; font-weight: 600; }}
</style>
</head>
<body>

  <!-- EN-TÊTE -->
  <div class="header">
    <div class="logo-block">
      <div class="brand">KAHLO</div>
      <div class="tagline">café · lyon</div>
    </div>
    <div class="doc-info">
      <div class="facture-label">FACTURE</div>
      <div class="numero">{commande.numero}</div>
      <div class="date">Émise le {date_fmt}</div>
      {f'<div class="date">Remise le {remise_fmt}</div>' if commande.date_remise_reelle else ''}
    </div>
  </div>

  <!-- PARTIES -->
  <div class="parties">
    <div class="partie emetteur">
      <div class="partie-label">De</div>
      <div class="partie-nom">{MARQUE['nom']}</div>
      <div>{MARQUE['ville']}</div>
      <div>{MARQUE['email']}</div>
      {f"<div>{MARQUE['tel']}</div>" if MARQUE['tel'] else ''}
      {f"<div>SIRET : {MARQUE['siret']}</div>" if MARQUE['siret'] else ''}
    </div>
    <div class="partie destinataire">
      <div class="partie-label">Pour</div>
      <div class="partie-nom">{client_nom}</div>
      {client_info}
    </div>
  </div>

  <!-- DÉTAIL COMMANDE -->
  <table>
    <thead>
      <tr>
        <th>Origine</th>
        <th>Poids</th>
        <th>Mouture</th>
        <th style="text-align:right;">Prix</th>
      </tr>
    </thead>
    <tbody>
      {lignes_html}
    </tbody>
  </table>

  <!-- TOTAL -->
  <div class="total-bloc">
    <table class="total-table">
      <tr>
        <td>Sous-total HT</td>
        <td>{commande.montant_total:.2f} €</td>
      </tr>
      <tr>
        <td>TVA (auto-entrepreneur : exonéré)</td>
        <td>0.00 €</td>
      </tr>
      <tr class="total-final">
        <td>TOTAL</td>
        <td>{commande.montant_total:.2f} €</td>
      </tr>
    </table>
  </div>

  <!-- PAIEMENT -->
  <div class="paiement-bloc">
    <div>
      <div class="paiement-label">Mode de paiement</div>
      <div class="paiement-val">{"SumUp (carte bancaire)" if commande.paiement_mode == "sumup" else "Espèces"}</div>
      {f'<div style="font-size:11px;color:#999;margin-top:2px;">Réf. {commande.sumup_transaction_code}</div>' if commande.sumup_transaction_code else ''}
    </div>
    <div class="statut-paye">✓ Payé</div>
  </div>

  <!-- PIED DE PAGE -->
  <div class="footer">
    <div class="merci">Merci pour votre confiance ☕</div>
    <p>{MARQUE['nom']} — {MARQUE['ville']}</p>
    <p>{MARQUE['email']}{f" · {MARQUE['tel']}" if MARQUE['tel'] else ''}</p>
    {siret_line}
    <p style="margin-top:8px;font-style:italic;color:#b0a090;">
      Auto-entrepreneur — TVA non applicable, article 293B du CGI
    </p>
  </div>

</body>
</html>"""


async def generer_facture_pdf(db: AsyncSession, commande) -> str:
    """
    Génère le PDF de la facture pour une commande.
    Retourne le chemin du fichier PDF créé.
    """
    from sqlalchemy import select
    from models import Client, Lot

    # Charger le client
    client = await db.get(Client, commande.client_id)

    # Charger les détails des lignes avec le nom du lot
    lignes_enrichies = []
    for ligne in commande.lignes:
        lot = await db.get(Lot, ligne.lot_id)
        lignes_enrichies.append({
            "origine":      lot.origine if lot else f"Lot #{ligne.lot_id}",
            "poids_g":      ligne.poids_g,
            "mouture":      ligne.mouture,
            "prix_unitaire": ligne.prix_unitaire,
        })

    html = _html_facture(commande, client, lignes_enrichies)

    chemin = FACTURES_DIR / f"facture-{commande.numero}.pdf"

    # WeasyPrint est synchrone — on l'exécute dans un thread pour ne pas bloquer
    def _generer():
        try:
            from weasyprint import HTML
            HTML(string=html, base_url=None).write_pdf(str(chemin))
        except ImportError:
            # WeasyPrint pas encore installé : écriture HTML en fallback
            chemin_html = chemin.with_suffix(".html")
            chemin_html.write_text(html, encoding="utf-8")
            raise RuntimeError("WeasyPrint non installé — fichier HTML généré en fallback")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _generer)

    return str(chemin)
