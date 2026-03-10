import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../services/api";
import { useAuthStore } from "../stores/auth";

const C = {
  espresso: "#261810", gold: "#C18A4A", prune: "#6B3F57",
  rose: "#B07A8B", creme: "#DFCFC4", dark: "#1a0f0a",
};

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const loginStore = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async () => {
    setError("");
    setLoading(true);
    try {
      const data = await login(username, password);
      loginStore(data.access_token, data.role, data.username);
      navigate("/");
    } catch {
      setError("Identifiants incorrects");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: `radial-gradient(ellipse at 30% 20%, rgba(107,63,87,0.15) 0%, transparent 50%),
                    radial-gradient(ellipse at 70% 80%, rgba(193,138,74,0.08) 0%, transparent 50%),
                    ${C.dark}`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "'Outfit', sans-serif",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=Raleway:wght@300;700;900&display=swap');
        .login-input{transition:all 0.25s ease;border:1px solid rgba(193,138,74,0.15)!important}
        .login-input:focus{border-color:rgba(193,138,74,0.4)!important;box-shadow:0 0 0 3px rgba(193,138,74,0.08),inset 0 1px 0 rgba(255,255,255,0.03)!important}
        .login-btn{transition:all 0.3s cubic-bezier(.4,0,.2,1)}
        .login-btn:hover{transform:translateY(-1px);box-shadow:0 8px 24px rgba(107,63,87,0.4)!important}
        .login-btn:active{transform:translateY(0)}
      `}</style>

      <div style={{
        background: "rgba(38,24,16,0.55)",
        backdropFilter: "blur(32px) saturate(180%)",
        WebkitBackdropFilter: "blur(32px) saturate(180%)",
        border: `1px solid rgba(193,138,74,0.15)`,
        borderRadius: 28,
        padding: "48px 40px",
        width: 400,
        textAlign: "center",
        boxShadow: `
          0 24px 80px rgba(0,0,0,0.5),
          inset 0 1px 0 rgba(255,255,255,0.06),
          inset 0 -1px 0 rgba(0,0,0,0.1)
        `,
      }}>
        <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 32, color: C.gold, letterSpacing: 3 }}>KAHLO</div>
        <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 300, fontSize: 11, color: C.rose, letterSpacing: 6, marginBottom: 40 }}>CAFÉ · ERP</div>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <input
            className="login-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Identifiant"
            style={{
              background: "rgba(0,0,0,0.25)",
              backdropFilter: "blur(8px)",
              border: `1px solid rgba(193,138,74,0.15)`,
              borderRadius: 14, padding: "13px 18px", color: C.creme,
              fontFamily: "'Outfit', sans-serif", fontSize: 14, outline: "none",
              boxShadow: "inset 0 1px 0 rgba(255,255,255,0.03)",
            }}
          />
          <input
            className="login-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder="Mot de passe"
            style={{
              background: "rgba(0,0,0,0.25)",
              backdropFilter: "blur(8px)",
              border: `1px solid rgba(193,138,74,0.15)`,
              borderRadius: 14, padding: "13px 18px", color: C.creme,
              fontFamily: "'Outfit', sans-serif", fontSize: 14, outline: "none",
              boxShadow: "inset 0 1px 0 rgba(255,255,255,0.03)",
            }}
          />

          {error && <div style={{ fontSize: 12, color: "#e8a0b8" }}>{error}</div>}

          <button
            className="login-btn"
            onClick={handleSubmit}
            disabled={loading}
            style={{
              background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`,
              border: "none", borderRadius: 14, padding: 15,
              color: "white", fontSize: 14, fontWeight: 600,
              cursor: "pointer", fontFamily: "'Outfit', sans-serif",
              marginTop: 8, opacity: loading ? 0.7 : 1,
              boxShadow: "0 4px 16px rgba(107,63,87,0.3), inset 0 1px 0 rgba(255,255,255,0.15)",
            }}
          >
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </div>

        <div style={{ fontSize: 11, color: "rgba(223,207,196,0.2)", marginTop: 32 }}>
          Kahlo Café · Usage interne uniquement
        </div>
      </div>
    </div>
  );
}
