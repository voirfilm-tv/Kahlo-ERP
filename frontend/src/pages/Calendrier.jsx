import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "../components/Layout";
import { getEvenements, creerEvenement, supprimerEvenement, getBilanMarche, syncCalendrier, extractError } from "../services/api";

const C = {
  espresso: "#261810", gold: "#C18A4A", prune: "#6B3F57",
  rose: "#B07A8B", creme: "#DFCFC4", dark: "#1a0f0a", card: "#2e1a10",
};

const TYPES = {
  marche:      { label: "Marché",      color: "#C18A4A", bg: "rgba(193,138,74,0.15)" },
  remise:      { label: "Remise",      color: "#4ade80", bg: "rgba(74,222,128,0.1)" },
  fournisseur: { label: "Fournisseur", color: "#B07A8B", bg: "rgba(176,122,139,0.15)" },
  perso:       { label: "Personnel",   color: "rgba(223,207,196,0.4)", bg: "rgba(223,207,196,0.06)" },
};

const JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
const MOIS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"];

function Skeleton({ h = 20 }) {
  return <div style={{ height: h, borderRadius: 6, background: "rgba(193,138,74,0.06)", animation: "pulse 1.5s infinite" }} />;
}

function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function daysInMonth(date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
}

export default function Calendrier() {
  const qc = useQueryClient();
  const [vue, setVue] = useState("mois");
  const [current, setCurrent] = useState(new Date());
  const [selected, setSelected] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newEvt, setNewEvt] = useState({ titre: "", type: "marche", date: "", heure_debut: "08:00", heure_fin: "18:00", lieu: "", notes: "" });
  const [toast, setToast] = useState(null);

  const debut = new Date(current.getFullYear(), current.getMonth(), 1);
  const fin   = new Date(current.getFullYear(), current.getMonth() + 1, 0);

  const { data: evenements = [], isLoading } = useQuery({
    queryKey: ["evenements", current.getFullYear(), current.getMonth()],
    queryFn: () => getEvenements({
      debut: debut.toISOString().slice(0, 10),
      fin:   fin.toISOString().slice(0, 10),
    }),
    refetchInterval: 60_000,
  });

  const { data: bilan, isLoading: loadingBilan } = useQuery({
    queryKey: ["bilan-marche", selected?.id],
    queryFn: () => getBilanMarche(selected.id),
    enabled: !!selected?.id && selected?.type === "marche",
  });

  const creerMutation = useMutation({
    mutationFn: creerEvenement,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["evenements"] }); setShowAdd(false); },
    onError: (err) => setToast({ ok: false, text: extractError(err, "Erreur lors de la création") }),
  });

  const supprimerMutation = useMutation({
    mutationFn: supprimerEvenement,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["evenements"] }); setSelected(null); },
    onError: (err) => setToast({ ok: false, text: extractError(err, "Erreur lors de la suppression") }),
  });

  const syncMutation = useMutation({
    mutationFn: syncCalendrier,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["evenements"] }); setToast({ ok: true, text: "Synchronisation effectuée" }); },
    onError: (err) => setToast({ ok: false, text: extractError(err, "Erreur de synchronisation") }),
  });

  const evtsByDate = {};
  evenements.forEach(e => {
    const k = e.date.slice(0, 10);
    if (!evtsByDate[k]) evtsByDate[k] = [];
    evtsByDate[k].push(e);
  });

  // Grille calendrier
  const firstDay = startOfMonth(current);
  const startDow = (firstDay.getDay() + 6) % 7; // lundi = 0
  const nbDays = daysInMonth(current);
  const cells = [];
  for (let i = 0; i < startDow; i++) cells.push(null);
  for (let d = 1; d <= nbDays; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  const today = new Date();
  const isToday = (d) => d && current.getFullYear() === today.getFullYear() && current.getMonth() === today.getMonth() && d === today.getDate();
  const dateKey = (d) => `${current.getFullYear()}-${String(current.getMonth()+1).padStart(2,"0")}-${String(d).padStart(2,"0")}`;

  const nextMonth  = () => setCurrent(new Date(current.getFullYear(), current.getMonth() + 1, 1));
  const prevMonth  = () => setCurrent(new Date(current.getFullYear(), current.getMonth() - 1, 1));

  const prochains = evenements
    .filter(e => new Date(e.date) >= today)
    .sort((a, b) => new Date(a.date) - new Date(b.date))
    .slice(0, 8);

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
        .day-cell { min-height: 80px; border-right: 1px solid rgba(193,138,74,0.06); border-bottom: 1px solid rgba(193,138,74,0.06); padding: 6px; cursor: pointer; transition: background 0.15s; }
        .day-cell:hover { background: rgba(193,138,74,0.03); }
        .tab-a { padding: 7px 16px; border-radius: 10px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid rgba(193,138,74,0.2); font-family: 'Outfit',sans-serif; background: rgba(193,138,74,0.12); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); color: ${C.gold}; box-shadow: inset 0 1px 0 rgba(255,255,255,0.04); transition: all 0.2s; }
        .tab-i { padding: 7px 16px; border-radius: 10px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid transparent; font-family: 'Outfit',sans-serif; background: transparent; color: rgba(223,207,196,0.4); transition: all 0.2s; }
        .tab-i:hover { background: rgba(193,138,74,0.05); }
      `}</style>

      <div style={{ padding: "32px 28px", fontFamily: "'Outfit', sans-serif", color: C.creme, marginRight: selected ? 380 : 0, transition: "margin-right 0.3s" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <div>
            <h1 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 24 }}>Calendrier</h1>
            <p style={{ color: "rgba(223,207,196,0.4)", fontSize: 13, marginTop: 3 }}>{evenements.length} événement(s) ce mois</p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn-g" onClick={() => syncMutation.mutate()} disabled={syncMutation.isPending}>
              {syncMutation.isPending ? "Sync..." : "↺ Synchroniser"}
            </button>
            <button className="btn-p" onClick={() => setShowAdd(true)}>+ Événement</button>
          </div>
        </div>

        {/* Toast */}
        {toast && (
          <div style={{ padding: "10px 16px", borderRadius: 12, marginBottom: 16, fontSize: 12, display: "flex", justifyContent: "space-between", alignItems: "center", background: toast.ok ? "rgba(74,222,128,0.08)" : "rgba(232,160,184,0.08)", color: toast.ok ? "#4ade80" : "#e8a0b8", border: `1px solid ${toast.ok ? "rgba(74,222,128,0.2)" : "rgba(232,160,184,0.2)"}` }}>
            <span>{toast.ok ? "✓" : "✗"} {toast.text}</span>
            <button onClick={() => setToast(null)} style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", fontSize: 16 }}>×</button>
          </div>
        )}

        {/* Navigation + Tabs */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <button onClick={prevMonth} style={{ background: "none", border: "1px solid rgba(193,138,74,0.2)", borderRadius: 8, padding: "6px 12px", color: C.gold, cursor: "pointer" }}>←</button>
            <span style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 16 }}>{MOIS_FR[current.getMonth()]} {current.getFullYear()}</span>
            <button onClick={nextMonth} style={{ background: "none", border: "1px solid rgba(193,138,74,0.2)", borderRadius: 8, padding: "6px 12px", color: C.gold, cursor: "pointer" }}>→</button>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button className={vue === "mois" ? "tab-a" : "tab-i"} onClick={() => setVue("mois")}>▦ Mois</button>
            <button className={vue === "liste" ? "tab-a" : "tab-i"} onClick={() => setVue("liste")}>≡ Liste</button>
          </div>
        </div>

        {/* VUE MOIS */}
        {vue === "mois" && (
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", background: "rgba(0,0,0,0.2)", borderBottom: "1px solid rgba(193,138,74,0.1)" }}>
              {JOURS.map(j => <div key={j} style={{ padding: "10px 6px", textAlign: "center", fontSize: 10, color: "rgba(223,207,196,0.35)", fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase" }}>{j}</div>)}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)" }}>
              {isLoading
                ? Array.from({ length: 35 }, (_, i) => <div key={i} className="day-cell"><Skeleton h={14} /></div>)
                : cells.map((d, i) => {
                  const k = d ? dateKey(d) : null;
                  const evts = k ? (evtsByDate[k] || []) : [];
                  return (
                    <div key={i} className="day-cell"
                      style={{ background: isToday(d) ? "rgba(193,138,74,0.06)" : "transparent" }}
                      onClick={() => { if (d) { setNewEvt(p => ({ ...p, date: k })); setShowAdd(true); } }}>
                      {d && (
                        <>
                          <div style={{ fontSize: 11, fontWeight: isToday(d) ? 700 : 400, color: isToday(d) ? C.gold : "rgba(223,207,196,0.5)", marginBottom: 4, textAlign: "right" }}>{d}</div>
                          {evts.slice(0, 3).map(e => (
                            <div key={e.id} onClick={ev => { ev.stopPropagation(); setSelected(e); }}
                              style={{ background: TYPES[e.type]?.bg || TYPES.perso.bg, color: TYPES[e.type]?.color || C.creme, borderRadius: 5, padding: "2px 6px", fontSize: 10, fontWeight: 600, marginBottom: 3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", cursor: "pointer" }}>
                              {e.titre}
                            </div>
                          ))}
                          {evts.length > 3 && <div style={{ fontSize: 9, color: "rgba(223,207,196,0.35)", textAlign: "center" }}>+{evts.length - 3}</div>}
                        </>
                      )}
                    </div>
                  );
                })
              }
            </div>
          </div>
        )}

        {/* VUE LISTE */}
        {vue === "liste" && (
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            {isLoading
              ? [1,2,3].map(i => <div key={i} style={{ padding: 18 }}><Skeleton h={20} /></div>)
              : prochains.length === 0
                ? <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "rgba(223,207,196,0.3)" }}>Aucun événement à venir</div>
                : prochains.map(e => {
                  const t = TYPES[e.type] || TYPES.perso;
                  return (
                    <div key={e.id} onClick={() => setSelected(selected?.id === e.id ? null : e)}
                      style={{ display: "flex", alignItems: "center", gap: 16, padding: "16px 20px", borderBottom: "1px solid rgba(223,207,196,0.05)", cursor: "pointer" }}>
                      <div style={{ width: 4, height: 36, borderRadius: 2, background: t.color, flexShrink: 0 }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>{e.titre}</div>
                        <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)" }}>
                          {new Date(e.date).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}
                          {e.lieu && ` · ${e.lieu}`}
                        </div>
                      </div>
                      <span style={{ background: t.bg, color: t.color, padding: "3px 10px", borderRadius: 20, fontSize: 10, fontWeight: 600 }}>{t.label}</span>
                    </div>
                  );
                })
            }
          </div>
        )}
      </div>

      {/* Panel détail */}
      {selected && (
        <div style={{ position: "fixed", right: 0, top: 0, width: 380, height: "100vh", background: C.espresso, borderLeft: "1px solid rgba(193,138,74,0.15)", padding: "28px 24px", overflowY: "auto", zIndex: 100 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
            <span style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 12, color: TYPES[selected.type]?.color || C.gold, textTransform: "uppercase", letterSpacing: 1 }}>
              {TYPES[selected.type]?.label || "Événement"}
            </span>
            <button onClick={() => setSelected(null)} style={{ background: "none", border: "none", color: "rgba(223,207,196,0.4)", cursor: "pointer", fontSize: 22 }}>×</button>
          </div>

          <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 20, marginBottom: 4 }}>{selected.titre}</div>
          <div style={{ fontSize: 13, color: "rgba(223,207,196,0.5)", marginBottom: 20 }}>
            {new Date(selected.date).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}
            {selected.lieu && <div style={{ marginTop: 4 }}>📍 {selected.lieu}</div>}
          </div>

          {selected.notes && (
            <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 14, marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: "rgba(223,207,196,0.6)", lineHeight: 1.7 }}>{selected.notes}</div>
            </div>
          )}

          {/* Bilan marché */}
          {selected.type === "marche" && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 12, color: C.gold, marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>Bilan du marché</div>
              {loadingBilan
                ? <Skeleton h={60} />
                : bilan
                  ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                      {[
                        { l: "CA réalisé", v: `${bilan.ca} €`, c: C.gold },
                        { l: "Kg vendus", v: `${bilan.kg_vendus} kg` },
                        { l: "Commandes", v: bilan.nb_commandes },
                        { l: "Taux écoulement", v: `${bilan.taux_ecoulement}%` },
                      ].map((r, i) => (
                        <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "9px 0", borderBottom: "1px solid rgba(223,207,196,0.06)" }}>
                          <span style={{ fontSize: 12, color: "rgba(223,207,196,0.4)" }}>{r.l}</span>
                          <span style={{ fontSize: 12, fontWeight: 700, color: r.c || C.creme }}>{r.v}</span>
                        </div>
                      ))}
                    </div>
                  )
                  : <div style={{ fontSize: 12, color: "rgba(223,207,196,0.3)" }}>Pas encore de bilan (marché à venir)</div>
              }
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <button className="btn-g" style={{ width: "100%", padding: 11 }}
              onClick={() => supprimerMutation.mutate(selected.id)}>
              🗑 Supprimer cet événement
            </button>
          </div>
        </div>
      )}

      {/* Modal nouvel événement */}
      {showAdd && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={() => setShowAdd(false)}>
          <div style={{ background: C.espresso, border: "1px solid rgba(193,138,74,0.2)", borderRadius: 20, padding: 32, width: 460 }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
              <h2 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 18 }}>Nouvel événement</h2>
              <button onClick={() => setShowAdd(false)} style={{ background: "none", border: "none", color: "rgba(223,207,196,0.4)", cursor: "pointer", fontSize: 22 }}>×</button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {[
                { key: "titre", label: "Titre *", placeholder: "Marché de la Croix-Rousse" },
                { key: "date", label: "Date *", type: "date" },
                { key: "lieu", label: "Lieu", placeholder: "Place de la Croix-Rousse" },
              ].map(f => (
                <div key={f.key}>
                  <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>{f.label}</label>
                  <input className="inp" type={f.type || "text"} placeholder={f.placeholder} value={newEvt[f.key]} onChange={e => setNewEvt(p => ({ ...p, [f.key]: e.target.value }))} />
                </div>
              ))}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {[{ key: "heure_debut", label: "Heure début", type: "time" }, { key: "heure_fin", label: "Heure fin", type: "time" }].map(f => (
                  <div key={f.key}>
                    <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>{f.label}</label>
                    <input className="inp" type="time" value={newEvt[f.key]} onChange={e => setNewEvt(p => ({ ...p, [f.key]: e.target.value }))} />
                  </div>
                ))}
              </div>
              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 }}>Type</label>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {Object.entries(TYPES).map(([k, v]) => (
                    <div key={k} onClick={() => setNewEvt(p => ({ ...p, type: k }))} style={{ padding: "7px 14px", borderRadius: 8, cursor: "pointer", fontSize: 12, fontWeight: 600, transition: "all 0.15s", background: newEvt.type === k ? v.bg : "rgba(0,0,0,0.2)", color: newEvt.type === k ? v.color : "rgba(223,207,196,0.4)", border: `1px solid ${newEvt.type === k ? v.color + "44" : "rgba(193,138,74,0.1)"}` }}>
                      {v.label}
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <label style={{ fontSize: 11, color: "rgba(223,207,196,0.4)", display: "block", marginBottom: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>Notes</label>
                <textarea className="inp" rows={2} style={{ resize: "none" }} value={newEvt.notes} onChange={e => setNewEvt(p => ({ ...p, notes: e.target.value }))} placeholder="Emplacement, matériel à prévoir..." />
              </div>
              <button
                className="btn-p" style={{ padding: 13, opacity: creerMutation.isPending ? 0.7 : 1 }}
                disabled={creerMutation.isPending || !newEvt.titre || !newEvt.date}
                onClick={() => creerMutation.mutate(newEvt)}
              >
                {creerMutation.isPending ? "Création..." : "Créer l'événement"}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
