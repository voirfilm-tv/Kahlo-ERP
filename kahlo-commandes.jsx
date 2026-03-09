import { useState } from "react";

const COLORS = {
  espresso: "#261810",
  gold: "#C18A4A",
  prune: "#6B3F57",
  rose: "#B07A8B",
  creme: "#DFCFC4",
  dark: "#1a0f0a",
  card: "#2e1a10",
};

const STATUTS = {
  en_attente: { label: "En attente", color: COLORS.gold, bg: "rgba(193,138,74,0.12)" },
  prete: { label: "Prête", color: "#4ade80", bg: "rgba(74,222,128,0.1)" },
  remise: { label: "Remise", color: "rgba(223,207,196,0.4)", bg: "rgba(223,207,196,0.06)" },
  annulee: { label: "Annulée", color: "#e8a0b8", bg: "rgba(176,122,139,0.1)" },
};

const MOUTURES = ["Grains entiers", "Filtre", "Expresso", "Cafetière italienne", "Chemex"];

const commandes = [
  { id: "CMD-041", client: "Marie Dupont", email: "marie.dupont@gmail.com", tel: "06 12 34 56 78", produit: "Éthiopie Yirgacheffe", poids: 250, mouture: "Filtre", prix: 32, marche: "Croix-Rousse – 15 mars", statut: "prete", date_commande: "2026-03-02", date_remise: "2026-03-15", notes: "Habituelle, préfère le sac kraft", paiement: "sumup", sumup_id: "chk_3Nh2A..." },
  { id: "CMD-042", client: "Jean Martin", email: "jean.martin@orange.fr", tel: "07 98 76 54 32", produit: "Colombie Huila", poids: 500, mouture: "Expresso", prix: 28, marche: "Croix-Rousse – 15 mars", statut: "en_attente", date_commande: "2026-03-05", date_remise: "2026-03-15", notes: "Grains entiers svp", paiement: "sumup", sumup_id: "chk_3Nh3B..." },
  { id: "CMD-043", client: "Sophie Bernard", email: "s.bernard@proton.me", tel: "06 55 44 33 22", produit: "Kenya AA", poids: 250, mouture: "Filtre", prix: 36, marche: "Foire Bio – 22 mars", statut: "en_attente", date_commande: "2026-03-06", date_remise: "2026-03-22", notes: "", paiement: "sumup", sumup_id: "chk_3Nh4C..." },
  { id: "CMD-044", client: "Paul Lefebvre", email: "paul.lefebvre@sfr.fr", tel: "06 11 22 33 44", produit: "Guatemala Antigua", poids: 1000, mouture: "Grains entiers", prix: 27, marche: "Foire Bio – 22 mars", statut: "en_attente", date_commande: "2026-03-07", date_remise: "2026-03-22", notes: "Commande pour 1kg — client régulier", paiement: "sumup", sumup_id: "chk_3Nh5D..." },
  { id: "CMD-039", client: "Thomas Petit", email: "t.petit@gmail.com", tel: "06 77 88 99 00", produit: "Colombie Huila", poids: 500, mouture: "Expresso", prix: 28, marche: "Croix-Rousse – 1 mars", statut: "remise", date_commande: "2026-02-20", date_remise: "2026-03-01", notes: "", paiement: "sumup", sumup_id: "chk_3Nh1A..." },
  { id: "CMD-038", client: "Camille Rousseau", email: "camille.r@gmail.com", tel: "07 33 44 55 66", produit: "Éthiopie Yirgacheffe", poids: 250, mouture: "Filtre", prix: 32, marche: "Croix-Rousse – 1 mars", statut: "remise", date_commande: "2026-02-18", date_remise: "2026-03-01", notes: "", paiement: "especes", sumup_id: null },
  { id: "CMD-037", client: "Marc Dubois", email: "m.dubois@gmail.com", tel: "06 44 55 66 77", produit: "Kenya AA", poids: 500, mouture: "Chemex", prix: 36, marche: "Foire Bio – 22 fév", statut: "annulee", date_commande: "2026-02-10", date_remise: "2026-02-22", notes: "Client absent le jour J", paiement: "sumup", sumup_id: "chk_3Ng9Z..." },
];

const MARCHES_DISPO = [
  "Croix-Rousse – 15 mars",
  "Foire Bio – 22 mars",
  "Marché des Créateurs – 5 avril",
];

const ORIGINES = ["Éthiopie Yirgacheffe", "Colombie Huila", "Guatemala Antigua", "Brésil Cerrado", "Kenya AA"];

const PRIX = { "Éthiopie Yirgacheffe": 32, "Colombie Huila": 28, "Guatemala Antigua": 27, "Brésil Cerrado": 22, "Kenya AA": 36 };

export default function KahloCommandes() {
  const [selected, setSelected] = useState(null);
  const [filterStatut, setFilterStatut] = useState("tous");
  const [filterMarche, setFilterMarche] = useState("tous");
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [newOrigine, setNewOrigine] = useState("Éthiopie Yirgacheffe");
  const [newPoids, setNewPoids] = useState(250);
  const [tab, setTab] = useState("liste");

  const filtered = commandes.filter(c => {
    const matchS = filterStatut === "tous" || c.statut === filterStatut;
    const matchM = filterMarche === "tous" || c.marche === filterMarche;
    const matchQ = `${c.client} ${c.produit} ${c.id}`.toLowerCase().includes(search.toLowerCase());
    return matchS && matchM && matchQ;
  });

  const parMarche = MARCHES_DISPO.reduce((acc, m) => {
    acc[m] = commandes.filter(c => c.marche === m && c.statut !== "annulee");
    return acc;
  }, {});

  const stats = {
    total: commandes.filter(c => c.statut !== "annulee").length,
    pretes: commandes.filter(c => c.statut === "prete").length,
    en_attente: commandes.filter(c => c.statut === "en_attente").length,
    ca: commandes.filter(c => c.statut !== "annulee").reduce((a, c) => a + c.prix, 0),
  };

  const prixTotal = PRIX[newOrigine] ? Math.round((PRIX[newOrigine] / 250) * newPoids) : 0;

  return (
    <div style={{ minHeight: "100vh", background: COLORS.dark, fontFamily: "'Outfit', sans-serif", color: COLORS.creme, display: "flex" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=Raleway:wght@300;400;700;900&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: ${COLORS.prune}; border-radius: 2px; }
        .card { background: ${COLORS.card}; border: 1px solid rgba(193,138,74,0.12); border-radius: 16px; }
        .btn-p { background: linear-gradient(135deg, ${COLORS.prune}, ${COLORS.gold}); border: none; border-radius: 10px; padding: 10px 20px; color: white; font-size: 13px; font-weight: 600; cursor: pointer; font-family: 'Outfit', sans-serif; }
        .btn-g { background: rgba(193,138,74,0.08); border: 1px solid rgba(193,138,74,0.2); border-radius: 10px; padding: 8px 16px; color: ${COLORS.gold}; font-size: 12px; font-weight: 600; cursor: pointer; font-family: 'Outfit', sans-serif; }
        .btn-sm { border: none; border-radius: 8px; padding: 5px 11px; font-size: 11px; font-weight: 600; cursor: pointer; font-family: 'Outfit', sans-serif; transition: all 0.2s; }
        .row { display: flex; align-items: center; gap: 14px; padding: 13px 18px; border-bottom: 1px solid rgba(223,207,196,0.05); cursor: pointer; transition: background 0.15s; }
        .row:hover { background: rgba(193,138,74,0.05); }
        .row.active { background: rgba(193,138,74,0.08); border-left: 2px solid ${COLORS.gold}; }
        .inp { background: rgba(255,255,255,0.04); border: 1px solid rgba(193,138,74,0.15); border-radius: 10px; padding: 9px 14px; color: ${COLORS.creme}; font-size: 13px; font-family: 'Outfit', sans-serif; outline: none; width: 100%; }
        .inp:focus { border-color: rgba(193,138,74,0.4); }
        .tab-a { padding: 7px 16px; border-radius: 8px; font-size: 12px; font-weight: 500; cursor: pointer; border: none; font-family: 'Outfit', sans-serif; background: rgba(193,138,74,0.15); color: ${COLORS.gold}; }
        .tab-i { padding: 7px 16px; border-radius: 8px; font-size: 12px; font-weight: 500; cursor: pointer; border: none; font-family: 'Outfit', sans-serif; background: transparent; color: rgba(223,207,196,0.4); }
        .tab-i:hover { color: ${COLORS.creme}; }
        .nav-i { display: flex; align-items: center; gap: 10px; padding: 10px 16px; border-radius: 10px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s; margin-bottom: 2px; }
        .row-d { display: flex; justify-content: space-between; padding-bottom: 10px; border-bottom: 1px solid rgba(223,207,196,0.06); }
        .poids-btn { background: rgba(193,138,74,0.08); border: 1px solid rgba(193,138,74,0.15); border-radius: 8px; padding: 8px 16px; color: ${COLORS.gold}; font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .poids-btn.sel { background: rgba(193,138,74,0.2); border-color: ${COLORS.gold}; }
        .step { width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; }
        .step-done { background: rgba(74,222,128,0.15); color: #4ade80; border: 1px solid rgba(74,222,128,0.3); }
        .step-active { background: rgba(193,138,74,0.2); color: ${COLORS.gold}; border: 1px solid rgba(193,138,74,0.4); }
        .step-todo { background: rgba(223,207,196,0.06); color: rgba(223,207,196,0.3); border: 1px solid rgba(223,207,196,0.1); }
      `}</style>

      {/* Sidebar */}
      <div style={{ width: 220, background: COLORS.espresso, borderRight: `1px solid rgba(193,138,74,0.1)`, display: "flex", flexDirection: "column", padding: "24px 12px", position: "fixed", height: "100vh", zIndex: 10 }}>
        <div style={{ padding: "0 8px 28px", borderBottom: `1px solid rgba(193,138,74,0.1)`, marginBottom: 20 }}>
          <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 20, color: COLORS.gold, letterSpacing: 1 }}>KAHLO</div>
          <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 300, fontSize: 11, color: COLORS.rose, letterSpacing: 4, marginTop: 1 }}>CAFÉ · ERP</div>
        </div>
        <nav style={{ flex: 1 }}>
          {[
            { id: "dashboard", icon: "◈", label: "Dashboard" },
            { id: "marches", icon: "⊡", label: "Marchés" },
            { id: "stock", icon: "◉", label: "Stock" },
            { id: "crm", icon: "◎", label: "Clients" },
            { id: "commandes", icon: "◫", label: "Commandes", active: true },
            { id: "fournisseurs", icon: "◧", label: "Fournisseurs" },
            { id: "calendrier", icon: "▦", label: "Calendrier" },
            { id: "analytics", icon: "◬", label: "Analytics" },
          ].map(item => (
            <div key={item.id} className="nav-i" style={{ color: item.active ? COLORS.gold : "rgba(223,207,196,0.4)", background: item.active ? "rgba(193,138,74,0.12)" : "transparent" }}>
              <span style={{ fontSize: 14 }}>{item.icon}</span>{item.label}
            </div>
          ))}
        </nav>
        <div style={{ borderTop: `1px solid rgba(193,138,74,0.1)`, paddingTop: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px" }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", background: `linear-gradient(135deg, ${COLORS.prune}, ${COLORS.rose})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700 }}>K</div>
            <div>
              <div style={{ fontSize: 12, fontWeight: 600 }}>Kahlo Café</div>
              <div style={{ fontSize: 10, color: COLORS.rose }}>Lyon, FR</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div style={{ marginLeft: 220, flex: 1, padding: "32px 28px", marginRight: selected ? 380 : 0, transition: "margin-right 0.3s" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div>
            <h1 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 24, color: COLORS.creme }}>Commandes</h1>
            <p style={{ color: "rgba(223,207,196,0.4)", fontSize: 13, marginTop: 3 }}>
              {stats.en_attente} en attente · {stats.pretes} prêtes · {stats.ca} € engagés
            </p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn-g">⬇ Exporter</button>
            <button className="btn-p" onClick={() => setShowAdd(true)}>+ Nouvelle commande</button>
          </div>
        </div>

        {/* KPIs */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 22 }}>
          {[
            { label: "Total actives", value: stats.total, sub: "Hors annulées" },
            { label: "En attente", value: stats.en_attente, sub: "À préparer", alert: stats.en_attente > 0 },
            { label: "Prêtes", value: stats.pretes, sub: "À remettre", ok: stats.pretes > 0 },
            { label: "CA engagé", value: `${stats.ca} €`, sub: "Commandes actives" },
          ].map((k, i) => (
            <div key={i} className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>{k.label}</div>
              <div style={{ fontSize: 26, fontFamily: "'Raleway', sans-serif", fontWeight: 700, color: k.alert ? COLORS.gold : k.ok ? "#4ade80" : COLORS.gold, marginBottom: 4 }}>{k.value}</div>
              <div style={{ fontSize: 11, color: "rgba(223,207,196,0.3)" }}>{k.sub}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 6, marginBottom: 18 }}>
          {[
            { id: "liste", label: "◫ Toutes les commandes" },
            { id: "marche", label: "🏪 Par marché" },
          ].map(t => (
            <button key={t.id} className={tab === t.id ? "tab-a" : "tab-i"} onClick={() => setTab(t.id)}>{t.label}</button>
          ))}
        </div>

        {/* TAB LISTE */}
        {tab === "liste" && (
          <>
            {/* Filtres */}
            <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
              <input className="inp" placeholder="🔍 Client, produit, n° commande..." value={search} onChange={e => setSearch(e.target.value)} style={{ maxWidth: 280 }} />
              <select className="inp" style={{ maxWidth: 160 }} value={filterStatut} onChange={e => setFilterStatut(e.target.value)}>
                <option value="tous">Tous les statuts</option>
                {Object.entries(STATUTS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
              <select className="inp" style={{ maxWidth: 220 }} value={filterMarche} onChange={e => setFilterMarche(e.target.value)}>
                <option value="tous">Tous les marchés</option>
                {MARCHES_DISPO.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>

            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              {/* Header tableau */}
              <div style={{ display: "grid", gridTemplateColumns: "100px 1fr 1fr 130px 100px 80px 110px", gap: 8, padding: "12px 18px", background: "rgba(0,0,0,0.2)", borderBottom: `1px solid rgba(193,138,74,0.1)` }}>
                {["N°", "Client", "Produit", "Marché remise", "Montant", "Statut", "Actions"].map(h => (
                  <div key={h} style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase" }}>{h}</div>
                ))}
              </div>

              {filtered.map(c => {
                const s = STATUTS[c.statut];
                return (
                  <div key={c.id} className={`row ${selected?.id === c.id ? "active" : ""}`} onClick={() => setSelected(selected?.id === c.id ? null : c)}
                    style={{ display: "grid", gridTemplateColumns: "100px 1fr 1fr 130px 100px 80px 110px", gap: 8, alignItems: "center" }}>
                    <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)", fontFamily: "monospace" }}>{c.id}</div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>{c.client}</div>
                      <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)" }}>{c.email}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 500 }}>{c.produit}</div>
                      <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)" }}>{c.poids}g · {c.mouture}</div>
                    </div>
                    <div style={{ fontSize: 11, color: "rgba(223,207,196,0.5)" }}>{c.marche}</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.gold }}>{c.prix} €</div>
                    <div>
                      <span style={{ background: s.bg, color: s.color, padding: "3px 9px", borderRadius: 20, fontSize: 10, fontWeight: 600 }}>{s.label}</span>
                    </div>
                    <div style={{ display: "flex", gap: 5 }} onClick={e => e.stopPropagation()}>
                      {c.statut === "en_attente" && (
                        <button className="btn-sm" style={{ background: "rgba(74,222,128,0.1)", color: "#4ade80", border: "1px solid rgba(74,222,128,0.2)" }}>✓ Prête</button>
                      )}
                      {c.statut === "prete" && (
                        <button className="btn-sm" style={{ background: "rgba(193,138,74,0.1)", color: COLORS.gold, border: `1px solid rgba(193,138,74,0.2)` }}>📱 Notif</button>
                      )}
                      {c.statut === "remise" && (
                        <button className="btn-sm" style={{ background: "rgba(223,207,196,0.06)", color: "rgba(223,207,196,0.4)", border: "1px solid rgba(223,207,196,0.1)" }}>🧾 Facture</button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* TAB PAR MARCHÉ */}
        {tab === "marche" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {MARCHES_DISPO.map(marche => {
              const cmds = parMarche[marche] || [];
              const caMarche = cmds.reduce((a, c) => a + c.prix, 0);
              const nPret = cmds.filter(c => c.statut === "prete").length;
              return (
                <div key={marche} className="card" style={{ padding: 0, overflow: "hidden" }}>
                  {/* Header marché */}
                  <div style={{ padding: "16px 20px", background: "rgba(0,0,0,0.2)", borderBottom: `1px solid rgba(193,138,74,0.1)`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <span style={{ fontSize: 16 }}>🏪</span>
                      <div>
                        <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 15, color: COLORS.creme }}>{marche}</div>
                        <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", marginTop: 2 }}>{cmds.length} commande(s) · {caMarche} € · {nPret}/{cmds.length} prête(s)</div>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button className="btn-g" style={{ fontSize: 11, padding: "6px 14px" }}>📋 Checklist</button>
                      <button className="btn-p" style={{ fontSize: 11, padding: "6px 14px" }}>📱 Notifier tous</button>
                    </div>
                  </div>

                  {/* Barre de progression prêtes */}
                  <div style={{ height: 3, background: "rgba(223,207,196,0.06)" }}>
                    <div style={{ height: "100%", width: cmds.length ? `${(nPret / cmds.length) * 100}%` : "0%", background: `linear-gradient(90deg, ${COLORS.prune}, #4ade80)`, transition: "width 0.5s" }} />
                  </div>

                  {cmds.length === 0
                    ? <div style={{ padding: 20, textAlign: "center", fontSize: 13, color: "rgba(223,207,196,0.3)" }}>Aucune commande pour ce marché</div>
                    : cmds.map(c => {
                      const s = STATUTS[c.statut];
                      return (
                        <div key={c.id} className="row" style={{ display: "flex", alignItems: "center" }} onClick={() => setSelected(selected?.id === c.id ? null : c)}>
                          <div style={{ width: 36, height: 36, borderRadius: "50%", background: `linear-gradient(135deg, ${COLORS.prune}, ${COLORS.rose})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, flexShrink: 0 }}>
                            {c.client.split(" ").map(n => n[0]).join("")}
                          </div>
                          <div style={{ flex: 1, marginLeft: 12 }}>
                            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>{c.client}</div>
                            <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)" }}>{c.produit} · {c.poids}g · {c.mouture}</div>
                          </div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: COLORS.gold, marginRight: 16 }}>{c.prix} €</div>
                          <span style={{ background: s.bg, color: s.color, padding: "3px 10px", borderRadius: 20, fontSize: 10, fontWeight: 600, marginRight: 12 }}>{s.label}</span>
                          <div style={{ display: "flex", gap: 6 }} onClick={e => e.stopPropagation()}>
                            {c.statut === "en_attente" && <button className="btn-sm" style={{ background: "rgba(74,222,128,0.1)", color: "#4ade80", border: "1px solid rgba(74,222,128,0.2)" }}>✓ Prête</button>}
                            {c.statut === "prete" && <button className="btn-sm" style={{ background: "rgba(193,138,74,0.1)", color: COLORS.gold, border: `1px solid rgba(193,138,74,0.2)` }}>📱 Notifier</button>}
                          </div>
                        </div>
                      );
                    })
                  }
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Panel détail commande */}
      {selected && (
        <div style={{ position: "fixed", right: 0, top: 0, width: 380, height: "100vh", background: COLORS.espresso, borderLeft: `1px solid rgba(193,138,74,0.15)`, padding: "28px 24px", overflowY: "auto", zIndex: 100 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
            <span style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 12, color: COLORS.gold, textTransform: "uppercase", letterSpacing: 1 }}>Détail commande</span>
            <button onClick={() => setSelected(null)} style={{ background: "none", border: "none", color: "rgba(223,207,196,0.4)", cursor: "pointer", fontSize: 22 }}>×</button>
          </div>

          {/* ID + statut */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
            <div>
              <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 17, color: COLORS.creme }}>{selected.client}</div>
              <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)", fontFamily: "monospace", marginTop: 2 }}>{selected.id}</div>
            </div>
            <span style={{ background: STATUTS[selected.statut].bg, color: STATUTS[selected.statut].color, padding: "5px 14px", borderRadius: 20, fontSize: 12, fontWeight: 600 }}>{STATUTS[selected.statut].label}</span>
          </div>

          {/* Timeline statut */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 22, padding: "12px 16px", background: "rgba(0,0,0,0.2)", borderRadius: 12 }}>
            {[
              { label: "Commande", done: true },
              { label: "Préparation", done: selected.statut !== "en_attente" },
              { label: "Prête", done: selected.statut === "prete" || selected.statut === "remise" },
              { label: "Remise", done: selected.statut === "remise" },
            ].map((step, i, arr) => (
              <div key={i} style={{ display: "flex", alignItems: "center", flex: 1 }}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                  <div className={`step ${step.done ? "step-done" : i === arr.findIndex(s => !s.done) ? "step-active" : "step-todo"}`}>
                    {step.done ? "✓" : i + 1}
                  </div>
                  <div style={{ fontSize: 9, color: step.done ? "#4ade80" : "rgba(223,207,196,0.3)", whiteSpace: "nowrap" }}>{step.label}</div>
                </div>
                {i < arr.length - 1 && (
                  <div style={{ flex: 1, height: 1, background: step.done ? "rgba(74,222,128,0.3)" : "rgba(223,207,196,0.08)", margin: "0 4px", marginBottom: 14 }} />
                )}
              </div>
            ))}
          </div>

          {/* Infos */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
            {[
              { l: "Produit", v: selected.produit },
              { l: "Poids", v: `${selected.poids}g` },
              { l: "Mouture", v: selected.mouture },
              { l: "Montant", v: `${selected.prix} €`, c: COLORS.gold },
              { l: "Marché de remise", v: selected.marche },
              { l: "Date commande", v: selected.date_commande },
              { l: "Date remise prévue", v: selected.date_remise },
              { l: "Paiement", v: selected.paiement === "sumup" ? "SumUp ✓" : "Espèces", c: selected.paiement === "sumup" ? "#4ade80" : COLORS.creme },
              selected.sumup_id && { l: "SumUp ID", v: selected.sumup_id, small: true },
            ].filter(Boolean).map((r, i) => (
              <div key={i} className="row-d">
                <span style={{ fontSize: 12, color: "rgba(223,207,196,0.4)" }}>{r.l}</span>
                <span style={{ fontSize: r.small ? 10 : 12, fontWeight: r.small ? 400 : 600, color: r.c || COLORS.creme, fontFamily: r.small ? "monospace" : "inherit" }}>{r.v}</span>
              </div>
            ))}
          </div>

          {/* Contact */}
          <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 14, marginBottom: 20 }}>
            <div style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 10 }}>Contact client</div>
            <div style={{ fontSize: 12, color: "rgba(223,207,196,0.6)", marginBottom: 6 }}>✉ {selected.email}</div>
            <div style={{ fontSize: 12, color: "rgba(223,207,196,0.6)" }}>📱 {selected.tel}</div>
          </div>

          {selected.notes && (
            <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 14, marginBottom: 20 }}>
              <div style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 }}>Notes</div>
              <div style={{ fontSize: 12, color: "rgba(223,207,196,0.6)", fontStyle: "italic", lineHeight: 1.7 }}>{selected.notes}</div>
            </div>
          )}

          {/* Actions selon statut */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {selected.statut === "en_attente" && <>
              <button className="btn-p" style={{ width: "100%", padding: 11 }}>✓ Marquer comme prête</button>
              <button className="btn-g" style={{ width: "100%", padding: 11 }}>📱 Notifier le client</button>
            </>}
            {selected.statut === "prete" && <>
              <button className="btn-p" style={{ width: "100%", padding: 11 }}>📱 Notifier — commande prête</button>
              <button className="btn-g" style={{ width: "100%", padding: 11 }}>✓ Marquer comme remise</button>
            </>}
            {selected.statut === "remise" && <>
              <button className="btn-g" style={{ width: "100%", padding: 11 }}>🧾 Télécharger la facture PDF</button>
              <button className="btn-g" style={{ width: "100%", padding: 11 }}>👤 Voir le profil client</button>
            </>}
            {selected.statut === "annulee" && <>
              <button className="btn-g" style={{ width: "100%", padding: 11 }}>↺ Recréer la commande</button>
            </>}
            <button className="btn-g" style={{ width: "100%", padding: 11 }}>✎ Modifier</button>
          </div>
        </div>
      )}

      {/* Modal nouvelle commande */}
      {showAdd && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={() => setShowAdd(false)}>
          <div style={{ background: COLORS.espresso, border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 20, padding: 32, width: 500, maxHeight: "90vh", overflowY: "auto" }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 26 }}>
              <h2 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 18 }}>Nouvelle commande</h2>
              <button onClick={() => setShowAdd(false)} style={{ background: "none", border: "none", color: "rgba(223,207,196,0.4)", cursor: "pointer", fontSize: 22 }}>×</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              {/* Client */}
              <div>
                <div style={{ fontSize: 10, color: "rgba(223,207,196,0.4)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Client</div>
                <input className="inp" placeholder="Nom du client ou rechercher..." />
              </div>

              {/* Origine */}
              <div>
                <div style={{ fontSize: 10, color: "rgba(223,207,196,0.4)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Origine</div>
                <select className="inp" value={newOrigine} onChange={e => setNewOrigine(e.target.value)}>
                  {ORIGINES.map(o => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>

              {/* Poids */}
              <div>
                <div style={{ fontSize: 10, color: "rgba(223,207,196,0.4)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Poids</div>
                <div style={{ display: "flex", gap: 8 }}>
                  {[250, 500, 1000].map(p => (
                    <button key={p} className={`poids-btn ${newPoids === p ? "sel" : ""}`} onClick={() => setNewPoids(p)}>{p}g</button>
                  ))}
                </div>
              </div>

              {/* Mouture */}
              <div>
                <div style={{ fontSize: 10, color: "rgba(223,207,196,0.4)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Mouture</div>
                <select className="inp">
                  {MOUTURES.map(m => <option key={m}>{m}</option>)}
                </select>
              </div>

              {/* Marché */}
              <div>
                <div style={{ fontSize: 10, color: "rgba(223,207,196,0.4)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Marché de remise</div>
                <select className="inp">
                  {MARCHES_DISPO.map(m => <option key={m}>{m}</option>)}
                </select>
              </div>

              {/* Prix calculé */}
              <div style={{ background: `linear-gradient(135deg, rgba(107,63,87,0.3), rgba(193,138,74,0.1))`, border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 12, padding: "14px 18px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", marginBottom: 3 }}>Prix calculé automatiquement</div>
                  <div style={{ fontSize: 12, color: "rgba(223,207,196,0.6)" }}>{newOrigine} · {newPoids}g</div>
                </div>
                <div style={{ fontSize: 28, fontFamily: "'Raleway', sans-serif", fontWeight: 900, color: COLORS.gold }}>{prixTotal} €</div>
              </div>

              {/* Notes */}
              <div>
                <div style={{ fontSize: 10, color: "rgba(223,207,196,0.4)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Notes</div>
                <textarea className="inp" placeholder="Instructions particulières, préférences..." rows={2} style={{ resize: "none" }} />
              </div>

              {/* Paiement */}
              <div>
                <div style={{ fontSize: 10, color: "rgba(223,207,196,0.4)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Mode de paiement</div>
                <div style={{ display: "flex", gap: 8 }}>
                  {[
                    { id: "sumup", label: "💳 SumUp (lien de paiement)" },
                    { id: "especes", label: "💶 Espèces sur place" },
                  ].map(p => (
                    <div key={p.id} style={{ flex: 1, background: "rgba(0,0,0,0.2)", border: "1px solid rgba(193,138,74,0.15)", borderRadius: 10, padding: "10px 14px", cursor: "pointer", fontSize: 12, color: "rgba(223,207,196,0.6)", textAlign: "center" }}>{p.label}</div>
                  ))}
                </div>
              </div>

              <button className="btn-p" style={{ padding: 14, fontSize: 14, marginTop: 4 }}>Créer la commande</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
