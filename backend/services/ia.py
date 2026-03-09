"""
KAHLO CAFÉ — Service IA Gemini
Toutes les fonctions d'intelligence artificielle
Modèle : gemini-1.5-flash (gratuit, excellent en français)
"""

import google.generativeai as genai
import os
import json
from typing import Optional

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")


# ============================================================
#  ANALYSE DE MARCHÉ
# ============================================================

async def analyser_marche(marche_data: dict) -> str:
    """Génère un résumé narratif d'un marché passé"""
    prompt = f"""
    Tu es l'assistant de Kahlo Café, une marque de café artisanal lyonnaise.
    Analyse ce marché en 3-4 phrases, de façon concise et actionnable :

    - Nom : {marche_data['nom']}
    - Date : {marche_data['date']}
    - CA réalisé : {marche_data['ca']} €
    - Stock emmené : {marche_data['stock_emmene']} kg
    - Stock ramené : {marche_data['stock_ramene']} kg
    - Taux d'écoulement : {marche_data['taux_ecoulement']}%
    - Frais : {marche_data['frais']} €
    - Marge nette : {marche_data['marge_nette']} €
    - Météo : {marche_data.get('meteo', 'non renseignée')}
    - Notes : {marche_data.get('notes', '')}

    Donne des insights concrets sur ce qui a bien fonctionné ou pas,
    et une recommandation pour le prochain marché du même type.
    Réponds directement en français, sans introduction.
    """
    response = await model.generate_content_async(prompt)
    return response.text


# ============================================================
#  SUGGESTION DE STOCK
# ============================================================

async def suggerer_stock_marche(marche: dict, stocks: list, historique: list) -> dict:
    """
    Suggère les quantités optimales à emmener pour un marché
    basé sur l'historique de ventes
    """
    prompt = f"""
    Tu es l'assistant logistique de Kahlo Café.
    Suggère les quantités de café à emmener pour ce marché.
    
    Prochain marché : {marche['nom']} le {marche['date']}
    
    Stock disponible :
    {json.dumps(stocks, ensure_ascii=False, indent=2)}
    
    Historique des ventes sur des marchés similaires :
    {json.dumps(historique, ensure_ascii=False, indent=2)}
    
    Réponds UNIQUEMENT en JSON valide, sans markdown, avec ce format :
    {{
        "suggestions": [
            {{"origine": "Éthiopie Yirgacheffe", "quantite_kg": 3.5, "raison": "best seller"}},
            ...
        ],
        "conseil": "Une phrase de conseil général"
    }}
    """
    response = await model.generate_content_async(prompt)
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return {"suggestions": [], "conseil": response.text}


# ============================================================
#  FICHE PRODUIT (pour réseaux sociaux)
# ============================================================

async def generer_fiche_produit(lot: dict) -> dict:
    """Génère une fiche produit et un post Instagram pour une origine"""
    prompt = f"""
    Tu es le copywriter de Kahlo Café, marque de café artisanal inspirée par Frida Kahlo.
    L'identité de la marque : sensible, artistique, authentique, lyonnaise.
    
    Génère pour cette origine :
    - Une description produit courte (2-3 phrases, poétique mais informatif)
    - Un post Instagram (avec emojis, 3-4 lignes + 5 hashtags pertinents)
    
    Origine : {lot['origine']}
    Fournisseur : {lot['fournisseur']}
    Notes de dégustation : {lot['notes_degustation']}
    Prix : {lot['prix_vente_kg']} €/kg
    
    Réponds en JSON :
    {{
        "description_produit": "...",
        "post_instagram": "...",
        "hashtags": ["#kahlocafe", ...]
    }}
    """
    response = await model.generate_content_async(prompt)
    try:
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except json.JSONDecodeError:
        return {"description_produit": response.text, "post_instagram": "", "hashtags": []}


# ============================================================
#  ANALYSE DASHBOARD
# ============================================================

async def analyser_dashboard(data: dict) -> str:
    """Analyse générale de la situation business du mois"""
    prompt = f"""
    Tu es le conseiller business de Kahlo Café.
    Analyse la situation du mois en 4-5 phrases clés, directement actionnables.
    
    Données du mois :
    - CA : {data['ca_mois']} € (objectif : {data['ca_objectif']} €)
    - Marchés réalisés : {data['nb_marches']}
    - Stock critique : {data['stocks_critiques']} origines
    - Commandes en attente : {data['commandes_attente']}
    - Meilleure origine : {data['top_origine']}
    - Clients inactifs : {data['clients_inactifs']}
    
    Sois direct, sans introduction ni conclusion. Juste les insights.
    """
    response = await model.generate_content_async(prompt)
    return response.text


# ============================================================
#  PRÉVISION D'ÉPUISEMENT DE STOCK
# ============================================================

def calculer_epuisement(stock_kg: float, ventes_mois_kg: float) -> dict:
    """
    Calcul pur Python — pas besoin d'IA pour ça
    Retourne le nombre de jours avant épuisement
    """
    if ventes_mois_kg <= 0:
        return {"jours": 999, "statut": "ok"}

    ventes_par_jour = ventes_mois_kg / 30
    jours = round(stock_kg / ventes_par_jour)

    statut = "critique" if jours < 14 else "attention" if jours < 30 else "ok"
    return {"jours": jours, "statut": statut}


# ============================================================
#  DÉTECTION D'ANOMALIES
# ============================================================

def detecter_anomalies(ventes_historique: list) -> list:
    """
    Détecte les anomalies dans les ventes sans IA
    Algorithme simple : z-score
    """
    if len(ventes_historique) < 3:
        return []

    mean = sum(ventes_historique) / len(ventes_historique)
    variance = sum((x - mean) ** 2 for x in ventes_historique) / len(ventes_historique)
    std = variance ** 0.5

    anomalies = []
    for i, v in enumerate(ventes_historique):
        if std > 0 and abs(v - mean) > 2 * std:
            anomalies.append({
                "index": i,
                "valeur": v,
                "ecart": round(abs(v - mean) / std, 1),
                "type": "haute" if v > mean else "basse"
            })
    return anomalies


# ============================================================
#  RECOMMANDATION D'ASSORTIMENT
# ============================================================

def recommander_assortiment(marche_nom: str, historique_ventes: list) -> list:
    """
    Recommande l'assortiment optimal pour un marché
    Basé sur l'historique des ventes du même marché
    Algorithme de scoring pur Python
    """
    scores = {}

    for vente in historique_ventes:
        if vente.get("marche") == marche_nom:
            origine = vente["origine"]
            if origine not in scores:
                scores[origine] = {"total_kg": 0, "nb_fois": 0, "taux_moy": 0}
            scores[origine]["total_kg"] += vente["kg_vendu"]
            scores[origine]["nb_fois"] += 1
            scores[origine]["taux_moy"] += vente.get("taux_ecoulement", 80)

    # Calculer score final
    recommandations = []
    for origine, s in scores.items():
        score = (s["total_kg"] * 0.4) + (s["nb_fois"] * 0.3) + ((s["taux_moy"] / s["nb_fois"]) * 0.3)
        recommandations.append({
            "origine": origine,
            "score": round(score, 1),
            "kg_suggere": round(s["total_kg"] / s["nb_fois"] * 1.1, 1),  # +10% marge
        })

    return sorted(recommandations, key=lambda x: x["score"], reverse=True)
