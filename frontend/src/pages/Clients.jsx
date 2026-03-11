import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "../components/Layout";
import { getClients, creerClient, modifierClient, ajouterTampon, getAlertesCRM, extractError } from "../services/api";

const C = {
  espresso: "#261810", gold: "#C18A4A", prune: "#6B3F57",
  rose: "#B07A8B", creme: "#DFCFC4", dark: "#1a0f0a", card: "#2e1a10",
};

const PROFILS = {
  florale:      { emoji: "🌸", label: "Florale",      desc: "Notes florales et légères" },
  intense:      { emoji: "🔥", label: "Intense",      desc: "Torréfaction prononcée" },
  douce:        { emoji: "🍫", label: "Douce",        desc: "Rondeur et douceur" },
  aventuriere:  { emoji: "🌍", label: "Aventurière",  desc: "Origines rares et singulières" },
};

const MOUTURES = ["Grains entiers", "Filtre", "Expresso", "Cafetière italienne", "Chemex"];

function Skeleton({ h = 20, w = "100%" }) {
  return <div style={{ width: w, height: h, borderRadius: 6, background: "rgba(193,138,74,0.06)", animation: "pulse 1.5s infinite" }} />;
}

function initials(prenom, nom) {
  return `${prenom?.[0] || ""}${nom?.[0] || ""}`.toUpperCase();
}

export default function Clients() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState(null);
  const [tab, setTab] = useState("liste");
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [newClient, setNewClient] = useState({ prenom: "", nom: "", email: "", telephone: "", ville: "", profil: "florale", mouture_pref: "Grains entiers", quantite_hab_g: 250 });

  const { data: clients = [], isLoading } = useQuery({
    queryKey: ["clients"],
    queryFn: getClients,
  });

  const { data: alertes } = useQuery({
    queryKey: ["alertes-crm"],
    queryFn: getAlertesCRM,
  });

  const EMPTY_CLIENT = { prenom: "", nom: "", email: "", telephone: "", ville: "", profil: "florale", mouture_pref: "Grains entiers", quantite_hab_g: 250 };

  const creerMutation = useMutation({
    mutationFn: creerClient,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["clients"] }); setShowAdd(false); setNewClient(EMPTY_CLIENT); },
  });

  const tamponMutation = useMutation({
    mutationFn: ajouterTampon,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clients"] }),
  });

  const filtered = clients.filter(c =>
    `${c.prenom} ${c.nom} ${c.email} ${c.ville || ""}`.toLowerCase().includes(search.toLowerCase())
  );

  const anniversairesProches = clients.filter(c => {
    if (!c.anniversaire) return false;
    const today = new Date();
    const anniv = new Date(c.anniversaire);
    anniv.setFullYear(today.getFullYear());
    const diff = (anniv - today) / (1000 * 60 * 60 * 24);
    return diff >= 0 && diff <= 14;
  });

  const inactifs = clients.filter(c => {
    if (!c.commandes || c.commandes.length === 0) return false;
    const derniere = Math.max(...c.commandes.map(cmd => new Date(cmd.date_commande)));
    return (Date.now() - derniere) > 45 * 24 * 60 * 60 * 1000;
  });

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
        .btn-g { background: rgba(193,138,74,0.06); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); border: 1px solid rgba(193,138,74,0.15); border-radius: 12px; padding: 8px 16px; color: ${C.gold}; font-size: 12px; font-weight: 600; cursor: pointer; font-family: 'Outfit',sans-serif; box-shadow: inset 0 1px 0 rgba(255,255,255,0.03); transition: all 0.2s ease; }
        .btn-g:hover { background: rgba(193,138,74,0.12); border-color: rgba(193,138,74,0.3); }
        .client-row { display: flex; align-items: center; gap: 14px; padding: 13px 18px; border-bottom: 1px solid rgba(223,207,196,0.05); cursor: pointer; transition: background 0.15s; }
        .client-row:hover { background: rgba(193,138,74,0.04); }
        .client-row.active { background: rgba(193,138,74,0.08); border-left: 2px solid ${C.gold}; }
        .tab-a { padding: 7px 16px; border-radius: 10px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid rgba(193,138,74,0.2); font-family: 'Outfit',sans-serif; background: rgba(193,138,74,0.12); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); color: ${C.gold}; box-shadow: inset 0 1px 0 rgba(255,255,255,0.04); transition: all 0.2s; }
        .tab-i { padding: 7px 16px; border-radius: 10px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid transparent; font-family: 'Outfit',sans-serif; background: transparent; color: rgba(223,207,196,0.4); transition: all 0.2s; }
        .tab-i:hover { background: rgba(193,138,74,0.05); }
      `}</style>

      <div style={{ padding: "32px 28px", fontFamily: "'Outfit', sans-serif", color: C.creme, marginRight: selected ? 360 : 0, transition: "margin-right 0.3s" }}>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div>
            <h1 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 24 }}>Clients</h1>
            <p style={{ color: "rgba(223,207,196,0.4)", fontSize: 13, marginTop: 3 }}>
              {clients.length} client(s) · {clients.filter(c => c.vip).length} VIP
              {anniversairesProches.length > 0 && <span style={{ color: C.rose }}> · 🎂 {anniversairesProches.length} anniversaire(s) bientôt</span>}
            </p>
          </div>
          <button className="btn-p" onClick={() => setShowAdd(true)}>+ Nouveau client</button>
        </div>

        <div style={{ display: "flex", gap: 6, marginBottom: 18 }}>
          <button className={tab === "liste" ? "tab-a" : "tab-i"} onClick={() => setTab("liste")}>◎ Tous les clients</button>
          <button className={tab === "alertes" ? "tab-a" : "tab-i"} onClick={() => setTab("alertes")}>
            ⚡ Alertes {(anniversairesProches.length + inactifs.length) > 0 && <span style={{ background: C.rose, color: "white", borderRadius: 10, padding: "1px 7px", fontSize: 10, marginLeft: 4 }}>{anniversairesProches.length + inactifs.length}</span>}
          </button>
          <button className={tab === "fidelite" ? "tab-a" : "tab-i"} onClick={() => setTab("fidelite")}>☕ Fidélité</button>
        </div>

        {/* TAB LISTE */}
        {tab === "liste" && (
          <>
            <input className="inp" placeholder="🔍 Rechercher..." value={search} onChange={e => setSearch(e.target.value)} style={{ maxWidth: 320, marginBottom: 16 }} />
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              {isLoading
                ? [1,2,3,4].map(i => <div key={i} style={{ padding: "14px 18px", borderBottom: "1px solid rgba(223,207,196,0.05)" }}><Skeleton h={18} /></div>)
                : filtered.length === 0
                  ? <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "rgba(223,207,196,0.3)" }}>
                      {search ? "Aucun résultat" : "Aucun client — ajoutez-en un !"}
                    </div>
                  : filtered.map(c => {
                    const profil = PROFILS[c.profil];
                    return (
                      <div key={c.id} className={`client-row ${selected?.id === c.id ? "active" : ""}`} onClick={() => setSelected(selected?.id === c.id ? null : c)}>
                        <div style={{ width: 38, height: 38, borderRadius: "50%", background: `linear-gradient(135deg, ${C.prune}, ${C.rose})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700, flexShrink: 0 }}>
                          {initials(c.prenom, c.nom)}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                            <span style={{ fontSize: 13, fontWeight: 600 }}>{c.prenom} {c.nom}</span>
                            {c.vip && <span style={{ fontSize: 10, background: "rgba(193,138,74,0.15)", color: C.gold, borderRadius: 10, padding: "1px 8px", fontWeight: 600 }}>VIP</span>}
                            {profil && <span title={profil.label}>{profil.emoji}</span>}
                          </div>
                          <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)" }}>{c.ville || c.email || "—"}</div>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontSize: 13, fontWeight: 700, color: C.gold }}>{c.total_achats || 0} €</div>
                          <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)" }}>{c.nb_achats || 0} achat(s)</div>
                        </div>
                      </div>
                    );
                  })
              }
            </div>
          </>
        )}

        {/* TAB ALERTES */}
        {tab === "alertes" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {anniversairesProches.length > 0 && (
              <div className="card" style={{ padding: 20 }}>
                <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 13, color: C.rose, marginBottom: 14 }}>🎂 Anniversaires dans les 14 jours</div>
                {anniversairesProches.map(c => {
                  const anniv = new Date(c.anniversaire);
                  anniv.setFullYear(new Date().getFullYear());
                  const diff = Math.round((anniv - new Date()) / (1000 * 60 * 60 * 24));
                  return (
                    <div key={c.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid rgba(223,207,196,0.06)" }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{c.prenom} {c.nom}</div>
                        <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)" }}>Dans {diff} jour(s)</div>
                      </div>
                      <button className="btn-g" style={{ fontSize: 11, padding: "5px 12px" }}>✉ Email Brevo</button>
                    </div>
                  );
                })}
              </div>
            )}

            {inactifs.length > 0 && (
              <div className="card" style={{ padding: 20 }}>
                <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 13, color: C.gold, marginBottom: 14 }}>😴 Clients inactifs (+45 jours)</div>
                {inactifs.map(c => (
                  <div key={c.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid rgba(223,207,196,0.06)" }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{c.prenom} {c.nom}</div>
                    <button className="btn-g" style={{ fontSize: 11, padding: "5px 12px" }}>↩ Relancer</button>
                  </div>
                ))}
              </div>
            )}

            {anniversairesProches.length === 0 && inactifs.length === 0 && (
              <div style={{ textAlign: "center", padding: 48, color: "rgba(223,207,196,0.3)", fontSize: 14 }}>
                ✓ Aucune alerte client pour le moment
              </div>
            )}
          </div>
        )}

        {/* TAB FIDÉLITÉ */}
        {tab === "fidelite" && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
            {isLoading
              ? [1,2,3].map(i => <div key={i} className="card" style={{ padding: 20 }}><Skeleton h={100} /></div>)
              : [...clients].sort((a, b) => (b.tampons || 0) - (a.tampons || 0)).map(c => (
                <div key={c.id} className="card" style={{ padding: 20 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>{c.prenom} {c.nom}</div>
                      <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)" }}>{c.tampons || 0} / 10 tampons</div>
                    </div>
                    <button className="btn-g" style={{ fontSize: 11, padding: "4px 10px" }} onClick={() => tamponMutation.mutate(c.id)}>+ tampon</button>
                  </div>
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                    {Array.from({ length: 10 }, (_, i) => (
                      <span key={i} style={{ fontSize: 18, opacity: i < (c.tampons || 0) ? 1 : 0.15 }}>☕</span>
                    ))}
                  </div>
                  {(c.tampons || 0) >= 10 && (
                    <div style={{ marginTop: 10, fontSize: 12, color: "#4ade80", fontWeight: 600 }}>🎁 Récompense disponible !</div>
                  )}
                </div>
              ))
            }
          </div>
        )}
      </div>

      {/* Panel client */}
      {selected && (
        <div style={{ position: "fixed", right: 0, top: 0, width: 360, height: "100vh", background: C.espresso, borderLeft: "1px solid rgba(193,138,74,0.15)", padding: "28px 24px", overflowY: "auto", zIndex: 100 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
            <span style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 12, color: C.gold, textTransform: "uppercase", letterSpacing: 1 }}>Profil client</span>
            <button onClick={() => setSelected(null)} style={{ background: "none", border: "none", color: "rgba(223,207,196,0.4)", cursor: "pointer", fontSize: 22 }}>×</button>
          </div>
          <div style={{ textAlign: "center", marginBottom: 20 }}>
            <div style={{ width: 60, height: 60, borderRadius: "50%", background: `linear-gradient(135deg, ${C.prune}, ${C.rose})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 700, margin: "0 auto 10px" }}>
              {initials(selected.prenom, selected.nom)}
            </div>
            <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 18 }}>{selected.prenom} {selected.nom}</div>
            {selected.profil && <div style={{ fontSize: 12, color: C.rose, marginTop: 2 }}>{PROFILS[selected.profil]?.emoji} {PROFILS[selected.profil]?.label}</div>}
          </div>
          {[
            { l: "Email", v: selected.email },
            { l: "Téléphone", v: selected.telephone || "—" },
            { l: "Ville", v: selected.ville || "—" },
            { l: "Mouture préférée", v: selected.mouture_pref || "—" },
            { l: "Quantité habituelle", v: `${selected.quantite_hab_g || 250}g` },
            { l: "Total achats", v: `${selected.total_achats || 0} €`, c: C.gold },
            { l: "Tampons", v: `${selected.tampons || 0}/10` },
          ].map((r, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid rgba(223,207,196,0.06)" }}>
              <span style={{ fontSize: 12, color: "rgba(223,207,196,0.4)" }}>{r.l}</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: r.c || C.creme }}>{r.v}</span>
            </div>
          ))}
          {selected.notes && (
            <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 14, marginTop: 16 }}>
              <div style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.5 }}>Notes</div>
              <div style={{ fontSize: 12, color: "rgba(223,207,196,0.6)", fontStyle: "italic", lineHeight: 1.7 }}>{selected.notes}</div>
            </div>
          )}
        </div>
      )}

      {/* Modal nouveau client */}
      {showAdd && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={() => setShowAdd(false)}>
          <div style={{ background: C.espresso, border: "1px solid rgba(193,138,74,0.2)", borderRadius: 20, padding: 32, width: 480, maxHeight: "90vh", overflowY: "auto" }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
              <h2 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 18 }}>Nouveau client</h2>
              <button onClick={() => setShowAdd(false)} style={{ background: "none", border: "none", color: "rgba(223,207,196,0.4)", cursor: "pointer", fontSize: 22 }}>×</button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {[
                { key: "prenom", label: "Prénom *", placeholder: "Marie" },
                { key: "nom", label: "Nom *", placeholder: "Dupont" },
                { key: "email", label: "Email", placeholder: "marie@exemple.fr", type: "email" },
                { key: "telephone", label: "Téléphone", placeholder: "06 XX XX XX XX" },
                { key: "ville", label: "Ville", placeholder: "Lyon" },
              ].map(f => (
                <div key={f.key}>
                  <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>{f.label}</label>
                  <input className="inp" type={f.type || "text"} placeholder={f.placeholder} value={newClient[f.key]} onChange={e => setNewClient(p => ({ ...p, [f.key]: e.target.value }))} />
                </div>
              ))}
              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Profil Kahlo</label>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  {Object.entries(PROFILS).map(([k, v]) => (
                    <div key={k} onClick={() => setNewClient(p => ({ ...p, profil: k }))} style={{ padding: "10px 14px", borderRadius: 10, cursor: "pointer", border: `1px solid ${newClient.profil === k ? "rgba(193,138,74,0.4)" : "rgba(193,138,74,0.1)"}`, background: newClient.profil === k ? "rgba(193,138,74,0.12)" : "rgba(0,0,0,0.2)" }}>
                      <span style={{ fontSize: 16 }}>{v.emoji}</span>
                      <span style={{ fontSize: 12, fontWeight: 600, color: newClient.profil === k ? C.gold : C.creme, marginLeft: 6 }}>{v.label}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Mouture préférée</label>
                <select className="inp" value={newClient.mouture_pref} onChange={e => setNewClient(p => ({ ...p, mouture_pref: e.target.value }))}>
                  {MOUTURES.map(m => <option key={m}>{m}</option>)}
                </select>
              </div>
              <button
                className="btn-p" style={{ padding: 13, marginTop: 4, opacity: creerMutation.isPending ? 0.7 : 1 }}
                disabled={creerMutation.isPending || !newClient.prenom || !newClient.nom}
                onClick={() => creerMutation.mutate(newClient)}
              >
                {creerMutation.isPending ? "Création..." : "Créer le client"}
              </button>
              {creerMutation.isError && <div style={{ fontSize: 12, color: "#e8a0b8" }}>{extractError(creerMutation.error, "Erreur lors de la création du client")}</div>}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
