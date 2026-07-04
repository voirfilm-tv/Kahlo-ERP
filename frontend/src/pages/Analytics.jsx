import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import Layout from "../components/Layout";
import { getAnalyticsGeneral, getAnalyticsMarches, getAnalyticsOrigines, getAnalyticsClients, getAnalyseIA, getStatutSumUp, getVentesSumUp, syncVentesSumUp, extractError } from "../services/api";
import { useQueryClient } from "@tanstack/react-query";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";

const C = {
  espresso: "#261810", gold: "#C18A4A", prune: "#6B3F57",
  rose: "#B07A8B", creme: "#DFCFC4", dark: "#1a0f0a", card: "#2e1a10",
};

const PALETTE = [C.gold, C.prune, C.rose, "#8fbc8f", "#deb887", "#6495ed"];

function Skeleton({ h = 20, w = "100%" }) {
  return <div style={{ width: w, height: h, borderRadius: 6, background: "rgba(193,138,74,0.06)", animation: "pulse 1.5s infinite" }} />;
}

const MOIS_FR = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"];

export default function Analytics() {
  const [tab, setTab] = useState("general");
  const [periode, setPeriode] = useState("12");
  const [iaResult, setIaResult] = useState(null);

  const { data: general, isLoading: lgn } = useQuery({
    queryKey: ["analytics-general", periode],
    queryFn: () => getAnalyticsGeneral({ mois: parseInt(periode) }),
    enabled: tab === "general",
  });

  const { data: marches, isLoading: lmr } = useQuery({
    queryKey: ["analytics-marches"],
    queryFn: getAnalyticsMarches,
    enabled: tab === "marches",
  });

  const { data: origines, isLoading: lor } = useQuery({
    queryKey: ["analytics-origines"],
    queryFn: getAnalyticsOrigines,
    enabled: tab === "origines",
  });

  const { data: clients, isLoading: lcl } = useQuery({
    queryKey: ["analytics-clients"],
    queryFn: getAnalyticsClients,
    enabled: tab === "clients",
  });

  const iaMutation = useMutation({
    mutationFn: getAnalyseIA,
    onSuccess: (data) => setIaResult(data?.analyse || "Analyse indisponible."),
    onError: (err) => setIaResult(`Erreur : ${extractError(err, "Impossible d'obtenir l'analyse IA")}`),
  });

  const caData = (general?.ca_mensuel || []).map(r => ({
    mois: MOIS_FR[(r.mois || 1) - 1],
    ca: r.ca,
  }));

  const originesData = (general?.top_origines || []).map(o => ({
    name: o.origine,
    value: o.ca,
  }));

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
        .tab-a { padding: 8px 18px; border-radius: 10px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid rgba(193,138,74,0.2); font-family: 'Outfit',sans-serif; background: rgba(193,138,74,0.12); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); color: ${C.gold}; box-shadow: inset 0 1px 0 rgba(255,255,255,0.04); transition: all 0.2s; }
        .tab-i { padding: 8px 18px; border-radius: 10px; font-size: 12px; font-weight: 500; cursor: pointer; border: 1px solid transparent; font-family: 'Outfit',sans-serif; background: transparent; color: rgba(223,207,196,0.4); transition: all 0.2s; }
        .tab-i:hover { background: rgba(193,138,74,0.05); }
        .kpi { background: rgba(46,26,16,0.55); backdrop-filter: blur(20px) saturate(180%); -webkit-backdrop-filter: blur(20px) saturate(180%); border: 1px solid rgba(193,138,74,0.12); border-radius: 16px; padding: 18px; box-shadow: 0 4px 24px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.04); transition: transform 0.2s ease; }
        .kpi:hover { transform: translateY(-1px); }
      `}</style>

      <div style={{ padding: "32px 28px", fontFamily: "'Outfit', sans-serif", color: C.creme }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <h1 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 24 }}>Analytics</h1>
          <div style={{ display: "flex", gap: 10 }}>
            <select value={periode} onChange={e => setPeriode(e.target.value)} style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(193,138,74,0.15)", borderRadius: 10, padding: "8px 14px", color: C.creme, fontFamily: "'Outfit', sans-serif", fontSize: 12, outline: "none" }}>
              <option value="3">3 derniers mois</option>
              <option value="6">6 derniers mois</option>
              <option value="12">12 derniers mois</option>
            </select>
            <button
              onClick={() => iaMutation.mutate()}
              disabled={iaMutation.isPending}
              style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "8px 18px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}
            >
              {iaMutation.isPending ? "..." : "✦ Analyser"}
            </button>
          </div>
        </div>

        {/* Bloc IA */}
        {iaResult && (
          <div style={{ background: "linear-gradient(135deg, rgba(107,63,87,0.2), rgba(193,138,74,0.07))", border: "1px solid rgba(193,138,74,0.2)", borderRadius: 14, padding: "16px 20px", marginBottom: 24, display: "flex", gap: 14 }}>
            <div style={{ width: 30, height: 30, borderRadius: "50%", background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, flexShrink: 0 }}>✦</div>
            <div style={{ fontSize: 13, color: "rgba(223,207,196,0.8)", lineHeight: 1.8 }}>{iaResult}</div>
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: "flex", gap: 6, marginBottom: 24 }}>
          {[["general","◈ Général"],["marches","▦ Marchés"],["origines","◉ Origines"],["clients","◎ Clients"],["sumup","💳 SumUp"]].map(([k, l]) => (
            <button key={k} className={tab === k ? "tab-a" : "tab-i"} onClick={() => setTab(k)}>{l}</button>
          ))}
        </div>

        {/* TAB SUMUP — ventes réelles importées via l'API */}
        {tab === "sumup" && <TabSumUp />}

        {/* TAB GÉNÉRAL */}
        {tab === "general" && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 22 }}>
              {[
                { label: "CA total période", value: general ? `${general.ca_total?.toLocaleString("fr")} €` : null },
                { label: "Commandes totales", value: general?.nb_commandes },
                { label: "Panier moyen", value: general ? `${general.panier_moyen} €` : null },
                { label: "Clients actifs", value: general?.clients_actifs },
              ].map((k, i) => (
                <div key={i} className="kpi">
                  <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>{k.label}</div>
                  {lgn ? <Skeleton h={26} w="60%" /> : <div style={{ fontSize: 24, fontFamily: "'Raleway', sans-serif", fontWeight: 700, color: C.gold }}>{k.value ?? "—"}</div>}
                </div>
              ))}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 18 }}>
              <div className="card" style={{ padding: 20 }}>
                <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 13, marginBottom: 16 }}>Évolution du CA</div>
                {lgn ? <Skeleton h={180} /> : caData.length === 0
                  ? <div style={{ height: 180, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: "rgba(223,207,196,0.3)" }}>Pas encore de données</div>
                  : (
                    <ResponsiveContainer width="100%" height={180}>
                      <AreaChart data={caData}>
                        <defs>
                          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={C.gold} stopOpacity={0.3} />
                            <stop offset="95%" stopColor={C.gold} stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="mois" tick={{ fill: "rgba(223,207,196,0.3)", fontSize: 10 }} axisLine={false} tickLine={false} />
                        <YAxis hide />
                        <Tooltip contentStyle={{ background: C.espresso, border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 8, fontSize: 12 }} formatter={(v) => [`${v} €`, "CA"]} />
                        <Area type="monotone" dataKey="ca" stroke={C.gold} strokeWidth={2} fill="url(#grad)" dot={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  )
                }
              </div>
              <div className="card" style={{ padding: 20 }}>
                <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 13, marginBottom: 16 }}>CA par origine</div>
                {lgn ? <Skeleton h={180} /> : originesData.length === 0
                  ? <div style={{ height: 180, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: "rgba(223,207,196,0.3)" }}>Pas encore de données</div>
                  : (
                    <ResponsiveContainer width="100%" height={180}>
                      <PieChart>
                        <Pie data={originesData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} strokeWidth={0}>
                          {originesData.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                        </Pie>
                        <Tooltip contentStyle={{ background: C.espresso, border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 8, fontSize: 12 }} formatter={(v) => [`${v} €`]} />
                        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 10, color: "rgba(223,207,196,0.5)" }} />
                      </PieChart>
                    </ResponsiveContainer>
                  )
                }
              </div>
            </div>
          </>
        )}

        {/* TAB MARCHÉS */}
        {tab === "marches" && (
          <>
            {lmr ? <Skeleton h={200} /> : !marches?.marches?.length
              ? <div style={{ padding: 48, textAlign: "center", fontSize: 14, color: "rgba(223,207,196,0.3)" }}>Aucun marché passé encore</div>
              : (
                <>
                  <div className="card" style={{ padding: 20, marginBottom: 18 }}>
                    <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 13, marginBottom: 16 }}>CA par marché</div>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={marches.marches}>
                        <XAxis dataKey="nom" tick={{ fill: "rgba(223,207,196,0.3)", fontSize: 10 }} axisLine={false} tickLine={false} />
                        <YAxis hide />
                        <Tooltip contentStyle={{ background: C.espresso, border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 8, fontSize: 12 }} formatter={(v) => [`${v} €`, "CA"]} />
                        <Bar dataKey="ca" fill={C.gold} radius={[4,4,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 80px", gap: 8, padding: "12px 20px", background: "rgba(0,0,0,0.2)", borderBottom: "1px solid rgba(193,138,74,0.1)" }}>
                      {["Marché","CA","Kg vendus","Commandes","Taux"].map(h => <div key={h} style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", fontWeight: 600, textTransform: "uppercase" }}>{h}</div>)}
                    </div>
                    {marches.marches.map(m => (
                      <div key={m.id} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 80px", gap: 8, padding: "14px 20px", borderBottom: "1px solid rgba(223,207,196,0.05)", alignItems: "center" }}>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 600 }}>{m.nom}</div>
                          <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)" }}>{m.lieu}</div>
                        </div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: C.gold }}>{m.ca} €</div>
                        <div style={{ fontSize: 13 }}>{m.kg_vendus} kg</div>
                        <div style={{ fontSize: 13 }}>{m.nb_commandes}</div>
                        <div>
                          <div style={{ height: 6, background: "rgba(223,207,196,0.06)", borderRadius: 3, overflow: "hidden", marginBottom: 3 }}>
                            <div style={{ height: "100%", width: `${m.taux_ecoulement}%`, background: m.taux_ecoulement > 70 ? "#4ade80" : C.gold, borderRadius: 3 }} />
                          </div>
                          <div style={{ fontSize: 10, color: "rgba(223,207,196,0.4)" }}>{m.taux_ecoulement}%</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )
            }
          </>
        )}

        {/* TAB ORIGINES */}
        {tab === "origines" && (
          lor ? <Skeleton h={300} />
          : !origines?.origines?.length
            ? <div style={{ padding: 48, textAlign: "center", fontSize: 14, color: "rgba(223,207,196,0.3)" }}>Pas encore de données de vente</div>
            : (
              <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr", gap: 8, padding: "12px 20px", background: "rgba(0,0,0,0.2)", borderBottom: "1px solid rgba(193,138,74,0.1)" }}>
                  {["Origine","CA","Kg vendus","Marge","Rotation"].map(h => <div key={h} style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", fontWeight: 600, textTransform: "uppercase" }}>{h}</div>)}
                </div>
                {origines.origines.map((o, i) => (
                  <div key={o.origine} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr", gap: 8, padding: "14px 20px", borderBottom: "1px solid rgba(223,207,196,0.05)", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{ width: 8, height: 8, borderRadius: "50%", background: PALETTE[i % PALETTE.length], flexShrink: 0 }} />
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{o.origine}</div>
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: C.gold }}>{o.ca} €</div>
                    <div style={{ fontSize: 13 }}>{o.kg_vendus} kg</div>
                    <div style={{ fontSize: 13, color: o.marge_pct > 40 ? "#4ade80" : C.gold }}>{o.marge_pct}%</div>
                    <div style={{ fontSize: 11, color: "rgba(223,207,196,0.5)" }}>{o.nb_ventes} vente(s)</div>
                  </div>
                ))}
              </div>
            )
        )}

        {/* TAB CLIENTS */}
        {tab === "clients" && (
          lcl ? <Skeleton h={300} />
          : !clients
            ? <div style={{ padding: 48, textAlign: "center", fontSize: 14, color: "rgba(223,207,196,0.3)" }}>Pas encore de données clients</div>
            : (
              <>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 22 }}>
                  {[
                    { label: "Clients totaux", value: clients.total },
                    { label: "Nouveaux ce mois", value: clients.nouveaux_mois },
                    { label: "Clients récurrents", value: clients.recurrents },
                    { label: "Taux rétention", value: `${clients.taux_retention}%` },
                  ].map((k, i) => (
                    <div key={i} className="kpi">
                      <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>{k.label}</div>
                      <div style={{ fontSize: 24, fontFamily: "'Raleway', sans-serif", fontWeight: 700, color: C.gold }}>{k.value}</div>
                    </div>
                  ))}
                </div>
                {clients.top_clients?.length > 0 && (
                  <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                    <div style={{ padding: "14px 20px", background: "rgba(0,0,0,0.2)", borderBottom: "1px solid rgba(193,138,74,0.1)", fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 12, textTransform: "uppercase", letterSpacing: 1, color: C.gold }}>
                      Top clients
                    </div>
                    {clients.top_clients.map((c, i) => (
                      <div key={c.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", borderBottom: "1px solid rgba(223,207,196,0.05)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "rgba(223,207,196,0.3)", width: 20 }}>#{i+1}</span>
                          <div>
                            <div style={{ fontSize: 13, fontWeight: 600 }}>{c.prenom} {c.nom}</div>
                            <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)" }}>{c.nb_achats} achat(s)</div>
                          </div>
                        </div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: C.gold }}>{c.total_achats} €</div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )
        )}
      </div>
    </Layout>
  );
}

// ════════════════════════════════════════════════════════════
//  TAB SUMUP — CA réel, frais, ventes importées + sync manuelle
// ════════════════════════════════════════════════════════════
function TabSumUp() {
  const qc = useQueryClient();
  const [jours, setJours] = useState("30");
  const [msg, setMsg] = useState(null);

  const { data: statut } = useQuery({
    queryKey: ["sumup-statut"],
    queryFn: getStatutSumUp,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["sumup-ventes", jours],
    queryFn: () => getVentesSumUp({ jours: parseInt(jours), limit: 100 }),
  });

  const syncMutation = useMutation({
    mutationFn: () => syncVentesSumUp(),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["sumup-ventes"] });
      qc.invalidateQueries({ queryKey: ["sumup-statut"] });
      qc.invalidateQueries({ queryKey: ["lots"] });
      setMsg({ ok: true, text: `${r.importees} vente(s) importée(s) · ${r.stock_maj} stock(s) mis à jour · ${r.remboursements} remboursement(s)` });
    },
    onError: (err) => setMsg({ ok: false, text: extractError(err, "Erreur de synchronisation SumUp") }),
  });

  const stats = data?.stats;
  const ventes = data?.ventes || [];

  if (statut && !statut.configure) {
    return (
      <div className="card" style={{ padding: 40, textAlign: "center" }}>
        <div style={{ fontSize: 28, marginBottom: 12 }}>💳</div>
        <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 15, marginBottom: 8 }}>SumUp n'est pas encore connecté</div>
        <div style={{ fontSize: 13, color: "rgba(223,207,196,0.45)", lineHeight: 1.8, maxWidth: 460, margin: "0 auto" }}>
          Ajoutez votre clé API dans <b style={{ color: C.gold }}>Paramètres → SumUp</b> pour importer
          automatiquement vos ventes (terminal et en ligne), suivre votre chiffre d'affaires réel,
          les frais SumUp, et mettre à jour le stock à chaque vente.
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Barre d'actions */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <select value={jours} onChange={e => setJours(e.target.value)} style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(193,138,74,0.15)", borderRadius: 10, padding: "8px 14px", color: C.creme, fontFamily: "'Outfit', sans-serif", fontSize: 12, outline: "none" }}>
            <option value="7">7 derniers jours</option>
            <option value="30">30 derniers jours</option>
            <option value="90">90 derniers jours</option>
            <option value="365">12 derniers mois</option>
          </select>
          {statut?.derniere_sync && (
            <span style={{ fontSize: 11, color: "rgba(223,207,196,0.35)" }}>
              Dernière sync : {new Date(statut.derniere_sync).toLocaleString("fr-FR")} · auto toutes les 15 min
            </span>
          )}
        </div>
        <button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
          style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "8px 18px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif", opacity: syncMutation.isPending ? 0.6 : 1 }}
        >
          {syncMutation.isPending ? "Synchronisation..." : "↺ Synchroniser maintenant"}
        </button>
      </div>

      {msg && (
        <div style={{ padding: "10px 16px", borderRadius: 12, marginBottom: 16, fontSize: 12, display: "flex", justifyContent: "space-between", background: msg.ok ? "rgba(74,222,128,0.08)" : "rgba(232,160,184,0.08)", color: msg.ok ? "#4ade80" : "#e8a0b8", border: `1px solid ${msg.ok ? "rgba(74,222,128,0.2)" : "rgba(232,160,184,0.2)"}` }}>
          <span>{msg.ok ? "✓" : "✗"} {msg.text}</span>
          <button onClick={() => setMsg(null)} style={{ background: "none", border: "none", color: "inherit", cursor: "pointer" }}>×</button>
        </div>
      )}

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 22 }}>
        {[
          { label: "CA brut encaissé", value: stats ? `${stats.ca_brut.toLocaleString("fr")} €` : null },
          { label: "Frais SumUp", value: stats ? `− ${stats.frais.toLocaleString("fr")} €` : null, c: "#e8a0b8" },
          { label: "CA net", value: stats ? `${stats.ca_net.toLocaleString("fr")} €` : null, c: "#4ade80" },
          { label: "Nb de ventes", value: stats?.nb_ventes },
        ].map((k, i) => (
          <div key={i} className="kpi">
            <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>{k.label}</div>
            {isLoading ? <Skeleton h={26} w="60%" /> : <div style={{ fontSize: 24, fontFamily: "'Raleway', sans-serif", fontWeight: 700, color: k.c || C.gold }}>{k.value ?? "—"}</div>}
          </div>
        ))}
      </div>

      {/* Liste des ventes */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "150px 1.6fr 100px 90px 110px 110px", gap: 8, padding: "12px 18px", background: "rgba(0,0,0,0.2)", borderBottom: "1px solid rgba(193,138,74,0.1)" }}>
          {["Date", "Produits", "Montant", "Frais", "Type", "Stock"].map(h => (
            <div key={h} style={{ fontSize: 10, color: "rgba(223,207,196,0.3)", fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase" }}>{h}</div>
          ))}
        </div>
        {isLoading
          ? [1,2,3].map(i => <div key={i} style={{ padding: "14px 18px" }}><Skeleton h={18} /></div>)
          : ventes.length === 0
            ? <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "rgba(223,207,196,0.3)" }}>
                Aucune vente importée sur la période — cliquez sur « Synchroniser maintenant »
              </div>
            : ventes.map(v => {
              const rembourse = ["REFUNDED","CHARGEBACK","CANCELLED","FAILED"].includes(v.statut);
              return (
                <div key={v.id} style={{ display: "grid", gridTemplateColumns: "150px 1.6fr 100px 90px 110px 110px", gap: 8, alignItems: "center", padding: "12px 18px", borderBottom: "1px solid rgba(223,207,196,0.05)", opacity: rembourse ? 0.45 : 1 }}>
                  <div style={{ fontSize: 11, color: "rgba(223,207,196,0.5)" }}>
                    {v.date_transaction ? new Date(v.date_transaction).toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"}
                  </div>
                  <div style={{ fontSize: 12 }}>
                    {(v.produits || []).length > 0
                      ? v.produits.map((p, i) => <span key={i}>{i > 0 && " · "}{p.name}{p.quantity > 1 ? ` ×${p.quantity}` : ""}</span>)
                      : <span style={{ color: "rgba(223,207,196,0.3)" }}>Montant libre (sans article)</span>}
                    {rembourse && <span style={{ marginLeft: 8, fontSize: 10, color: "#e8a0b8", fontWeight: 600 }}>REMBOURSÉE</span>}
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: C.gold }}>{v.montant.toFixed(2)} €</div>
                  <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)" }}>{v.frais ? `−${v.frais.toFixed(2)} €` : "—"}</div>
                  <div style={{ fontSize: 11, color: "rgba(223,207,196,0.5)" }}>{v.payment_type || "—"}{v.entry_mode ? ` · ${v.entry_mode}` : ""}</div>
                  <div>
                    {v.stock_traite
                      ? <span style={{ fontSize: 10, fontWeight: 600, padding: "3px 8px", borderRadius: 20, background: "rgba(74,222,128,0.1)", color: "#4ade80" }} title={(v.stock_details || []).map(d => d.kg ? `${d.origine} −${d.kg}kg` : "").join(" · ")}>✓ déduit</span>
                      : <span style={{ fontSize: 10, fontWeight: 600, padding: "3px 8px", borderRadius: 20, background: "rgba(223,207,196,0.06)", color: "rgba(223,207,196,0.35)" }} title="Nommez vos articles SumUp comme vos origines ERP avec le poids (ex : Moka Bio 250g)">non lié</span>}
                  </div>
                </div>
              );
            })
        }
      </div>
      <div style={{ fontSize: 11, color: "rgba(223,207,196,0.3)", marginTop: 12, lineHeight: 1.7 }}>
        💡 Pour que le stock se déduise automatiquement, vendez via le <b>catalogue d'articles</b> dans l'app SumUp
        et nommez vos articles comme vos origines ERP en incluant le poids — ex : « Éthiopie Yirgacheffe 250g ».
      </div>
    </>
  );
}
