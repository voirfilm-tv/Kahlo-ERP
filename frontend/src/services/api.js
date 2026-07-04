/**
 * KAHLO CAFÉ — Client API
 * Toutes les fonctions qui appellent le backend FastAPI.
 * Le JWT est envoyé automatiquement via cookie HttpOnly (withCredentials).
 * Le CSRF token est lu depuis le cookie kahlo_csrf et envoyé dans le header X-CSRF-Token.
 *
 * IMPORTANT : les chemins ci-dessous doivent rester alignés avec les routers
 * FastAPI (backend/routers/*). Les tests backend font foi.
 */

import axios from "axios";
import { useAuthStore } from "../stores/auth";

// ────────────────────────────────────────────────────────────
//  Instance Axios
// ────────────────────────────────────────────────────────────

function _getCookie(name) {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,  // Envoie les cookies HttpOnly à chaque requête
});

// Injecte le CSRF token à chaque requête mutative
api.interceptors.request.use((config) => {
  const csrf = _getCookie("kahlo_csrf");
  if (csrf) config.headers["X-CSRF-Token"] = csrf;
  return config;
});

// Redirige vers /login si token expiré
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;

// ────────────────────────────────────────────────────────────
//  HELPERS
// ────────────────────────────────────────────────────────────

/** Extrait le message d'erreur lisible depuis une réponse Axios.
 *  Priorité : detail (FastAPI) > message > statusText > fallback */
export function extractError(err, fallback = "Une erreur est survenue") {
  const d = err?.response?.data;
  if (typeof d?.detail === "string") return d.detail;
  if (Array.isArray(d?.detail)) return d.detail.map(e => e.msg).join(", ");
  if (typeof d?.message === "string") return d.message;
  if (err?.response?.statusText) return err.response.statusText;
  if (err?.message === "Network Error") return "Impossible de joindre le serveur";
  return fallback;
}

/** Télécharge un fichier authentifié (PDF etc.) via axios + blob */
export async function telechargerFichier(url, nomFichier) {
  const res = await api.get(url, { responseType: "blob" });
  const blobUrl = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = nomFichier;
  a.click();
  URL.revokeObjectURL(blobUrl);
}

// ────────────────────────────────────────────────────────────
//  AUTH
// ────────────────────────────────────────────────────────────

export const login = (username, password) =>
  api.post("/auth/login", { username, password }).then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  DASHBOARD
// ────────────────────────────────────────────────────────────

export const getDashboardStats = () =>
  api.get("/analytics/dashboard").then((r) => r.data);

export const getCaMensuel = (mois = 7) =>
  api.get("/analytics/ca-mensuel", { params: { mois } }).then((r) => r.data);

export const getMarchesAVenir = () =>
  api.get("/marches/a_venir").then((r) => r.data);

export const getAnalyseIA = () =>
  api.post("/ia/analyser-dashboard").then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  STOCK & LOTS
// ────────────────────────────────────────────────────────────

export const getLots = (params = {}) =>
  api.get("/stock/", { params }).then((r) => r.data);

export const getLot = (id) =>
  api.get(`/stock/${id}`).then((r) => r.data);

export const creerLot = (data) =>
  api.post("/stock/", data).then((r) => r.data);

export const modifierLot = (id, data) =>
  api.patch(`/stock/${id}`, data).then((r) => r.data);

export const ajusterStock = (lotId, deltaKg, motif) =>
  api.post("/stock/ajustement", { lot_id: lotId, delta_kg: deltaKg, motif }).then((r) => r.data);

export const getStatsStock = () =>
  api.get("/stock/stats").then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  FOURNISSEURS
// ────────────────────────────────────────────────────────────

export const getFournisseurs = () =>
  api.get("/fournisseurs/").then((r) => r.data);

export const creerFournisseur = (data) =>
  api.post("/fournisseurs/", data).then((r) => r.data);

export const noterFournisseur = (id, score) =>
  api.patch(`/fournisseurs/${id}/score`, null, { params: { score } }).then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  CLIENTS / CRM
// ────────────────────────────────────────────────────────────

export const getClients = (params = {}) =>
  api.get("/clients/", { params }).then((r) => r.data);

export const getClient = (id) =>
  api.get(`/clients/${id}`).then((r) => r.data);

export const creerClient = (data) =>
  api.post("/clients/", data).then((r) => r.data);

export const modifierClient = (id, data) =>
  api.patch(`/clients/${id}`, data).then((r) => r.data);

export const ajouterTampon = (id) =>
  api.post(`/clients/${id}/tampon`).then((r) => r.data);

export const resetTampons = (id) =>
  api.post(`/clients/${id}/tampon/reset`).then((r) => r.data);

export const getAlertesCRM = () =>
  api.get("/clients/alertes").then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  COMMANDES
// ────────────────────────────────────────────────────────────

export const getCommandes = (params = {}) =>
  api.get("/commandes/", { params }).then((r) => r.data);

export const getCommande = (id) =>
  api.get(`/commandes/${id}`).then((r) => r.data);

export const creerCommande = (data) =>
  api.post("/commandes/", data).then((r) => r.data);

export const changerStatutCommande = (id, statut, notes) =>
  api.patch(`/commandes/${id}/statut`, { statut, notes }).then((r) => r.data);

export const notifierClientPrete = (id) =>
  api.post(`/commandes/${id}/notifier-prete`).then((r) => r.data);

export const creerCheckoutSumUp = (id) =>
  api.post(`/commandes/${id}/checkout-sumup`).then((r) => r.data);

export const verifierStatutPaiement = (id) =>
  api.get(`/commandes/${id}/statut-paiement`).then((r) => r.data);

export const getStatsCommandes = () =>
  api.get("/commandes/stats").then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  MARCHÉS
// ────────────────────────────────────────────────────────────

export const getMarches = (params = {}) =>
  api.get("/marches/", { params }).then((r) => r.data);

export const creerMarche = (data) =>
  api.post("/marches/", data).then((r) => r.data);

export const modifierMarche = (id, data) =>
  api.patch(`/marches/${id}`, data).then((r) => r.data);

export const changerStatutMarche = (id, statut) =>
  api.patch(`/marches/${id}/statut`, null, { params: { statut } }).then((r) => r.data);

export const saisirBilanMarche = (id, data) =>
  api.post(`/marches/${id}/bilan`, data).then((r) => r.data);

export const getBilanMarche = (id) =>
  api.get(`/marches/${id}/bilan`).then((r) => r.data);

export const getAnalyseMarcheIA = (id) =>
  api.get(`/marches/${id}/analyse-ia`).then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  CALENDRIER / ÉVÉNEMENTS
// ────────────────────────────────────────────────────────────

export const getEvenements = (params = {}) =>
  api.get("/calendrier/", { params }).then((r) => r.data);

export const creerEvenement = (data) =>
  api.post("/calendrier/", data).then((r) => r.data);

export const supprimerEvenement = (id) =>
  api.delete(`/calendrier/${id}`).then((r) => r.data);

export const syncCalendrier = () =>
  api.post("/calendrier/sync/caldav").then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  ANALYTICS
// ────────────────────────────────────────────────────────────

export const getAnalyticsGeneral = (params = {}) =>
  api.get("/analytics/general", { params }).then((r) => r.data);

export const getAnalyticsMarches = () =>
  api.get("/analytics/marches").then((r) => r.data);

export const getAnalyticsOrigines = () =>
  api.get("/analytics/origines").then((r) => r.data);

export const getAnalyticsClients = () =>
  api.get("/analytics/clients").then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  INVESTISSEMENTS & CALCULATRICE PRIX
// ────────────────────────────────────────────────────────────

export const getInvestissements = (params = {}) =>
  api.get("/investissements/", { params }).then((r) => r.data);

export const getStatsInvestissements = () =>
  api.get("/investissements/stats").then((r) => r.data);

export const creerInvestissement = (data) =>
  api.post("/investissements/", data).then((r) => r.data);

export const modifierInvestissement = (id, data) =>
  api.patch(`/investissements/${id}`, data).then((r) => r.data);

export const supprimerInvestissement = (id) =>
  api.delete(`/investissements/${id}`).then((r) => r.data);

export const enregistrerVentesInvestissement = (id, quantite = 1) =>
  api.post(`/investissements/${id}/vente`, { quantite }).then((r) => r.data);

export const calculerPrixVente = (data) =>
  api.post("/investissements/calculatrice", data).then((r) => r.data);

export const getScenariosPrix = () =>
  api.get("/investissements/scenarios").then((r) => r.data);

export const creerScenarioPrix = (data) =>
  api.post("/investissements/scenarios", data).then((r) => r.data);

export const modifierScenarioPrix = (id, data) =>
  api.patch(`/investissements/scenarios/${id}`, data).then((r) => r.data);

export const supprimerScenarioPrix = (id) =>
  api.delete(`/investissements/scenarios/${id}`).then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  SUMUP — VENTES RÉELLES
// ────────────────────────────────────────────────────────────

export const getStatutSumUp = () =>
  api.get("/sumup/statut").then((r) => r.data);

export const syncVentesSumUp = (joursHistorique) =>
  api.post("/sumup/sync", joursHistorique ? { jours_historique: joursHistorique } : {}).then((r) => r.data);

export const getVentesSumUp = (params = {}) =>
  api.get("/sumup/ventes", { params }).then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  PARAMÈTRES
// ────────────────────────────────────────────────────────────

export const getParametres = () =>
  api.get("/parametres/").then((r) => r.data);

export const sauvegarderParametres = (data) =>
  api.post("/parametres/", data).then((r) => r.data);

export const testerConnexionSumUp = () =>
  api.post("/parametres/tester-sumup").then((r) => r.data);

export const testerConnexionBrevo = () =>
  api.post("/parametres/tester-brevo").then((r) => r.data);

export const testerConnexionGemini = () =>
  api.post("/parametres/tester-gemini").then((r) => r.data);

export const sauvegarderMaintenant = () =>
  api.post("/parametres/sauvegarde").then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  UTILISATEURS & MOT DE PASSE
// ────────────────────────────────────────────────────────────

export const changerMotDePasse = (ancien, nouveau, confirmer) =>
  api.post("/utilisateurs/mot-de-passe", {
    ancien_mot_de_passe: ancien,
    nouveau_mot_de_passe: nouveau,
    confirmer_mot_de_passe: confirmer,
  }).then((r) => r.data);

export const getUtilisateurs = () =>
  api.get("/utilisateurs/").then((r) => r.data);

export const creerUtilisateur = (data) =>
  api.post("/utilisateurs/", data).then((r) => r.data);

export const modifierUtilisateur = (id, data) =>
  api.patch(`/utilisateurs/${id}`, data).then((r) => r.data);

export const supprimerUtilisateur = (id) =>
  api.delete(`/utilisateurs/${id}`).then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  DOMAINES
// ────────────────────────────────────────────────────────────

export const getDomaines = () =>
  api.get("/utilisateurs/domaines").then((r) => r.data);

export const ajouterDomaine = (data) =>
  api.post("/utilisateurs/domaines", data).then((r) => r.data);

export const verifierDomaine = (id) =>
  api.post(`/utilisateurs/domaines/${id}/verifier`).then((r) => r.data);

export const modifierDomaine = (id, data) =>
  api.patch(`/utilisateurs/domaines/${id}`, data).then((r) => r.data);

export const supprimerDomaine = (id) =>
  api.delete(`/utilisateurs/domaines/${id}`).then((r) => r.data);


// ────────────────────────────────────────────────────────────
//  MISE À JOUR LOGICIELLE (ADMIN)
// ────────────────────────────────────────────────────────────

export const getSystemUpdateStatus = () =>
  api.get("/system-update/status").then((r) => r.data);

export const verifierMiseAJourSysteme = () =>
  api.post("/system-update/check").then((r) => r.data);

export const lancerMiseAJourSysteme = (targetVersion) =>
  api.post("/system-update/start", { target_version: targetVersion }).then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  SYNC OFFLINE
// ────────────────────────────────────────────────────────────

export const lancerSync = () =>
  api.post("/sync/").then((r) => r.data);

export const getSyncStatus = () =>
  api.get("/sync/status").then((r) => r.data);
