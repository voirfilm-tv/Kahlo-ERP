/**
 * KAHLO CAFÉ — Client API
 * Toutes les fonctions qui appellent le backend FastAPI.
 * Le token JWT est injecté automatiquement depuis le store Zustand.
 */

import axios from "axios";
import { useAuthStore } from "../stores/auth";

// ────────────────────────────────────────────────────────────
//  Instance Axios
// ────────────────────────────────────────────────────────────

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Injecte le token JWT à chaque requête
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
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
//  AUTH
// ────────────────────────────────────────────────────────────

export const login = (username, password) =>
  api.post("/auth/token", new URLSearchParams({ username, password }), {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  }).then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  DASHBOARD
// ────────────────────────────────────────────────────────────

export const getDashboardStats = () =>
  api.get("/analytics/dashboard").then((r) => r.data);

export const getCaMensuel = (mois = 7) =>
  api.get("/analytics/ca-mensuel", { params: { mois } }).then((r) => r.data);

export const getMarchesAVenir = () =>
  api.get("/marches", { params: { a_venir: true, limit: 5 } }).then((r) => r.data);

export const getAnalyseIA = () =>
  api.post("/ia/analyser-dashboard").then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  STOCK & LOTS
// ────────────────────────────────────────────────────────────

export const getLots = (params = {}) =>
  api.get("/stock/lots", { params }).then((r) => r.data);

export const getLot = (id) =>
  api.get(`/stock/lots/${id}`).then((r) => r.data);

export const creerLot = (data) =>
  api.post("/stock/lots", data).then((r) => r.data);

export const modifierLot = (id, data) =>
  api.patch(`/stock/lots/${id}`, data).then((r) => r.data);

export const ajusterStock = (id, delta, raison) =>
  api.post(`/stock/lots/${id}/ajuster`, { delta, raison }).then((r) => r.data);

export const getAlertesStock = () =>
  api.get("/stock/alertes").then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  FOURNISSEURS
// ────────────────────────────────────────────────────────────

export const getFournisseurs = () =>
  api.get("/fournisseurs").then((r) => r.data);

export const getFournisseur = (id) =>
  api.get(`/fournisseurs/${id}`).then((r) => r.data);

export const creerFournisseur = (data) =>
  api.post("/fournisseurs", data).then((r) => r.data);

export const noterFournisseur = (id, score) =>
  api.patch(`/fournisseurs/${id}/note`, { score }).then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  CLIENTS / CRM
// ────────────────────────────────────────────────────────────

export const getClients = (params = {}) =>
  api.get("/clients", { params }).then((r) => r.data);

export const getClient = (id) =>
  api.get(`/clients/${id}`).then((r) => r.data);

export const creerClient = (data) =>
  api.post("/clients", data).then((r) => r.data);

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
  api.get("/commandes", { params }).then((r) => r.data);

export const getCommande = (id) =>
  api.get(`/commandes/${id}`).then((r) => r.data);

export const creerCommande = (data) =>
  api.post("/commandes", data).then((r) => r.data);

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
  api.get("/marches", { params }).then((r) => r.data);

export const getMarche = (id) =>
  api.get(`/marches/${id}`).then((r) => r.data);

export const creerMarche = (data) =>
  api.post("/marches", data).then((r) => r.data);

export const modifierMarche = (id, data) =>
  api.patch(`/marches/${id}`, data).then((r) => r.data);

export const getBilanMarche = (id) =>
  api.get(`/marches/${id}/bilan`).then((r) => r.data);

export const getAnalyseMarcheIA = (id) =>
  api.post(`/ia/analyser-marche/${id}`).then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  CALENDRIER / ÉVÉNEMENTS
// ────────────────────────────────────────────────────────────

export const getEvenements = (params = {}) =>
  api.get("/calendrier/evenements", { params }).then((r) => r.data);

export const getEvenement = (id) =>
  api.get(`/calendrier/evenements/${id}`).then((r) => r.data);

export const creerEvenement = (data) =>
  api.post("/calendrier/evenements", data).then((r) => r.data);

export const modifierEvenement = (id, data) =>
  api.patch(`/calendrier/evenements/${id}`, data).then((r) => r.data);

export const supprimerEvenement = (id) =>
  api.delete(`/calendrier/evenements/${id}`).then((r) => r.data);

export const syncCalendrier = () =>
  api.post("/calendrier/sync").then((r) => r.data);

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
//  IA
// ────────────────────────────────────────────────────────────

export const getSuggestionStock = (marcheId) =>
  api.post("/ia/suggerer-stock", { marche_id: marcheId }).then((r) => r.data);

export const getFicheProduit = (lotId) =>
  api.post(`/ia/fiche-produit/${lotId}`).then((r) => r.data);

// ────────────────────────────────────────────────────────────
//  PARAMÈTRES
// ────────────────────────────────────────────────────────────

export const getParametres = () =>
  api.get("/parametres").then((r) => r.data);

export const sauvegarderParametres = (data) =>
  api.post("/parametres", data).then((r) => r.data);

export const testerConnexionSumUp = () =>
  api.post("/parametres/tester-sumup").then((r) => r.data);

export const testerConnexionBrevo = () =>
  api.post("/parametres/tester-brevo").then((r) => r.data);

export const testerConnexionGemini = () =>
  api.post("/parametres/tester-gemini").then((r) => r.data);

export const sauvegarderMaintenant = () =>
  api.post("/parametres/sauvegarde").then((r) => r.data);
