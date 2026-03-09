import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "../components/Layout";
import { getCommandes, creerCommande, changerStatutCommande, notifierClientPrete, getClients, getLots, getMarches, creerCheckoutSumUp } from "../services/api";

const C = {
  espresso: "#261810", gold: "#C18A4A", prune: "#6B3F57",
  rose: "#B07A8B", creme: "#DFCFC4", dark: "#1a0f0a", card: "#2e1a10",
};

const STATUTS = {
  en_attente: { label: "En attente", color: C.gold,    bg: "rgba(193,138,74,0.12)" },
  prete:      { label: "Prête",      color: "#4ade80", bg: "rgba(74,222,128,0.1)" },
  remise:     { label: "Remise",     color: "rgba(223,207,196,0.4)", bg: "rgba(223,207,196,0.06)" },
  annulee:    { label: "Annulée",    color: "#e8a0b8", bg: "rgba(176,122,139,0.1)" },
};

const MOUTURES = ["Grains entiers", "Filtre", "Expresso", "Cafetière italienne", "Chemex"];

function Skeleton({ h = 18 }) {
  return <div style={{ height: h, borderRadius: 6, background: "rgba(193,138,74,0.06)", animation: "pulse 1.5s infinite" }} />;
}

export default function Commandes() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState(null);
  const [filterStatut, setFilterStatut] = useState("tous");
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [newCmd, setNewCmd] = useState({ client_id: "", lot_id: "", poids_g: 250, mouture: "Grains entiers", paiement_mode: "sumup", notes: "" });

  const { data: commandes = [], isLoading } = useQuery({
    queryKey: ["commandes", filterStatut],
    queryFn: () => getCommandes(filterStatut !== "tous" ? { statut: filterStatut } : {}),
    refetchInterval: 30_000,
  });

  const { data: clients = [] } = useQuery({ queryKey: ["clients"], queryFn: getClients });
  const { data: lots = [] }    = useQuery({ queryKey: ["lots"],    queryFn: () => getLots({ actif: true }) });
  const { data: marches = [] } = useQuery({ queryKey: ["marches-a-venir"], queryFn: getMarches });

  const changerStatutMutation = useMutation({
    mutationFn: ({ id, statut }) => changerStatutCommande(id, statut),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["commandes"] }); if (selected) setSelected(null); },
  });

  const notifierMutation = useMutation({
    mutationFn: notifierClientPrete,
    onSuccess: () => alert("Notification envoyée via Brevo"),
  });

  const creerMutation = useMutation({
    mutationFn: (data) => creerCommande(data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["commandes"] }); setShowAdd(false); },
  });

  const checkoutMutation = useMutation({
    mutationFn: creerCheckoutSumUp,
    onSuccess: (data) => { alert(`Lien de paiement SumUp créé :\n${data.checkout_url}`); },
  });

  const lotSelectionne = lots.find(l => l.id === parseInt(newCmd.lot_id));
  const prix = lotSelectionne ? Math.round((lotSelectionne.prix_vente_kg / 1000) * newCmd.poids_g) : 0;

  const filtered = commandes.filter(c =>
    `${c.numero}`.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total: commandes.filter(c => c.statut !== "annulee").length,
    en_attente: commandes.filter(c => c.statut === "en_attente").length,
    pretes: commandes.filter(c => c.statut === "prete").length,
    ca: commandes.filter(c => c.statut !== "annulee").reduce((a, c) => a + c.montant_total, 0),
  };

  return (
    <Layout>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=Raleway:wght@300;400;700;900&display=swap');
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: ${C.prune}; border-radius: 2px; }
        .card { background: ${C.card}; border: 1px solid rgba(193,138,74,0.12); border-radius: 16px; }
        .inp { background: rgba(0,0,0,0.3); border: 1px solid rgba(193,138,74,0.15); border-radius: 10px; padding: 9px 14px; color: ${C.creme}; font-family: 'Outfit',sans-serif; font-size: 13px; outline: none; width: 100%; }
        .btn-p { background: linear-gradient(135deg,${C.prune},${C.gold}); border: none; border-radius: 10px; padding: 10px 20px; color: white; font-size: 13px; font-weight: 600; cursor: pointer; font-family: 'Outfit',sans-serif; }
        .btn-g { background: rgba(193,138,74,0.08); border: 1px solid rgba(193,138,74,0.2); border-radius: 10px; padding: 8px 16px; color: ${C.gold}; font-size: 12px; font-weight: 600; cursor: pointer; font-family: 'Outfit',sans-serif; }
        .btn-sm { border: none; border-radius: 8px; padding: 5px 12px; font-size: 11px; font-weight: 600; cursor: pointer; font-family: 'Outfit',sans-serif; }
        .row { display: flex; align-items: center; gap: 12px; padding: 13px 18px; border-bottom: 1px solid rgba(223,207,196,0.05); cursor: pointer; transition: background 0.15s; }
        .row:hover { background: rgba(193,138,74,0.04); }
        .row.active { background: rgba(193,138,74,0.08); border-left: 2px solid ${C.gold}; }
        .poids-btn { background: rgba(193,138,74,0.08); border: 1px solid rgba(193,138,74,0.15); border-radius: 8px; padding: 8px 16px; color: ${C.gold}; font-size: 13px; font-weight: 600; cursor: pointer; }
        .poids-sel { background: rgba(193,138,74,0.2); border-color: ${C.gold}; }
      `}</style>

      <div style={{ padding: "32px 28px", fontFamily: "'Outfit', sans-serif", color: C.creme, marginRight: selected ? 380 : 0, transition: "margin-right 0.3s" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div>
            <h1 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 24 }}>Commandes</h1>
            <p style={{ color: "rgba(223,207,196,0.4)", fontSize: 13, marginTop: 3 }}>
              {stats.en_attente} en attente · {stats.pretes} prêtes · {stats.ca.toFixed(2)} € engagés
            </p>
          </div>
          <button className="btn-p" onClick={() => setShowAdd(true)}>+ Nouvelle commande</button>
        </div>

        {/* KPIs */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 22 }}>
          {[
            { label: "Actives", value: stats.total },
            { label: "En attente", value: stats.en_attente, alert: stats.en_attente > 0 },
            { label: "Prêtes", value: stats.pretes, ok: stats.pretes > 0 },
            { label: "CA engagé", value: `${stats.ca.toFixed(2)} €` },
          ].map((k, i) => (
            <div key={i} className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>{k.label}</div>
              <div style={{ fontSize: 26, fontFamily: "'Raleway', sans-serif", fontWeight: 700, color: k.alert ? C.gold : k.ok ? "#4ade80" : C.gold }}>{k.value}</div>
            </div>
          ))}
        </div>

        {/* Filtres */}
        <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
          <input className="inp" placeholder="🔍 N° commande..." value={search} onChange={e => setSearch(e.target.value)} style={{ maxWidth: 220 }} />
          <select className="inp" style={{ maxWidth: 160 }} value={filterStatut} onChange={e => setFilterStatut(e.target.value)}>
            <option value="tous">Tous les statuts</option>
            {Object.entries(STATUTS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
        </div>

        {/* Tableau */}
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "100px 1fr 120px 90px 80px 120px", gap: 8, padding: "12px 18px", background: "rgba(0,0,0,0.2)", borderBottom: "1px solid rgba(193,138,74,0.1)" }}>
            {["N°", "Client", "Marché remise", "Montant", "Statut", "Action"].map(h => (
              <div key={h} style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", fontWeight: 600, textTransform: "uppercase" }}>{h}</div>
            ))}
          </div>

          {isLoading
            ? [1,2,3].map(i => <div key={i} style={{ padding: "14px 18px", borderBottom: "1px solid rgba(223,207,196,0.05)" }}><Skeleton /></div>)
            : filtered.length === 0
              ? <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "rgba(223,207,196,0.3)" }}>Aucune commande</div>
              : filtered.map(c => {
                const s = STATUTS[c.statut] || STATUTS.en_attente;
                return (
                  <div key={c.id} className={`row ${selected?.id === c.id ? "active" : ""}`}
                    style={{ display: "grid", gridTemplateColumns: "100px 1fr 120px 90px 80px 120px", gap: 8, alignItems: "center" }}
                    onClick={() => setSelected(selected?.id === c.id ? null : c)}>
                    <div style={{ fontFamily: "monospace", fontSize: 11, color: "rgba(223,207,196,0.4)" }}>{c.numero}</div>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>
                      {/* On affiche l'ID client car le backend ne retourne pas toujours le nom dans la liste */}
                      Client #{c.client_id}
                      <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)", marginTop: 1 }}>{new Date(c.date_commande).toLocaleDateString("fr-FR")}</div>
                    </div>
                    <div style={{ fontSize: 11, color: "rgba(223,207,196,0.5)" }}>{c.date_remise_prev ? new Date(c.date_remise_prev).toLocaleDateString("fr-FR") : "—"}</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: C.gold }}>{c.montant_total} €</div>
                    <div>
                      <span style={{ background: s.bg, color: s.color, padding: "3px 9px", borderRadius: 20, fontSize: 10, fontWeight: 600 }}>{s.label}</span>
                    </div>
                    <div onClick={e => e.stopPropagation()}>
                      {c.statut === "en_attente" && (
                        <button className="btn-sm" style={{ background: "rgba(74,222,128,0.1)", color: "#4ade80", border: "1px solid rgba(74,222,128,0.2)" }}
                          onClick={() => changerStatutMutation.mutate({ id: c.id, statut: "prete" })}>
                          ✓ Prête
                        </button>
                      )}
                      {c.statut === "prete" && (
                        <button className="btn-sm" style={{ background: "rgba(193,138,74,0.1)", color: C.gold, border: "1px solid rgba(193,138,74,0.2)" }}
                          onClick={() => notifierMutation.mutate(c.id)}>
                          📱 Notifier
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
          }
        </div>
      </div>

      {/* Panel détail */}
      {selected && (
        <div style={{ position: "fixed", right: 0, top: 0, width: 380, height: "100vh", background: C.espresso, borderLeft: "1px solid rgba(193,138,74,0.15)", padding: "28px 24px", overflowY: "auto", zIndex: 100 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
            <span style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 12, color: C.gold, textTransform: "uppercase", letterSpacing: 1 }}>Détail commande</span>
            <button onClick={() => setSelected(null)} style={{ background: "none", border: "none", color: "rgba(223,207,196,0.4)", cursor: "pointer", fontSize: 22 }}>×</button>
          </div>

          <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 20, marginBottom: 4 }}>{selected.numero}</div>
          <span style={{ background: STATUTS[selected.statut]?.bg, color: STATUTS[selected.statut]?.color, padding: "4px 14px", borderRadius: 20, fontSize: 11, fontWeight: 600 }}>
            {STATUTS[selected.statut]?.label}
          </span>

          <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 0 }}>
            {[
              { l: "Montant", v: `${selected.montant_total} €`, c: C.gold },
              { l: "Paiement", v: selected.paiement_mode === "sumup" ? "SumUp" : "Espèces" },
              { l: "Commande le", v: new Date(selected.date_commande).toLocaleDateString("fr-FR") },
              { l: "Remise prévue", v: selected.date_remise_prev ? new Date(selected.date_remise_prev).toLocaleDateString("fr-FR") : "—" },
              selected.notes && { l: "Notes", v: selected.notes },
            ].filter(Boolean).map((r, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid rgba(223,207,196,0.06)" }}>
                <span style={{ fontSize: 12, color: "rgba(223,207,196,0.4)" }}>{r.l}</span>
                <span style={{ fontSize: 12, fontWeight: 600, color: r.c || C.creme }}>{r.v}</span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 8 }}>
            {selected.statut === "en_attente" && <>
              <button className="btn-p" style={{ width: "100%", padding: 11 }} onClick={() => changerStatutMutation.mutate({ id: selected.id, statut: "prete" })}>✓ Marquer comme prête</button>
              {selected.paiement_mode === "sumup" && <button className="btn-g" style={{ width: "100%", padding: 11 }} onClick={() => checkoutMutation.mutate(selected.id)}>💳 Créer lien paiement SumUp</button>}
            </>}
            {selected.statut === "prete" && <>
              <button className="btn-p" style={{ width: "100%", padding: 11 }} onClick={() => notifierMutation.mutate(selected.id)}>📱 Notifier — commande prête</button>
              <button className="btn-g" style={{ width: "100%", padding: 11 }} onClick={() => changerStatutMutation.mutate({ id: selected.id, statut: "remise" })}>✓ Marquer comme remise</button>
            </>}
            {selected.statut === "remise" && <>
              <a href={`/api/commandes/${selected.id}/facture`} target="_blank" rel="noopener">
                <button className="btn-g" style={{ width: "100%", padding: 11 }}>🧾 Télécharger facture PDF</button>
              </a>
            </>}
            <button className="btn-g" style={{ width: "100%", padding: 11 }} onClick={() => changerStatutMutation.mutate({ id: selected.id, statut: "annulee" })}>✗ Annuler</button>
          </div>
        </div>
      )}

      {/* Modal nouvelle commande */}
      {showAdd && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={() => setShowAdd(false)}>
          <div style={{ background: C.espresso, border: "1px solid rgba(193,138,74,0.2)", borderRadius: 20, padding: 32, width: 480, maxHeight: "90vh", overflowY: "auto" }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
              <h2 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 18 }}>Nouvelle commande</h2>
              <button onClick={() => setShowAdd(false)} style={{ background: "none", border: "none", color: "rgba(223,207,196,0.4)", cursor: "pointer", fontSize: 22 }}>×</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Client *</label>
                <select className="inp" value={newCmd.client_id} onChange={e => setNewCmd(p => ({ ...p, client_id: e.target.value }))}>
                  <option value="">— Sélectionner un client —</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.prenom} {c.nom}</option>)}
                </select>
              </div>

              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Origine *</label>
                <select className="inp" value={newCmd.lot_id} onChange={e => setNewCmd(p => ({ ...p, lot_id: e.target.value }))}>
                  <option value="">— Sélectionner un lot —</option>
                  {lots.map(l => <option key={l.id} value={l.id}>{l.origine} ({l.stock_kg}kg dispo)</option>)}
                </select>
              </div>

              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Poids</label>
                <div style={{ display: "flex", gap: 8 }}>
                  {[250, 500, 1000].map(p => (
                    <button key={p} className={`poids-btn ${newCmd.poids_g === p ? "poids-sel" : ""}`} onClick={() => setNewCmd(prev => ({ ...prev, poids_g: p }))}>{p}g</button>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Mouture</label>
                <select className="inp" value={newCmd.mouture} onChange={e => setNewCmd(p => ({ ...p, mouture: e.target.value }))}>
                  {MOUTURES.map(m => <option key={m}>{m}</option>)}
                </select>
              </div>

              {prix > 0 && (
                <div style={{ background: "rgba(193,138,74,0.08)", border: "1px solid rgba(193,138,74,0.2)", borderRadius: 12, padding: "14px 18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, color: "rgba(223,207,196,0.6)" }}>Prix calculé</span>
                  <span style={{ fontSize: 24, fontFamily: "'Raleway', sans-serif", fontWeight: 900, color: C.gold }}>{prix} €</span>
                </div>
              )}

              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Paiement</label>
                <div style={{ display: "flex", gap: 8 }}>
                  {[{ v: "sumup", l: "💳 SumUp" }, { v: "especes", l: "💶 Espèces" }].map(opt => (
                    <div key={opt.v} onClick={() => setNewCmd(p => ({ ...p, paiement_mode: opt.v }))} style={{ flex: 1, padding: "10px 14px", borderRadius: 10, cursor: "pointer", textAlign: "center", fontSize: 13, background: newCmd.paiement_mode === opt.v ? "rgba(193,138,74,0.15)" : "rgba(0,0,0,0.2)", border: `1px solid ${newCmd.paiement_mode === opt.v ? "rgba(193,138,74,0.4)" : "rgba(193,138,74,0.1)"}`, color: newCmd.paiement_mode === opt.v ? C.gold : "rgba(223,207,196,0.5)" }}>
                      {opt.l}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Notes</label>
                <textarea className="inp" rows={2} style={{ resize: "none" }} value={newCmd.notes} onChange={e => setNewCmd(p => ({ ...p, notes: e.target.value }))} placeholder="Instructions particulières..." />
              </div>

              <button
                className="btn-p" style={{ padding: 13, marginTop: 4, opacity: creerMutation.isPending ? 0.7 : 1 }}
                disabled={creerMutation.isPending || !newCmd.client_id || !newCmd.lot_id}
                onClick={() => creerMutation.mutate({
                  client_id: parseInt(newCmd.client_id),
                  lignes: [{ lot_id: parseInt(newCmd.lot_id), poids_g: newCmd.poids_g, mouture: newCmd.mouture, prix_unitaire: prix }],
                  paiement_mode: newCmd.paiement_mode,
                  notes: newCmd.notes,
                })}
              >
                {creerMutation.isPending ? "Création..." : "Créer la commande"}
              </button>
              {creerMutation.isError && <div style={{ fontSize: 12, color: "#e8a0b8" }}>Erreur lors de la création</div>}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
