/**
 * KAHLO CAFÉ — Layout principal
 * Sidebar liquid glass + indicateur offline sync
 */

import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/auth";
import { useOfflineSync } from "../hooks/useOfflineSync";

const C = {
  espresso: "#261810", gold: "#C18A4A", prune: "#6B3F57",
  rose: "#B07A8B", creme: "#DFCFC4", dark: "#1a0f0a",
};

const NAV = [
  { path: "/",            icon: "◈", label: "Dashboard" },
  { path: "/commandes",   icon: "◫", label: "Commandes" },
  { path: "/stock",       icon: "◉", label: "Stock" },
  { path: "/clients",     icon: "◎", label: "Clients" },
  { path: "/calendrier",  icon: "▦", label: "Calendrier" },
  { path: "/analytics",   icon: "◬", label: "Analytics" },
  { path: "/parametres",  icon: "⚙", label: "Paramètres" },
];

export default function Layout({ children }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const { online, syncing, queueSize, triggerSync } = useOfflineSync();

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: C.dark, fontFamily: "'Outfit', sans-serif", color: C.creme }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=Raleway:wght@300;400;700;900&display=swap');*{box-sizing:border-box;margin:0;padding:0}::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:${C.prune};border-radius:2px}
      .nav-item{transition:all 0.25s cubic-bezier(.4,0,.2,1)}.nav-item:hover{background:rgba(193,138,74,0.08)!important;transform:translateX(2px)}
      `}</style>

      {/* Sidebar — liquid glass */}
      <div style={{
        width: 220,
        background: "rgba(38,24,16,0.65)",
        backdropFilter: "blur(24px) saturate(180%)",
        WebkitBackdropFilter: "blur(24px) saturate(180%)",
        borderRight: `1px solid rgba(193,138,74,0.12)`,
        boxShadow: "inset -1px 0 0 rgba(255,255,255,0.03), 4px 0 24px rgba(0,0,0,0.3)",
        display: "flex", flexDirection: "column", padding: "24px 12px",
        position: "fixed", height: "100vh", zIndex: 10,
      }}>
        {/* Logo */}
        <div style={{ padding: "0 8px 28px", borderBottom: `1px solid rgba(193,138,74,0.1)`, marginBottom: 20 }}>
          <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 20, color: C.gold, letterSpacing: 1 }}>KAHLO</div>
          <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 300, fontSize: 11, color: C.rose, letterSpacing: 4, marginTop: 1 }}>CAFÉ · ERP</div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1 }}>
          {NAV.map((item) => {
            const active = pathname === item.path;
            return (
              <div
                key={item.path}
                className="nav-item"
                onClick={() => navigate(item.path)}
                style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "10px 16px", borderRadius: 12, cursor: "pointer",
                  fontSize: 13, fontWeight: 500, marginBottom: 2,
                  color: active ? C.gold : "rgba(223,207,196,0.4)",
                  background: active ? "rgba(193,138,74,0.12)" : "transparent",
                  backdropFilter: active ? "blur(8px)" : "none",
                  border: active ? "1px solid rgba(193,138,74,0.15)" : "1px solid transparent",
                  boxShadow: active ? "inset 0 1px 0 rgba(255,255,255,0.04), 0 2px 8px rgba(0,0,0,0.15)" : "none",
                }}
              >
                <span style={{ fontSize: 14 }}>{item.icon}</span>{item.label}
              </div>
            );
          })}
        </nav>

        {/* Indicateur offline — glass */}
        <div style={{
          margin: "12px 0",
          padding: "10px 14px",
          borderRadius: 12,
          background: online
            ? "rgba(74,222,128,0.06)"
            : "rgba(232,160,184,0.08)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          border: `1px solid ${online ? "rgba(74,222,128,0.15)" : "rgba(232,160,184,0.2)"}`,
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.03)",
          cursor: queueSize > 0 ? "pointer" : "default",
        }} onClick={queueSize > 0 ? triggerSync : undefined}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%",
              background: online ? "#4ade80" : "#e8a0b8",
              boxShadow: `0 0 6px ${online ? "rgba(74,222,128,0.5)" : "rgba(232,160,184,0.5)"}`,
            }} />
            <span style={{ fontSize: 11, fontWeight: 600, color: online ? "#4ade80" : "#e8a0b8" }}>
              {syncing ? "Sync en cours..." : online ? "En ligne" : "Hors ligne"}
            </span>
          </div>
          {queueSize > 0 && (
            <div style={{ fontSize: 10, color: "rgba(223,207,196,0.4)" }}>
              {queueSize} op. en attente · cliquer pour sync
            </div>
          )}
        </div>

        {/* User + logout — glass */}
        <div style={{
          borderTop: `1px solid rgba(193,138,74,0.1)`, paddingTop: 16,
        }}>
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "10px 12px", borderRadius: 12,
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.04)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{
                width: 28, height: 28, borderRadius: "50%",
                background: `linear-gradient(135deg, ${C.prune}, ${C.rose})`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 12, fontWeight: 700,
                boxShadow: "0 2px 8px rgba(107,63,87,0.4)",
              }}>K</div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600 }}>Kahlo Café</div>
                <div style={{ fontSize: 10, color: C.rose }}>Lyon, FR</div>
              </div>
            </div>
            <button onClick={logout} style={{
              background: "none", border: "none", color: "rgba(223,207,196,0.3)",
              cursor: "pointer", fontSize: 16, padding: 4,
            }} title="Déconnexion">⏻</button>
          </div>
        </div>
      </div>

      {/* Content */}
      <main style={{ marginLeft: 220, flex: 1, minHeight: "100vh" }}>
        {children}
      </main>
    </div>
  );
}
