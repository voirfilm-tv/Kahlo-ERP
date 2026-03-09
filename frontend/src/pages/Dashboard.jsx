import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import {
  getDashboardStats, getCaMensuel, getMarchesAVenir,
  getLots, getCommandes, getAnalyseIA
} from "../services/api";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const C = {
  espresso: "#261810", gold: "#C18A4A", prune: "#6B3F57",
  rose: "#B07A8B", creme: "#DFCFC4", dark: "#1a0f0a", card: "#2e1a10",
};

const MOIS = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"];

function Skeleton({ w = "100%", h = 20 }) {
  return <div style={{ width: w, height: h, borderRadius: 6, background: "rgba(193,138,74,0.06)", animation: "pulse 1.5s infinite" }} />;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [showIA, setShowIA] = useState(false);

  const { data: stats, isLoading: loadingStats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getDashboardStats,
    refetchInterval: 60_000,
  });

  const { data: caData = [], isLoading: loadingCA } = useQuery({
    queryKey: ["ca-mensuel"],
    queryFn: () => getCaMensuel(7),
  });

  const { data: marches = [], isLoading: loadingMarches } = useQuery({
    queryKey: ["marches-a-venir"],
    queryFn: getMarchesAVenir,
  });

  const { data: lots = [], isLoading: loadingLots } = useQuery({
    queryKey: ["lots", { actif: true }],
    queryFn: () => getLots({ actif: true }),
  });

  const { data: commandes = [], isLoading: loadingCmds } = useQuery({
    queryKey: ["commandes", { statut: "en_attente" }],
    queryFn: () => getCommandes({ statut: "en_attente" }),
  });

  const { data: iaData, isLoading: loadingIA, refetch: fetchIA } = useQuery({
    queryKey: ["analyse-ia"],
    queryFn: getAnalyseIA,
    enabled: showIA,
  });

  const caChartData = caData.map(r => ({
    mois: MOIS[(r.mois || 1) - 1],
    ca: r.ca,
  }));

  const lotsAlerte = lots.filter(l => l.est_critique);
  const objectif = stats?.objectif_ca || 3500;
  const progressCA = stats ? Math.min(100, Math.round((stats.ca_mois / objectif) * 100)) : 0;

  return (
    <Layout>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=Raleway:wght@300;400;700;900&display=swap');
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: ${C.prune}; border-radius: 2px; }
        .card { background: ${C.card}; border: 1px solid rgba(193,138,74,0.12); border-radius: 16px; }
      `}</style>

      <div style={{ padding: "32px 28px", fontFamily: "'Outfit', sans-serif", color: C.creme }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
          <div>
            <h1 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 26, color: C.creme }}>
              Bonjour ☕
            </h1>
            <p style={{ color: "rgba(223,207,196,0.4)", fontSize: 13, marginTop: 3 }}>
              {new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}
            </p>
          </div>
          <button
            onClick={() => { setShowIA(true); fetchIA(); }}
            style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 12, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}
          >
            ✦ Analyse IA
          </button>
        </div>

        {/* Bloc IA */}
        {showIA && (
          <div style={{ background: `linear-gradient(135deg, rgba(107,63,87,0.25), rgba(193,138,74,0.08))`, border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 14, padding: "16px 20px", marginBottom: 24, display: "flex", gap: 14 }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, flexShrink: 0 }}>✦</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: C.gold, marginBottom: 6 }}>Analyse Gemini</div>
              {loadingIA
                ? <Skeleton h={14} />
                : <div style={{ fontSize: 12, color: "rgba(223,207,196,0.75)", lineHeight: 1.8 }}>{iaData?.analyse || "Analyse indisponible."}</div>
              }
            </div>
          </div>
        )}

        {/* KPIs */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 }}>
          {[
            { label: "CA ce mois", value: stats ? `${stats.ca_mois.toLocaleString("fr")} €` : null, sub: `Objectif : ${objectif} €` },
            { label: "CA cette semaine", value: stats ? `${stats.ca_semaine} €` : null, sub: "7 derniers jours" },
            { label: "Commandes en attente", value: stats?.commandes_attente, sub: "À préparer", alert: stats?.commandes_attente > 0 },
            { label: "Stocks critiques", value: stats?.stocks_critiques, sub: "Sous le seuil d'alerte", alert: stats?.stocks_critiques > 0 },
          ].map((k, i) => (
            <div key={i} className="card" style={{ padding: 18 }}>
              <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 8 }}>{k.label}</div>
              {loadingStats
                ? <Skeleton h={28} w="60%" />
                : <div style={{ fontSize: 26, fontFamily: "'Raleway', sans-serif", fontWeight: 700, color: k.alert ? "#e8a0b8" : C.gold, marginBottom: 4 }}>{k.value ?? "—"}</div>
              }
              <div style={{ fontSize: 11, color: "rgba(223,207,196,0.3)" }}>{k.sub}</div>
            </div>
          ))}
        </div>

        {/* Barre objectif */}
        {stats && (
          <div className="card" style={{ padding: "14px 18px", marginBottom: 24, display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ fontSize: 12, color: "rgba(223,207,196,0.5)", whiteSpace: "nowrap" }}>Objectif mensuel</div>
            <div style={{ flex: 1, height: 8, background: "rgba(223,207,196,0.06)", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${progressCA}%`, background: `linear-gradient(90deg, ${C.prune}, ${C.gold})`, borderRadius: 4, transition: "width 0.5s" }} />
            </div>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.gold, whiteSpace: "nowrap" }}>{progressCA}%</div>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
          {/* Évolution CA */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 13, marginBottom: 18 }}>Évolution CA</div>
            {loadingCA
              ? <Skeleton h={160} />
              : caChartData.length === 0
                ? <div style={{ height: 160, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, color: "rgba(223,207,196,0.3)" }}>Pas encore de données</div>
                : (
                  <ResponsiveContainer width="100%" height={160}>
                    <AreaChart data={caChartData}>
                      <defs>
                        <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={C.gold} stopOpacity={0.3} />
                          <stop offset="95%" stopColor={C.gold} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="mois" tick={{ fill: "rgba(223,207,196,0.3)", fontSize: 10 }} axisLine={false} tickLine={false} />
                      <YAxis hide />
                      <Tooltip contentStyle={{ background: C.espresso, border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 8, fontSize: 12 }} />
                      <Area type="monotone" dataKey="ca" stroke={C.gold} strokeWidth={2} fill="url(#g)" dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                )
            }
          </div>

          {/* Prochains marchés */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
              <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 13 }}>Prochains marchés</div>
              <button onClick={() => navigate("/calendrier")} style={{ background: "none", border: "none", color: C.gold, fontSize: 11, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>Voir tout →</button>
            </div>
            {loadingMarches
              ? [1,2,3].map(i => <Skeleton key={i} h={40} style={{ marginBottom: 8 }} />)
              : marches.length === 0
                ? <div style={{ fontSize: 13, color: "rgba(223,207,196,0.3)" }}>Aucun marché à venir</div>
                : marches.slice(0, 4).map(m => (
                  <div key={m.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: `1px solid rgba(223,207,196,0.05)` }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{m.nom}</div>
                      <div style={{ fontSize: 11, color: "rgba(223,207,196,0.4)" }}>{new Date(m.date).toLocaleDateString("fr-FR")}</div>
                    </div>
                    <span style={{ fontSize: 10, fontWeight: 600, padding: "3px 10px", borderRadius: 20, background: m.statut === "confirme" ? "rgba(74,222,128,0.1)" : "rgba(193,138,74,0.1)", color: m.statut === "confirme" ? "#4ade80" : C.gold }}>
                      {m.statut === "confirme" ? "Confirmé" : "Tentative"}
                    </span>
                  </div>
                ))
            }
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Stock critique */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
              <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 13 }}>Stock critique</div>
              <button onClick={() => navigate("/stock")} style={{ background: "none", border: "none", color: C.gold, fontSize: 11, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>Gérer →</button>
            </div>
            {loadingLots
              ? [1,2].map(i => <Skeleton key={i} h={36} style={{ marginBottom: 8 }} />)
              : lotsAlerte.length === 0
                ? <div style={{ fontSize: 13, color: "rgba(74,222,128,0.6)", display: "flex", alignItems: "center", gap: 8 }}><span>●</span>Tous les stocks sont OK</div>
                : lotsAlerte.map(l => (
                  <div key={l.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: `1px solid rgba(223,207,196,0.05)` }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{l.origine}</div>
                      <div style={{ fontSize: 11, color: "#e8a0b8" }}>{l.stock_kg} kg restants</div>
                    </div>
                    <div style={{ height: 6, width: 60, background: "rgba(223,207,196,0.08)", borderRadius: 3, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: `${Math.min(100, (l.stock_kg / l.seuil_alerte_kg) * 100)}%`, background: "#e8a0b8", borderRadius: 3 }} />
                    </div>
                  </div>
                ))
            }
          </div>

          {/* Commandes à remettre */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
              <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 700, fontSize: 13 }}>Commandes en attente</div>
              <button onClick={() => navigate("/commandes")} style={{ background: "none", border: "none", color: C.gold, fontSize: 11, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>Voir tout →</button>
            </div>
            {loadingCmds
              ? [1,2,3].map(i => <Skeleton key={i} h={36} style={{ marginBottom: 8 }} />)
              : commandes.length === 0
                ? <div style={{ fontSize: 13, color: "rgba(223,207,196,0.3)" }}>Aucune commande en attente</div>
                : commandes.slice(0, 4).map(c => (
                  <div key={c.id} onClick={() => navigate("/commandes")} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: `1px solid rgba(223,207,196,0.05)`, cursor: "pointer" }}>
                    <div>
                      <div style={{ fontSize: 12, fontFamily: "monospace", color: "rgba(223,207,196,0.4)", marginBottom: 2 }}>{c.numero}</div>
                      <div style={{ fontSize: 11, color: "rgba(223,207,196,0.5)" }}>{new Date(c.date_remise_prev).toLocaleDateString("fr-FR")}</div>
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: C.gold }}>{c.montant_total} €</div>
                  </div>
                ))
            }
          </div>
        </div>
      </div>
    </Layout>
  );
}
