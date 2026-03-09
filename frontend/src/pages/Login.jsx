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
      minHeight: "100vh", background: C.dark,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "'Outfit', sans-serif",
    }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=Raleway:wght@300;700;900&display=swap');`}</style>

      <div style={{
        background: C.espresso, border: `1px solid rgba(193,138,74,0.2)`,
        borderRadius: 24, padding: "48px 40px", width: 380, textAlign: "center",
      }}>
        <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 32, color: C.gold, letterSpacing: 3 }}>KAHLO</div>
        <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 300, fontSize: 11, color: C.rose, letterSpacing: 6, marginBottom: 40 }}>CAFÉ · ERP</div>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Identifiant"
            style={{
              background: "rgba(255,255,255,0.04)", border: `1px solid rgba(193,138,74,0.2)`,
              borderRadius: 12, padding: "12px 16px", color: C.creme,
              fontFamily: "'Outfit', sans-serif", fontSize: 14, outline: "none",
            }}
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder="Mot de passe"
            style={{
              background: "rgba(255,255,255,0.04)", border: `1px solid rgba(193,138,74,0.2)`,
              borderRadius: 12, padding: "12px 16px", color: C.creme,
              fontFamily: "'Outfit', sans-serif", fontSize: 14, outline: "none",
            }}
          />

          {error && <div style={{ fontSize: 12, color: "#e8a0b8" }}>{error}</div>}

          <button
            onClick={handleSubmit}
            disabled={loading}
            style={{
              background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`,
              border: "none", borderRadius: 12, padding: 14,
              color: "white", fontSize: 14, fontWeight: 600,
              cursor: "pointer", fontFamily: "'Outfit', sans-serif",
              marginTop: 8, opacity: loading ? 0.7 : 1,
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
