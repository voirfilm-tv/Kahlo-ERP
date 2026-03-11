import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import Layout from "../components/Layout";
import { getAnalyticsGeneral, getAnalyticsMarches, getAnalyticsOrigines, getAnalyticsClients, getAnalyseIA, extractError } from "../services/api";
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
          {[["general","◈ Général"],["marches","▦ Marchés"],["origines","◉ Origines"],["clients","◎ Clients"]].map(([k, l]) => (
            <button key={k} className={tab === k ? "tab-a" : "tab-i"} onClick={() => setTab(k)}>{l}</button>
          ))}
        </div>

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
