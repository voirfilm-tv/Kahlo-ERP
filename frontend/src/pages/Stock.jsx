import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "../components/Layout";
import { getLots, creerLot, modifierLot, ajusterStock, getFournisseurs } from "../services/api";

const C = {
  espresso: "#261810", gold: "#C18A4A", prune: "#6B3F57",
  rose: "#B07A8B", creme: "#DFCFC4", dark: "#1a0f0a", card: "#2e1a10",
};

function Skeleton({ h = 20, w = "100%" }) {
  return <div style={{ width: w, height: h, borderRadius: 6, background: "rgba(193,138,74,0.06)", animation: "pulse 1.5s infinite" }} />;
}

const MOUTURES = ["Grains entiers", "Filtre", "Expresso", "Cafetière italienne", "Chemex"];

export default function Stock() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState(null);
  const [tab, setTab] = useState("lots");
  const [showAdd, setShowAdd] = useState(false);
  const [search, setSearch] = useState("");
  const [newLot, setNewLot] = useState({ origine: "", fournisseur_id: "", stock_kg: "", seuil_alerte_kg: "3", prix_achat_kg: "", prix_vente_kg: "", notes_degustation: "" });

  const { data: lots = [], isLoading: loadingLots } = useQuery({
    queryKey: ["lots"],
    queryFn: () => getLots({ actif: true }),
    refetchInterval: 30_000,
  });

  const { data: fournisseurs = [], isLoading: loadingFourn } = useQuery({
    queryKey: ["fournisseurs"],
    queryFn: getFournisseurs,
  });

  const creerMutation = useMutation({
    mutationFn: creerLot,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["lots"] }); setShowAdd(false); setNewLot({ origine: "", fournisseur_id: "", stock_kg: "", seuil_alerte_kg: "3", prix_achat_kg: "", prix_vente_kg: "", notes_degustation: "" }); },
  });

  const ajusterMutation = useMutation({
    mutationFn: ({ id, delta, raison }) => ajusterStock(id, delta, raison),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["lots"] }),
  });

  const filtered = lots.filter(l =>
    `${l.origine} ${l.numero_lot}`.toLowerCase().includes(search.toLowerCase())
  );
  const alertes = lots.filter(l => l.est_critique);

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
        .lot-row { display: flex; align-items: center; gap: 14px; padding: 14px 18px; border-bottom: 1px solid rgba(223,207,196,0.05); cursor: pointer; transition: background 0.15s; }
        .lot-row:hover { background: rgba(193,138,74,0.04); }
        .lot-row.active { background: rgba(193,138,74,0.08); border-left: 2px solid ${C.gold}; }
        .tab-a { padding: 7px 16px; border-radius: 8px; font-size: 12px; font-weight: 500; cursor: pointer; border: none; font-family: 'Outfit',sans-serif; background: rgba(193,138,74,0.15); color: ${C.gold}; }
        .tab-i { padding: 7px 16px; border-radius: 8px; font-size: 12px; font-weight: 500; cursor: pointer; border: none; font-family: 'Outfit',sans-serif; background: transparent; color: rgba(223,207,196,0.4); }
      `}</style>

      <div style={{ padding: "32px 28px", fontFamily: "'Outfit', sans-serif", color: C.creme, marginRight: selected ? 360 : 0, transition: "margin-right 0.3s" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div>
            <h1 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 24 }}>Stock & Fournisseurs</h1>
            <p style={{ color: "rgba(223,207,196,0.4)", fontSize: 13, marginTop: 3 }}>
              {lots.length} lot(s) actif(s) · {alertes.length > 0 ? <span style={{ color: "#e8a0b8" }}>{alertes.length} en alerte</span> : <span style={{ color: "#4ade80" }}>Tout OK</span>}
            </p>
          </div>
          <button className="btn-p" onClick={() => setShowAdd(true)}>+ Nouveau lot</button>
        </div>

        {/* Alertes banner */}
        {alertes.length > 0 && (
          <div style={{ background: "rgba(232,160,184,0.08)", border: "1px solid rgba(232,160,184,0.2)", borderRadius: 12, padding: "12px 18px", marginBottom: 20, display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ color: "#e8a0b8", fontSize: 16 }}>⚠</span>
            <span style={{ fontSize: 13, color: "rgba(223,207,196,0.7)" }}>
              <strong style={{ color: C.creme }}>{alertes.length} lot(s)</strong> en dessous du seuil d'alerte : {alertes.map(l => l.origine).join(", ")}
            </span>
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: "flex", gap: 6, marginBottom: 18 }}>
          <button className={tab === "lots" ? "tab-a" : "tab-i"} onClick={() => setTab("lots")}>◉ Lots</button>
          <button className={tab === "fournisseurs" ? "tab-a" : "tab-i"} onClick={() => setTab("fournisseurs")}>◧ Fournisseurs</button>
        </div>

        {/* TAB LOTS */}
        {tab === "lots" && (
          <>
            <input className="inp" placeholder="🔍 Rechercher une origine..." value={search} onChange={e => setSearch(e.target.value)} style={{ maxWidth: 320, marginBottom: 16 }} />

            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1.8fr 1fr 80px 90px 80px 90px", gap: 8, padding: "12px 18px", background: "rgba(0,0,0,0.2)", borderBottom: "1px solid rgba(193,138,74,0.1)" }}>
                {["Origine", "Fournisseur", "Stock", "Seuil", "Marge", "DLC"].map(h => (
                  <div key={h} style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase" }}>{h}</div>
                ))}
              </div>

              {loadingLots
                ? [1,2,3,4].map(i => (
                    <div key={i} style={{ padding: "14px 18px", borderBottom: "1px solid rgba(223,207,196,0.05)" }}>
                      <Skeleton h={18} />
                    </div>
                  ))
                : filtered.length === 0
                  ? <div style={{ padding: 32, textAlign: "center", fontSize: 13, color: "rgba(223,207,196,0.3)" }}>
                      {search ? "Aucun résultat" : "Aucun lot — commencez par en ajouter un"}
                    </div>
                  : filtered.map(l => {
                    const pct = Math.min(100, (l.stock_kg / Math.max(l.seuil_alerte_kg * 3, 10)) * 100);
                    const barColor = l.est_critique ? "#e8a0b8" : l.stock_kg < l.seuil_alerte_kg * 2 ? C.gold : "#4ade80";
                    const fourn = fournisseurs.find(f => f.id === l.fournisseur_id);
                    return (
                      <div key={l.id} className={`lot-row ${selected?.id === l.id ? "active" : ""}`}
                        style={{ display: "grid", gridTemplateColumns: "1.8fr 1fr 80px 90px 80px 90px", gap: 8, alignItems: "center" }}
                        onClick={() => setSelected(selected?.id === l.id ? null : l)}>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>{l.origine}</div>
                          <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)", fontFamily: "monospace" }}>{l.numero_lot}</div>
                        </div>
                        <div style={{ fontSize: 12, color: "rgba(223,207,196,0.5)" }}>{fourn?.nom || "—"}</div>
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 600, color: barColor, marginBottom: 3 }}>{l.stock_kg} kg</div>
                          <div style={{ height: 3, background: "rgba(223,207,196,0.06)", borderRadius: 2, overflow: "hidden" }}>
                            <div style={{ height: "100%", width: `${pct}%`, background: barColor, borderRadius: 2 }} />
                          </div>
                        </div>
                        <div style={{ fontSize: 12, color: "rgba(223,207,196,0.5)" }}>{l.seuil_alerte_kg} kg</div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: l.marge_pct > 40 ? "#4ade80" : C.gold }}>{l.marge_pct}%</div>
                        <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)" }}>
                          {l.dlc ? new Date(l.dlc).toLocaleDateString("fr-FR", { month: "short", year: "2-digit" }) : "—"}
                        </div>
                      </div>
                    );
                  })
              }
            </div>
          </>
        )}

        {/* TAB FOURNISSEURS */}
        {tab === "fournisseurs" && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
            {loadingFourn
              ? [1,2,3].map(i => <div key={i} className="card" style={{ padding: 20 }}><Skeleton h={80} /></div>)
              : fournisseurs.length === 0
                ? <div style={{ padding: 32, color: "rgba(223,207,196,0.3)", fontSize: 13 }}>Aucun fournisseur enregistré</div>
                : fournisseurs.map(f => (
                  <div key={f.id} className="card" style={{ padding: 20 }}>
                    <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 15, marginBottom: 6 }}>{f.nom}</div>
                    <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", marginBottom: 12 }}>{f.pays} · délai ~{f.delai_moyen}j</div>
                    <div style={{ display: "flex", gap: 2, marginBottom: 10 }}>
                      {[1,2,3,4,5].map(s => <span key={s} style={{ fontSize: 14, color: s <= Math.round(f.score) ? C.gold : "rgba(223,207,196,0.15)" }}>★</span>)}
                      <span style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", marginLeft: 4 }}>{f.score}/5</span>
                    </div>
                    {f.email && <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)" }}>✉ {f.email}</div>}
                  </div>
                ))
            }
          </div>
        )}
      </div>

      {/* Panel détail lot */}
      {selected && (
        <div style={{ position: "fixed", right: 0, top: 0, width: 360, height: "100vh", background: C.espresso, borderLeft: "1px solid rgba(193,138,74,0.15)", padding: "28px 24px", overflowY: "auto", zIndex: 100 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <span style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 12, color: C.gold, textTransform: "uppercase", letterSpacing: 1 }}>Détail lot</span>
            <button onClick={() => setSelected(null)} style={{ background: "none", border: "none", color: "rgba(223,207,196,0.4)", cursor: "pointer", fontSize: 22 }}>×</button>
          </div>

          <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 18, marginBottom: 4 }}>{selected.origine}</div>
          <div style={{ fontFamily: "monospace", fontSize: 11, color: "rgba(223,207,196,0.4)", marginBottom: 20 }}>{selected.numero_lot}</div>

          {[
            { l: "Stock actuel", v: `${selected.stock_kg} kg`, c: selected.est_critique ? "#e8a0b8" : C.gold },
            { l: "Seuil d'alerte", v: `${selected.seuil_alerte_kg} kg` },
            { l: "Prix achat", v: `${selected.prix_achat_kg} €/kg` },
            { l: "Prix vente", v: `${selected.prix_vente_kg} €/kg` },
            { l: "Marge", v: `${selected.marge_pct}%`, c: selected.marge_pct > 40 ? "#4ade80" : C.gold },
            selected.dlc && { l: "DLC", v: new Date(selected.dlc).toLocaleDateString("fr-FR") },
          ].filter(Boolean).map((r, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid rgba(223,207,196,0.06)" }}>
              <span style={{ fontSize: 12, color: "rgba(223,207,196,0.4)" }}>{r.l}</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: r.c || C.creme }}>{r.v}</span>
            </div>
          ))}

          {selected.notes_degustation && (
            <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 14, margin: "16px 0" }}>
              <div style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.5 }}>Notes de dégustation</div>
              <div style={{ fontSize: 12, color: "rgba(223,207,196,0.6)", fontStyle: "italic", lineHeight: 1.7 }}>{selected.notes_degustation}</div>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 16 }}>
            <button className="btn-p" style={{ width: "100%", padding: 11 }}
              onClick={() => ajusterMutation.mutate({ id: selected.id, delta: -0.25, raison: "vente terrain" })}>
              - 250g (vente rapide)
            </button>
            <button className="btn-g" style={{ width: "100%", padding: 11 }}>✎ Modifier ce lot</button>
          </div>
        </div>
      )}

      {/* Modal nouveau lot */}
      {showAdd && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={() => setShowAdd(false)}>
          <div style={{ background: C.espresso, border: "1px solid rgba(193,138,74,0.2)", borderRadius: 20, padding: 32, width: 480, maxHeight: "90vh", overflowY: "auto" }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
              <h2 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 18 }}>Nouveau lot</h2>
              <button onClick={() => setShowAdd(false)} style={{ background: "none", border: "none", color: "rgba(223,207,196,0.4)", cursor: "pointer", fontSize: 22 }}>×</button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {[
                { key: "origine", label: "Origine (ex: Éthiopie Yirgacheffe)", placeholder: "Éthiopie Yirgacheffe" },
                { key: "stock_kg", label: "Stock (kg)", placeholder: "10", type: "number" },
                { key: "prix_achat_kg", label: "Prix achat (€/kg)", placeholder: "18", type: "number" },
                { key: "prix_vente_kg", label: "Prix vente (€/kg)", placeholder: "28", type: "number" },
                { key: "seuil_alerte_kg", label: "Seuil d'alerte (kg)", placeholder: "3", type: "number" },
                { key: "notes_degustation", label: "Notes de dégustation", placeholder: "Fruité, notes d'agrumes..." },
              ].map(f => (
                <div key={f.key}>
                  <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>{f.label}</label>
                  <input className="inp" type={f.type || "text"} placeholder={f.placeholder} value={newLot[f.key]} onChange={e => setNewLot(p => ({ ...p, [f.key]: e.target.value }))} />
                </div>
              ))}
              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Fournisseur</label>
                <select className="inp" value={newLot.fournisseur_id} onChange={e => setNewLot(p => ({ ...p, fournisseur_id: e.target.value }))}>
                  <option value="">— Sélectionner —</option>
                  {fournisseurs.map(f => <option key={f.id} value={f.id}>{f.nom}</option>)}
                </select>
              </div>
              <button
                className="btn-p"
                style={{ padding: 13, marginTop: 4, opacity: creerMutation.isPending ? 0.7 : 1 }}
                disabled={creerMutation.isPending}
                onClick={() => creerMutation.mutate({
                  ...newLot,
                  stock_kg: parseFloat(newLot.stock_kg),
                  prix_achat_kg: parseFloat(newLot.prix_achat_kg),
                  prix_vente_kg: parseFloat(newLot.prix_vente_kg),
                  seuil_alerte_kg: parseFloat(newLot.seuil_alerte_kg),
                  fournisseur_id: parseInt(newLot.fournisseur_id),
                  numero_lot: `LOT-${Date.now()}`,
                })}
              >
                {creerMutation.isPending ? "Création..." : "Créer le lot"}
              </button>
              {creerMutation.isError && <div style={{ fontSize: 12, color: "#e8a0b8" }}>Erreur lors de la création</div>}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
