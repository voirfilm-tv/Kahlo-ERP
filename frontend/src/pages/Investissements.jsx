/**
 * KAHLO CAFÉ — Panel Investissements
 * 3 onglets calqués sur la calculatrice Excel :
 *  - Investissements : achats amortis par unité de produit vendue
 *  - Calculatrice prix : composants de coût + marge + impôts + SumUp → prix de vente
 *  - Rentabilité : marge cumulée par scénario (feuille « renta »)
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "../components/Layout";
import {
  getInvestissements, getStatsInvestissements, creerInvestissement,
  modifierInvestissement, supprimerInvestissement, enregistrerVentesInvestissement,
  getScenariosPrix, creerScenarioPrix, modifierScenarioPrix, supprimerScenarioPrix,
  extractError,
} from "../services/api";

const C = {
  espresso: "#261810", gold: "#C18A4A", prune: "#6B3F57",
  rose: "#B07A8B", creme: "#DFCFC4", dark: "#1a0f0a", card: "#2e1a10",
  green: "#4ade80", red: "#e8a0b8",
};

const CATEGORIES = {
  materiel:    { label: "Matériel",    color: "#C18A4A", bg: "rgba(193,138,74,0.12)" },
  consommable: { label: "Consommable", color: "#B07A8B", bg: "rgba(176,122,139,0.15)" },
  marchandise: { label: "Marchandise", color: "#4ade80", bg: "rgba(74,222,128,0.1)" },
  evenement:   { label: "Événement",   color: "#8ab4f8", bg: "rgba(138,180,248,0.12)" },
  autre:       { label: "Autre",       color: "rgba(223,207,196,0.5)", bg: "rgba(223,207,196,0.06)" },
};

const EMPTY_INV = { nom: "", categorie: "materiel", valeur_totale: "", quantite: "1", amortissement_unites: "1", unites_vendues: "0", notes: "" };
const EMPTY_LIGNE = { libelle: "", valeur: "" };
const DEFAUT_CALC = {
  nom: "",
  composants: [
    { libelle: "Prix d'achat + livraison", valeur: "" },
    { libelle: "Emballage", valeur: "" },
  ],
  marge_pct: "30",
  taux_impots: "12.5",
  taux_sumup: "1.75",
  unites_vendues: "0",
};

function Skeleton({ h = 20, w = "100%" }) {
  return <div style={{ width: w, height: h, borderRadius: 6, background: "rgba(193,138,74,0.06)", animation: "pulse 1.5s infinite" }} />;
}

const eur = (v, dec = 2) =>
  (v ?? 0).toLocaleString("fr-FR", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + " €";

const num = (v) => {
  const n = parseFloat(String(v).replace(",", "."));
  return isNaN(n) ? 0 : n;
};

/** Formule Excel : PV = (coûts + marge) / (1 - (impôts + sumup)/100).
 *  Version live côté client — le backend fait foi à l'enregistrement. */
function calculLocal(composants, margePct, tauxImpots, tauxSumup) {
  const coutTotal = composants.reduce((a, c) => a + num(c.valeur), 0);
  const margeValeur = coutTotal * num(margePct) / 100;
  const taux = (num(tauxImpots) + num(tauxSumup)) / 100;
  const prixVente = taux < 1 ? (coutTotal + margeValeur) / (1 - taux) : 0;
  return { coutTotal, margeValeur, prixVente, frais: prixVente - coutTotal - margeValeur };
}

export default function Investissements() {
  const qc = useQueryClient();
  const [tab, setTab] = useState("investissements");
  const [showAdd, setShowAdd] = useState(false);
  const [editing, setEditing] = useState(null);      // investissement en cours d'édition
  const [form, setForm] = useState(EMPTY_INV);
  const [calc, setCalc] = useState(DEFAUT_CALC);
  const [editingScenario, setEditingScenario] = useState(null);
  const [toast, setToast] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null); // {type, id, nom}

  const notif = (ok, text) => { setToast({ ok, text }); setTimeout(() => setToast(null), 4000); };

  // ── Queries ──────────────────────────────────────────────
  const { data: invs = [], isLoading } = useQuery({
    queryKey: ["investissements"],
    queryFn: () => getInvestissements({ actif: true }),
  });

  const { data: stats } = useQuery({
    queryKey: ["investissements-stats"],
    queryFn: getStatsInvestissements,
  });

  const { data: scenarios = [], isLoading: loadingScenarios } = useQuery({
    queryKey: ["scenarios-prix"],
    queryFn: getScenariosPrix,
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["investissements"] });
    qc.invalidateQueries({ queryKey: ["investissements-stats"] });
    qc.invalidateQueries({ queryKey: ["scenarios-prix"] });
  };

  // ── Mutations investissements ────────────────────────────
  const saveInvMutation = useMutation({
    mutationFn: (data) => editing ? modifierInvestissement(editing.id, data) : creerInvestissement(data),
    onSuccess: () => { refresh(); setShowAdd(false); setEditing(null); setForm(EMPTY_INV); notif(true, editing ? "Investissement modifié" : "Investissement ajouté"); },
    onError: (err) => notif(false, extractError(err, "Erreur lors de l'enregistrement")),
  });

  const venteMutation = useMutation({
    mutationFn: ({ id, quantite }) => enregistrerVentesInvestissement(id, quantite),
    onSuccess: refresh,
    onError: (err) => notif(false, extractError(err)),
  });

  const deleteInvMutation = useMutation({
    mutationFn: supprimerInvestissement,
    onSuccess: () => { refresh(); setConfirmDelete(null); notif(true, "Investissement supprimé"); },
    onError: (err) => notif(false, extractError(err)),
  });

  // ── Mutations scénarios ──────────────────────────────────
  const saveScenarioMutation = useMutation({
    mutationFn: (data) => editingScenario ? modifierScenarioPrix(editingScenario, data) : creerScenarioPrix(data),
    onSuccess: () => { refresh(); setCalc(DEFAUT_CALC); setEditingScenario(null); notif(true, editingScenario ? "Scénario mis à jour" : "Scénario enregistré"); },
    onError: (err) => notif(false, extractError(err, "Erreur lors de l'enregistrement du scénario")),
  });

  const deleteScenarioMutation = useMutation({
    mutationFn: supprimerScenarioPrix,
    onSuccess: () => { refresh(); setConfirmDelete(null); notif(true, "Scénario supprimé"); },
    onError: (err) => notif(false, extractError(err)),
  });

  const majVentesScenarioMutation = useMutation({
    mutationFn: ({ id, unites_vendues }) => modifierScenarioPrix(id, { unites_vendues }),
    onSuccess: refresh,
    onError: (err) => notif(false, extractError(err)),
  });

  // ── Helpers formulaire ───────────────────────────────────
  const openEdit = (inv) => {
    setEditing(inv);
    setForm({
      nom: inv.nom, categorie: inv.categorie,
      valeur_totale: String(inv.valeur_totale), quantite: String(inv.quantite),
      amortissement_unites: String(inv.amortissement_unites), unites_vendues: String(inv.unites_vendues),
      notes: inv.notes || "",
    });
    setShowAdd(true);
  };

  const submitInv = () => {
    saveInvMutation.mutate({
      nom: form.nom.trim(),
      categorie: form.categorie,
      valeur_totale: num(form.valeur_totale),
      quantite: num(form.quantite) || 1,
      amortissement_unites: num(form.amortissement_unites) || 1,
      unites_vendues: num(form.unites_vendues),
      notes: form.notes || null,
    });
  };

  const openEditScenario = (s) => {
    setEditingScenario(s.id);
    setCalc({
      nom: s.nom,
      composants: (s.composants || []).map(c => ({ libelle: c.libelle, valeur: String(c.valeur) })),
      marge_pct: String(s.marge_pct),
      taux_impots: String(s.taux_impots),
      taux_sumup: String(s.taux_sumup),
      unites_vendues: String(s.unites_vendues),
    });
    setTab("calculatrice");
  };

  const submitScenario = () => {
    saveScenarioMutation.mutate({
      nom: calc.nom.trim(),
      composants: calc.composants
        .filter(c => c.libelle.trim())
        .map(c => ({ libelle: c.libelle.trim(), valeur: num(c.valeur) })),
      marge_pct: num(calc.marge_pct),
      taux_impots: num(calc.taux_impots),
      taux_sumup: num(calc.taux_sumup),
      unites_vendues: num(calc.unites_vendues),
    });
  };

  const live = calculLocal(calc.composants, calc.marge_pct, calc.taux_impots, calc.taux_sumup);
  const margeTotaleRenta = scenarios.reduce((a, s) => a + (s.marge_totale || 0), 0);

  return (
    <Layout>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=Raleway:wght@300;400;700;900&display=swap');
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: ${C.prune}; border-radius: 2px; }
        .card { background: rgba(46,26,16,0.55); backdrop-filter: blur(20px) saturate(180%); -webkit-backdrop-filter: blur(20px) saturate(180%); border: 1px solid rgba(193,138,74,0.12); border-radius: 18px; box-shadow: 0 4px 24px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.04); transition: transform 0.2s ease, box-shadow 0.2s ease; }
        .card:hover { transform: translateY(-1px); box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06); }
        .inp { background: rgba(0,0,0,0.25); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); border: 1px solid rgba(193,138,74,0.15); border-radius: 12px; padding: 10px 14px; color: ${C.creme}; font-family: 'Outfit',sans-serif; font-size: 13px; outline: none; width: 100%; box-shadow: inset 0 1px 0 rgba(255,255,255,0.03); transition: border-color 0.2s, box-shadow 0.2s; }
        .inp:focus { border-color: rgba(193,138,74,0.4); box-shadow: 0 0 0 3px rgba(193,138,74,0.08), inset 0 1px 0 rgba(255,255,255,0.03); }
        .btn-p { background: linear-gradient(135deg,${C.prune},${C.gold}); border: none; border-radius: 12px; padding: 10px 20px; color: white; font-size: 13px; font-weight: 600; cursor: pointer; font-family: 'Outfit',sans-serif; box-shadow: 0 4px 16px rgba(107,63,87,0.3), inset 0 1px 0 rgba(255,255,255,0.15); transition: all 0.25s ease; }
        .btn-p:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(107,63,87,0.4), inset 0 1px 0 rgba(255,255,255,0.2); }
        .btn-p:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-g { background: rgba(193,138,74,0.06); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); border: 1px solid rgba(193,138,74,0.15); border-radius: 12px; padding: 8px 16px; color: ${C.gold}; font-size: 12px; font-weight: 600; cursor: pointer; font-family: 'Outfit',sans-serif; box-shadow: inset 0 1px 0 rgba(255,255,255,0.03); transition: all 0.2s ease; }
        .btn-g:hover { background: rgba(193,138,74,0.12); border-color: rgba(193,138,74,0.3); }
        .btn-sm { border: none; border-radius: 8px; padding: 5px 10px; font-size: 11px; font-weight: 600; cursor: pointer; font-family: 'Outfit',sans-serif; }
        .tab-a { padding: 7px 16px; border-radius: 10px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid rgba(193,138,74,0.2); font-family: 'Outfit',sans-serif; background: rgba(193,138,74,0.12); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); color: ${C.gold}; box-shadow: inset 0 1px 0 rgba(255,255,255,0.04); transition: all 0.2s; }
        .tab-i { padding: 7px 16px; border-radius: 10px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid transparent; font-family: 'Outfit',sans-serif; background: transparent; color: rgba(223,207,196,0.4); transition: all 0.2s; }
        .tab-i:hover { background: rgba(193,138,74,0.05); }
        .inv-row { border-bottom: 1px solid rgba(223,207,196,0.05); transition: background 0.15s; }
        .inv-row:hover { background: rgba(193,138,74,0.04); }
      `}</style>

      <div style={{ padding: "32px 28px", fontFamily: "'Outfit', sans-serif", color: C.creme }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div>
            <h1 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 24 }}>Investissements</h1>
            <p style={{ color: "rgba(223,207,196,0.4)", fontSize: 13, marginTop: 3 }}>
              Suivi des achats, amortissement par produit vendu & calculatrice de prix
            </p>
          </div>
          {tab === "investissements" && (
            <button className="btn-p" onClick={() => { setEditing(null); setForm(EMPTY_INV); setShowAdd(true); }}>+ Nouvel investissement</button>
          )}
        </div>

        {/* Toast */}
        {toast && (
          <div style={{ padding: "10px 16px", borderRadius: 12, marginBottom: 16, fontSize: 12, display: "flex", justifyContent: "space-between", alignItems: "center", background: toast.ok ? "rgba(74,222,128,0.08)" : "rgba(232,160,184,0.08)", color: toast.ok ? C.green : C.red, border: `1px solid ${toast.ok ? "rgba(74,222,128,0.2)" : "rgba(232,160,184,0.2)"}` }}>
            <span>{toast.ok ? "✓" : "✗"} {toast.text}</span>
            <button onClick={() => setToast(null)} style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", fontSize: 16 }}>×</button>
          </div>
        )}

        {/* KPIs globaux */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 22 }}>
          {[
            { label: "Total investi", value: stats ? eur(stats.total_investi) : null, sub: `${stats?.nb_investissements ?? "—"} investissement(s)` },
            { label: "Déjà remboursé", value: stats ? eur(stats.total_rembourse) : null, sub: `${stats?.nb_amortis ?? 0} totalement amorti(s)`, ok: true },
            { label: "Reste à amortir", value: stats ? eur(stats.total_restant) : null, sub: "Sur les ventes futures", alert: stats?.total_restant > 0 },
            { label: "Progression", value: stats ? `${stats.progression_pct}%` : null, sub: "De l'investissement récupéré" },
          ].map((k, i) => (
            <div key={i} className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>{k.label}</div>
              {k.value === null
                ? <Skeleton h={28} w="60%" />
                : <div style={{ fontSize: 24, fontFamily: "'Raleway', sans-serif", fontWeight: 700, color: k.alert ? C.red : k.ok ? C.green : C.gold, marginBottom: 4 }}>{k.value}</div>
              }
              <div style={{ fontSize: 11, color: "rgba(223,207,196,0.3)" }}>{k.sub}</div>
            </div>
          ))}
        </div>

        {/* Barre de progression globale */}
        {stats && stats.total_investi > 0 && (
          <div className="card" style={{ padding: "14px 18px", marginBottom: 22, display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ fontSize: 12, color: "rgba(223,207,196,0.5)", whiteSpace: "nowrap" }}>Amortissement global</div>
            <div style={{ flex: 1, height: 8, background: "rgba(223,207,196,0.06)", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${stats.progression_pct}%`, background: `linear-gradient(90deg, ${C.prune}, ${C.gold})`, borderRadius: 4, transition: "width 0.5s" }} />
            </div>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.gold, whiteSpace: "nowrap" }}>{stats.progression_pct}%</div>
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: "flex", gap: 6, marginBottom: 18 }}>
          <button className={tab === "investissements" ? "tab-a" : "tab-i"} onClick={() => setTab("investissements")}>◇ Investissements</button>
          <button className={tab === "calculatrice" ? "tab-a" : "tab-i"} onClick={() => setTab("calculatrice")}>⌘ Calculatrice prix</button>
          <button className={tab === "rentabilite" ? "tab-a" : "tab-i"} onClick={() => setTab("rentabilite")}>◬ Rentabilité</button>
        </div>

        {/* ═══════════ TAB INVESTISSEMENTS ═══════════ */}
        {tab === "investissements" && (
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1.6fr 110px 90px 90px 100px 100px 100px 1fr 130px", gap: 8, padding: "12px 18px", background: "rgba(0,0,0,0.2)", borderBottom: "1px solid rgba(193,138,74,0.1)" }}>
              {["Investissement", "Valeur totale", "Quantité", "Coût/unité", "Amort. (ventes)", "Coût/produit", "Vendu", "Remboursé / Restant", "Actions"].map(h => (
                <div key={h} style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase" }}>{h}</div>
              ))}
            </div>

            {isLoading
              ? [1, 2, 3, 4].map(i => <div key={i} style={{ padding: "14px 18px", borderBottom: "1px solid rgba(223,207,196,0.05)" }}><Skeleton h={18} /></div>)
              : invs.length === 0
                ? <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "rgba(223,207,196,0.3)" }}>
                    Aucun investissement — ajoutez votre premier achat (imprimante, étiquettes, kakemono...)
                  </div>
                : invs.map(inv => {
                  const cat = CATEGORIES[inv.categorie] || CATEGORIES.autre;
                  const amorti = inv.restant <= 0;
                  return (
                    <div key={inv.id} className="inv-row" style={{ display: "grid", gridTemplateColumns: "1.6fr 110px 90px 90px 100px 100px 100px 1fr 130px", gap: 8, alignItems: "center", padding: "13px 18px" }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 3 }}>{inv.nom}</div>
                        <span style={{ background: cat.bg, color: cat.color, padding: "2px 8px", borderRadius: 20, fontSize: 9, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>{cat.label}</span>
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: C.gold }}>{eur(inv.valeur_totale)}</div>
                      <div style={{ fontSize: 12, color: "rgba(223,207,196,0.5)" }}>{inv.quantite}</div>
                      <div style={{ fontSize: 12, color: "rgba(223,207,196,0.5)" }}>{eur(inv.cout_unitaire, inv.cout_unitaire < 1 ? 3 : 2)}</div>
                      <div style={{ fontSize: 12, color: "rgba(223,207,196,0.5)" }}>{inv.amortissement_unites}</div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: C.rose }}>{eur(inv.cout_par_produit, inv.cout_par_produit < 1 ? 3 : 2)}</div>
                      <div style={{ fontSize: 12, color: "rgba(223,207,196,0.6)" }}>{inv.unites_vendues}</div>
                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
                          <span style={{ color: C.green }}>{eur(inv.somme_remboursee)}</span>
                          <span style={{ color: amorti ? C.green : C.red }}>
                            {amorti ? "✓ Amorti" : `${eur(inv.restant)} restant`}
                          </span>
                        </div>
                        <div style={{ height: 4, background: "rgba(223,207,196,0.06)", borderRadius: 2, overflow: "hidden" }}>
                          <div style={{ height: "100%", width: `${inv.progression_pct}%`, background: amorti ? C.green : `linear-gradient(90deg, ${C.prune}, ${C.gold})`, borderRadius: 2 }} />
                        </div>
                      </div>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="btn-sm" title="Enregistrer une vente (avance l'amortissement)"
                          style={{ background: "rgba(74,222,128,0.1)", color: C.green, border: "1px solid rgba(74,222,128,0.2)" }}
                          onClick={() => venteMutation.mutate({ id: inv.id, quantite: 1 })}>+1 vente</button>
                        <button className="btn-sm" title="Modifier"
                          style={{ background: "rgba(193,138,74,0.1)", color: C.gold, border: "1px solid rgba(193,138,74,0.2)" }}
                          onClick={() => openEdit(inv)}>✎</button>
                        <button className="btn-sm" title="Supprimer"
                          style={{ background: "rgba(232,160,184,0.08)", color: C.red, border: "1px solid rgba(232,160,184,0.2)" }}
                          onClick={() => setConfirmDelete({ type: "investissement", id: inv.id, nom: inv.nom })}>🗑</button>
                      </div>
                    </div>
                  );
                })
            }
          </div>
        )}

        {/* ═══════════ TAB CALCULATRICE ═══════════ */}
        {tab === "calculatrice" && (
          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 20, alignItems: "start" }}>

            {/* Colonne gauche : saisie */}
            <div className="card" style={{ padding: 24 }}>
              <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 13, marginBottom: 4 }}>
                {editingScenario ? "Modifier le scénario" : "Composer un prix de vente"}
              </div>
              <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)", marginBottom: 18 }}>
                Additionnez vos coûts, fixez la marge — le prix intègre impôts et frais SumUp.
              </div>

              <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Nom du produit *</label>
              <input className="inp" placeholder="PDV expresso 250g" value={calc.nom}
                onChange={e => setCalc(p => ({ ...p, nom: e.target.value }))} style={{ marginBottom: 16 }} />

              <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Composants du coût</label>
              {calc.composants.map((c, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                  <input className="inp" placeholder="Libellé (ex: sticker, imprimante...)" value={c.libelle}
                    onChange={e => setCalc(p => ({ ...p, composants: p.composants.map((x, j) => j === i ? { ...x, libelle: e.target.value } : x) }))} />
                  <input className="inp" type="number" step="0.01" min="0" placeholder="0.00" value={c.valeur} style={{ maxWidth: 110 }}
                    onChange={e => setCalc(p => ({ ...p, composants: p.composants.map((x, j) => j === i ? { ...x, valeur: e.target.value } : x) }))} />
                  <button className="btn-sm" style={{ background: "rgba(232,160,184,0.08)", color: C.red, border: "1px solid rgba(232,160,184,0.15)", flexShrink: 0 }}
                    onClick={() => setCalc(p => ({ ...p, composants: p.composants.filter((_, j) => j !== i) }))}>×</button>
                </div>
              ))}
              <button className="btn-g" style={{ marginBottom: 20 }}
                onClick={() => setCalc(p => ({ ...p, composants: [...p.composants, { ...EMPTY_LIGNE }] }))}>+ Ajouter un coût</button>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 16 }}>
                {[
                  { key: "marge_pct", label: "% de marge" },
                  { key: "taux_impots", label: "Taux impôts %" },
                  { key: "taux_sumup", label: "Taux SumUp %" },
                ].map(f => (
                  <div key={f.key}>
                    <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>{f.label}</label>
                    <input className="inp" type="number" step="0.01" min="0" value={calc[f.key]}
                      onChange={e => setCalc(p => ({ ...p, [f.key]: e.target.value }))} />
                  </div>
                ))}
              </div>

              <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Unités vendues (pour la rentabilité)</label>
              <input className="inp" type="number" min="0" value={calc.unites_vendues}
                onChange={e => setCalc(p => ({ ...p, unites_vendues: e.target.value }))} style={{ maxWidth: 160, marginBottom: 20 }} />

              <div style={{ display: "flex", gap: 10 }}>
                <button className="btn-p" disabled={!calc.nom.trim() || live.coutTotal <= 0 || saveScenarioMutation.isPending}
                  onClick={submitScenario}>
                  {saveScenarioMutation.isPending ? "Enregistrement..." : editingScenario ? "✓ Mettre à jour" : "💾 Enregistrer ce scénario"}
                </button>
                {editingScenario && (
                  <button className="btn-g" onClick={() => { setEditingScenario(null); setCalc(DEFAUT_CALC); }}>Annuler</button>
                )}
              </div>
            </div>

            {/* Colonne droite : résultat live + scénarios */}
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div className="card" style={{ padding: 24, background: `linear-gradient(135deg, rgba(107,63,87,0.25), rgba(46,26,16,0.55))` }}>
                <div style={{ fontSize: 10, color: "rgba(223,207,196,0.4)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 10 }}>Prix de vente conseillé</div>
                <div style={{ fontSize: 42, fontFamily: "'Raleway', sans-serif", fontWeight: 900, color: C.gold, marginBottom: 18 }}>
                  {live.prixVente > 0 ? eur(live.prixVente) : "—"}
                </div>
                {[
                  { l: "Coût total", v: eur(live.coutTotal) },
                  { l: `Marge (${num(calc.marge_pct)}%)`, v: eur(live.margeValeur), c: C.green },
                  { l: `Impôts + SumUp (${(num(calc.taux_impots) + num(calc.taux_sumup)).toFixed(2)}%)`, v: eur(live.frais), c: C.rose },
                ].map((r, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(223,207,196,0.06)" }}>
                    <span style={{ fontSize: 12, color: "rgba(223,207,196,0.45)" }}>{r.l}</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: r.c || C.creme }}>{r.v}</span>
                  </div>
                ))}
                {num(calc.taux_impots) + num(calc.taux_sumup) >= 100 && (
                  <div style={{ marginTop: 12, fontSize: 12, color: C.red }}>⚠ Taux cumulés ≥ 100% — calcul impossible</div>
                )}
              </div>

              {/* Scénarios enregistrés */}
              <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "14px 18px", borderBottom: "1px solid rgba(193,138,74,0.1)", fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 13 }}>
                  Scénarios enregistrés
                </div>
                {loadingScenarios
                  ? <div style={{ padding: 18 }}><Skeleton h={40} /></div>
                  : scenarios.length === 0
                    ? <div style={{ padding: 24, fontSize: 12, color: "rgba(223,207,196,0.3)", textAlign: "center" }}>Aucun scénario — enregistrez votre premier calcul</div>
                    : scenarios.map(s => (
                      <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 18px", borderBottom: "1px solid rgba(223,207,196,0.05)" }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 13, fontWeight: 600 }}>{s.nom}</div>
                          <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)" }}>
                            coût {eur(s.cout_total)} · marge {s.marge_pct}%
                          </div>
                        </div>
                        <div style={{ fontSize: 16, fontFamily: "'Raleway', sans-serif", fontWeight: 900, color: C.gold }}>{eur(s.prix_vente)}</div>
                        <button className="btn-sm" style={{ background: "rgba(193,138,74,0.1)", color: C.gold, border: "1px solid rgba(193,138,74,0.2)" }}
                          onClick={() => openEditScenario(s)}>✎</button>
                        <button className="btn-sm" style={{ background: "rgba(232,160,184,0.08)", color: C.red, border: "1px solid rgba(232,160,184,0.2)" }}
                          onClick={() => setConfirmDelete({ type: "scenario", id: s.id, nom: s.nom })}>🗑</button>
                      </div>
                    ))
                }
              </div>
            </div>
          </div>
        )}

        {/* ═══════════ TAB RENTABILITÉ ═══════════ */}
        {tab === "rentabilite" && (
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1.6fr 120px 120px 120px 140px 120px", gap: 8, padding: "12px 18px", background: "rgba(0,0,0,0.2)", borderBottom: "1px solid rgba(193,138,74,0.1)" }}>
              {["Produit", "Prix de vente", "Marge / unité", "Unités vendues", "Marge totale", "Actions"].map(h => (
                <div key={h} style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase" }}>{h}</div>
              ))}
            </div>

            {loadingScenarios
              ? [1, 2, 3].map(i => <div key={i} style={{ padding: "14px 18px" }}><Skeleton h={18} /></div>)
              : scenarios.length === 0
                ? <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "rgba(223,207,196,0.3)" }}>
                    Créez des scénarios dans l'onglet Calculatrice pour suivre la rentabilité
                  </div>
                : <>
                  {scenarios.map(s => (
                    <div key={s.id} className="inv-row" style={{ display: "grid", gridTemplateColumns: "1.6fr 120px 120px 120px 140px 120px", gap: 8, alignItems: "center", padding: "13px 18px" }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{s.nom}</div>
                      <div style={{ fontSize: 13, color: C.gold, fontWeight: 700 }}>{eur(s.prix_vente)}</div>
                      <div style={{ fontSize: 12, color: C.green }}>{eur(s.marge_valeur)}</div>
                      <div>
                        <input className="inp" type="number" min="0" defaultValue={s.unites_vendues} style={{ maxWidth: 90, padding: "6px 10px", fontSize: 12 }}
                          onBlur={e => {
                            const v = num(e.target.value);
                            if (v !== s.unites_vendues) majVentesScenarioMutation.mutate({ id: s.id, unites_vendues: v });
                          }} />
                      </div>
                      <div style={{ fontSize: 14, fontFamily: "'Raleway', sans-serif", fontWeight: 900, color: s.marge_totale >= 0 ? C.green : C.red }}>{eur(s.marge_totale)}</div>
                      <button className="btn-sm" style={{ background: "rgba(193,138,74,0.1)", color: C.gold, border: "1px solid rgba(193,138,74,0.2)", justifySelf: "start" }}
                        onClick={() => openEditScenario(s)}>✎ Détails</button>
                    </div>
                  ))}
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "16px 18px", background: "rgba(0,0,0,0.15)" }}>
                    <span style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, color: "rgba(223,207,196,0.5)" }}>Somme des marges</span>
                    <span style={{ fontSize: 18, fontFamily: "'Raleway', sans-serif", fontWeight: 900, color: margeTotaleRenta >= 0 ? C.green : C.red }}>{eur(margeTotaleRenta)}</span>
                  </div>
                </>
            }
          </div>
        )}
      </div>

      {/* Modal investissement (création / édition) */}
      {showAdd && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={() => { setShowAdd(false); setEditing(null); }}>
          <div style={{ background: C.espresso, border: "1px solid rgba(193,138,74,0.2)", borderRadius: 20, padding: 32, width: 500, maxHeight: "90vh", overflowY: "auto" }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
              <h2 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 18 }}>{editing ? "Modifier l'investissement" : "Nouvel investissement"}</h2>
              <button onClick={() => { setShowAdd(false); setEditing(null); }} style={{ background: "none", border: "none", color: "rgba(223,207,196,0.4)", cursor: "pointer", fontSize: 22 }}>×</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Nom *</label>
                <input className="inp" placeholder="Imprimante, rouleau étiquettes, kakemono..." value={form.nom}
                  onChange={e => setForm(p => ({ ...p, nom: e.target.value }))} />
              </div>

              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Catégorie</label>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {Object.entries(CATEGORIES).map(([k, v]) => (
                    <div key={k} onClick={() => setForm(p => ({ ...p, categorie: k }))}
                      style={{ padding: "7px 14px", borderRadius: 8, cursor: "pointer", fontSize: 12, fontWeight: 600, transition: "all 0.15s", background: form.categorie === k ? v.bg : "rgba(0,0,0,0.2)", color: form.categorie === k ? v.color : "rgba(223,207,196,0.4)", border: `1px solid ${form.categorie === k ? v.color + "44" : "rgba(193,138,74,0.1)"}` }}>
                      {v.label}
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {[
                  { key: "valeur_totale", label: "Valeur totale (€) *", placeholder: "73.46", hint: "Coût d'achat total" },
                  { key: "quantite", label: "Quantité achetée", placeholder: "1", hint: "ex: 500 étiquettes" },
                  { key: "amortissement_unites", label: "Amortissement (ventes)", placeholder: "300", hint: "Nb de produits vendus pour amortir 1 unité" },
                  { key: "unites_vendues", label: "Unités déjà vendues", placeholder: "0", hint: "Produits vendus depuis l'achat" },
                ].map(f => (
                  <div key={f.key}>
                    <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>{f.label}</label>
                    <input className="inp" type="number" step="0.01" min="0" placeholder={f.placeholder} value={form[f.key]}
                      onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))} />
                    <div style={{ fontSize: 10, color: "rgba(223,207,196,0.25)", marginTop: 3 }}>{f.hint}</div>
                  </div>
                ))}
              </div>

              {/* Aperçu live du coût par produit */}
              {num(form.valeur_totale) > 0 && (
                <div style={{ background: "rgba(193,138,74,0.08)", border: "1px solid rgba(193,138,74,0.2)", borderRadius: 12, padding: "12px 16px", fontSize: 12, color: "rgba(223,207,196,0.6)" }}>
                  Coût imputé par produit vendu :{" "}
                  <strong style={{ color: C.gold }}>
                    {eur(num(form.valeur_totale) / (num(form.quantite) || 1) / (num(form.amortissement_unites) || 1), 4)}
                  </strong>
                </div>
              )}

              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Notes</label>
                <textarea className="inp" rows={2} style={{ resize: "none" }} value={form.notes}
                  onChange={e => setForm(p => ({ ...p, notes: e.target.value }))} placeholder="Fournisseur, référence..." />
              </div>

              <button className="btn-p" style={{ padding: 13, marginTop: 4 }}
                disabled={saveInvMutation.isPending || !form.nom.trim() || num(form.valeur_totale) <= 0}
                onClick={submitInv}>
                {saveInvMutation.isPending ? "Enregistrement..." : editing ? "✓ Mettre à jour" : "Créer l'investissement"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal confirmation suppression */}
      {confirmDelete && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 300, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={() => setConfirmDelete(null)}>
          <div style={{ background: C.espresso, border: "1px solid rgba(232,160,184,0.25)", borderRadius: 20, padding: 28, width: 400 }} onClick={e => e.stopPropagation()}>
            <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 16, marginBottom: 10 }}>Confirmer la suppression</div>
            <div style={{ fontSize: 13, color: "rgba(223,207,196,0.6)", marginBottom: 20 }}>
              Supprimer « {confirmDelete.nom} » ? Cette action est définitive.
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button className="btn-g" onClick={() => setConfirmDelete(null)}>Annuler</button>
              <button className="btn-p" style={{ background: "linear-gradient(135deg, #7a3048, #b0546e)" }}
                disabled={deleteInvMutation.isPending || deleteScenarioMutation.isPending}
                onClick={() => confirmDelete.type === "investissement"
                  ? deleteInvMutation.mutate(confirmDelete.id)
                  : deleteScenarioMutation.mutate(confirmDelete.id)}>
                Supprimer
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
