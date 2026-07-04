import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Layout from "../components/Layout";
import { useAuthStore } from "../stores/auth";
import {
  getParametres, sauvegarderParametres, testerConnexionSumUp, testerConnexionBrevo, testerConnexionGemini, sauvegarderMaintenant,
  changerMotDePasse, getUtilisateurs, creerUtilisateur, modifierUtilisateur, supprimerUtilisateur,
  getDomaines, ajouterDomaine, verifierDomaine, modifierDomaine, supprimerDomaine,
  getSystemUpdateStatus, verifierMiseAJourSysteme, lancerMiseAJourSysteme,
  getConnexionCalDAV, regenererMotDePasseCalDAV, genererLienAppleCalDAV,
  extractError,
} from "../services/api";
import { QRCodeSVG } from "qrcode.react";
const C = {
  espresso: "#261810",
  gold: "#C18A4A",
  prune: "#6B3F57",
  rose: "#B07A8B",
  creme: "#DFCFC4",
  dark: "#1a0f0a",
  card: "#2e1a10",
  green: "#4ade80",
  red: "#e8a0b8",
};
const SECTIONS_BASE = [
  { id: "general",      icon: "◈", label: "Général" },
  { id: "sumup",        icon: "💳", label: "SumUp" },
  { id: "brevo",        icon: "✉", label: "Brevo / Email" },
  { id: "calendrier",   icon: "▦", label: "Calendrier" },
  { id: "ia",           icon: "✦", label: "Gemini IA" },
  { id: "stock",        icon: "◉", label: "Stock & Alertes" },
  { id: "crm",          icon: "◎", label: "CRM & Fidélité" },
  { id: "securite",     icon: "⬡", label: "Sécurité" },
  { id: "utilisateurs", icon: "◩", label: "Utilisateurs", adminOnly: true },
  { id: "domaines",     icon: "◆", label: "Domaines", adminOnly: true },
  { id: "sauvegarde",   icon: "◧", label: "Sauvegarde" },
  { id: "miseajour",    icon: "⟳", label: "Mise à jour", adminOnly: true },
];
// Composants réutilisables
function SectionTitle({ children }) {
  return (
    <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 13, color: C.gold, textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 20, paddingBottom: 10, borderBottom: `1px solid rgba(193,138,74,0.15)` }}>
      {children}
    </div>
  );
}
function Field({ label, hint, children }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: C.creme, marginBottom: 5 }}>{label}</label>
      {hint && <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)", marginBottom: 8 }}>{hint}</div>}
      {children}
    </div>
  );
}
function Input({ value, onChange, placeholder, type = "text", monospace }) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        background: "rgba(0,0,0,0.25)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
        border: `1px solid rgba(193,138,74,0.15)`,
        borderRadius: 12, padding: "10px 14px", color: C.creme, width: "100%",
        fontFamily: monospace ? "monospace" : "'Outfit', sans-serif",
        fontSize: monospace ? 12 : 13, outline: "none",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.03)",
        transition: "border-color 0.2s, box-shadow 0.2s",
      }}
    />
  );
}
function Toggle({ value, onChange, label, sub }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: `1px solid rgba(223,207,196,0.05)` }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 500 }}>{label}</div>
        {sub && <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)", marginTop: 2 }}>{sub}</div>}
      </div>
      <div
        onClick={() => onChange(!value)}
        style={{
          width: 44, height: 24, borderRadius: 12, cursor: "pointer", transition: "all 0.25s",
          background: value ? `linear-gradient(135deg, ${C.prune}, ${C.gold})` : "rgba(255,255,255,0.06)",
          position: "relative", flexShrink: 0,
          boxShadow: value ? "0 2px 8px rgba(107,63,87,0.3), inset 0 1px 0 rgba(255,255,255,0.1)" : "inset 0 1px 2px rgba(0,0,0,0.2)",
          border: value ? "1px solid rgba(193,138,74,0.2)" : "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <div style={{
          position: "absolute", top: 3, left: value ? 23 : 3,
          width: 18, height: 18, borderRadius: "50%", background: "white",
          transition: "left 0.25s", boxShadow: "0 1px 4px rgba(0,0,0,0.4)",
        }} />
      </div>
    </div>
  );
}
function StatusBadge({ ok, labelOk = "Connecté", labelKo = "Non configuré" }) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: "3px 10px", borderRadius: 20,
      background: ok ? "rgba(74,222,128,0.1)" : "rgba(232,160,184,0.1)",
      color: ok ? C.green : C.red,
      border: `1px solid ${ok ? "rgba(74,222,128,0.2)" : "rgba(232,160,184,0.2)"}`,
    }}>
      {ok ? `● ${labelOk}` : `○ ${labelKo}`}
    </span>
  );
}
function SaveBar({ dirty, onSave, onReset }) {
  if (!dirty) return null;
  return (
    <div style={{
      position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)",
      background: "rgba(38,24,16,0.7)",
      backdropFilter: "blur(24px) saturate(180%)",
      WebkitBackdropFilter: "blur(24px) saturate(180%)",
      border: `1px solid rgba(193,138,74,0.25)`,
      borderRadius: 16, padding: "12px 20px", display: "flex", alignItems: "center",
      gap: 14, zIndex: 999,
      boxShadow: "0 8px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06)",
    }}>
      <span style={{ fontSize: 13, color: "rgba(223,207,196,0.6)" }}>Modifications non sauvegardées</span>
      <button onClick={onReset} style={{ background: "transparent", border: `1px solid rgba(223,207,196,0.2)`, borderRadius: 8, padding: "7px 16px", color: "rgba(223,207,196,0.5)", fontSize: 12, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>Annuler</button>
      <button onClick={onSave} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 8, padding: "7px 20px", color: "white", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>Sauvegarder</button>
    </div>
  );
}
// ============================================================
//  SECTIONS CONTENU
// ============================================================
function SectionGeneral({ cfg, set }) {
  return (
    <div>
      <SectionTitle>Informations de la boutique</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Field label="Nom de la marque">
          <Input value={cfg.nom} onChange={v => set("nom", v)} placeholder="Kahlo Café" />
        </Field>
        <Field label="Ville / Localisation">
          <Input value={cfg.ville} onChange={v => set("ville", v)} placeholder="Lyon, France" />
        </Field>
        <Field label="Email de contact">
          <Input value={cfg.email} onChange={v => set("email", v)} placeholder="bonjour@kahlocafe.fr" type="email" />
        </Field>
        <Field label="Téléphone">
          <Input value={cfg.tel} onChange={v => set("tel", v)} placeholder="06 XX XX XX XX" />
        </Field>
      </div>
      <Field label="Objectif CA mensuel (€)" hint="Utilisé pour la barre de progression du dashboard">
        <Input value={cfg.objectif_ca} onChange={v => set("objectif_ca", v)} placeholder="3500" type="number" />
      </Field>
      <SectionTitle style={{ marginTop: 28 }}>Devise & Formats</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <Field label="Devise">
          <select value={cfg.devise} onChange={e => set("devise", e.target.value)} style={{ background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 10, padding: "10px 14px", color: C.creme, width: "100%", fontFamily: "'Outfit', sans-serif", fontSize: 13, outline: "none" }}>
            <option value="EUR">EUR €</option>
            <option value="USD">USD $</option>
            <option value="GBP">GBP £</option>
          </select>
        </Field>
        <Field label="Fuseau horaire">
          <select value={cfg.timezone} onChange={e => set("timezone", e.target.value)} style={{ background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 10, padding: "10px 14px", color: C.creme, width: "100%", fontFamily: "'Outfit', sans-serif", fontSize: 13, outline: "none" }}>
            <option value="Europe/Paris">Europe/Paris</option>
            <option value="Europe/London">Europe/London</option>
            <option value="UTC">UTC</option>
          </select>
        </Field>
        <Field label="Format de date">
          <select value={cfg.format_date} onChange={e => set("format_date", e.target.value)} style={{ background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 10, padding: "10px 14px", color: C.creme, width: "100%", fontFamily: "'Outfit', sans-serif", fontSize: 13, outline: "none" }}>
            <option value="dd/MM/yyyy">dd/MM/yyyy</option>
            <option value="MM/dd/yyyy">MM/dd/yyyy</option>
            <option value="yyyy-MM-dd">yyyy-MM-dd</option>
          </select>
        </Field>
      </div>
    </div>
  );
}
function SectionSumup({ cfg, set }) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [testMsg, setTestMsg] = useState("");
  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      // Teste la clé saisie dans le champ (pas besoin d'enregistrer d'abord)
      await testerConnexionSumUp(cfg.api_key);
      setTestResult("ok");
    } catch (e) {
      setTestResult("error");
      setTestMsg(extractError(e, "Clé refusée par SumUp"));
    }
    setTesting(false);
  };
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <SectionTitle>Connexion SumUp</SectionTitle>
        <StatusBadge ok={!!cfg.configure || testResult === "ok"} labelOk="Connecté" />
      </div>
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 16, marginBottom: 22, fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
        SumUp gère les paiements par carte (terminal physique sur le stand) et les checkouts en ligne (lien de paiement envoyé au client). À chaque paiement confirmé, l'ERP reçoit un webhook : le stock se décrémente, la commande change de statut, et le client est notifié.
        <br /><br />
        Avec la clé API, l'ERP <b style={{ color: C.creme }}>importe aussi automatiquement toutes vos ventes</b> (toutes les 15 min) :
        CA réel, frais SumUp et déduction du stock — visible dans <b style={{ color: C.gold }}>Analytics → 💳 SumUp</b>.
        Pour la déduction automatique du stock, nommez vos articles du catalogue SumUp comme vos origines ERP,
        poids inclus (ex : « Éthiopie Yirgacheffe 250g »).
        <br />
        <a href="https://developer.sumup.com" target="_blank" rel="noopener" style={{ color: C.gold }}>→ Créer une clé API sur developer.sumup.com (Dashboard → API keys)</a>
      </div>
      <Field label="Mode" hint="Sandbox pour tester, Live pour les vraies transactions sur le stand">
        <div style={{ display: "flex", gap: 10 }}>
          {["sandbox", "live"].map(m => (
            <div key={m} onClick={() => set("mode", m)} style={{
              flex: 1, padding: "10px 16px", borderRadius: 10, cursor: "pointer", textAlign: "center",
              fontSize: 13, fontWeight: 600, transition: "all 0.2s",
              background: cfg.mode === m ? "rgba(193,138,74,0.15)" : "rgba(0,0,0,0.2)",
              border: `1px solid ${cfg.mode === m ? "rgba(193,138,74,0.4)" : "rgba(193,138,74,0.1)"}`,
              color: cfg.mode === m ? C.gold : "rgba(223,207,196,0.4)",
            }}>
              {m === "sandbox" ? "🧪 Sandbox" : "⚡ Live"}
            </div>
          ))}
        </div>
      </Field>
      <Field label="Clé API SumUp" hint="Récupérée dans developer.sumup.com → Votre application → Clés API">
        <Input value={cfg.api_key} onChange={v => set("api_key", v)} placeholder="sup_sk_..." type="password" monospace />
      </Field>
      <Field label="Email marchand SumUp" hint="L'adresse email de votre compte SumUp — utilisée pour les checkouts">
        <Input value={cfg.merchant_email} onChange={v => set("merchant_email", v)} placeholder="bonjour@kahlocafe.fr" />
      </Field>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 24 }}>
        <button onClick={testConnection} disabled={testing || !cfg.api_key || cfg.api_key === "••••••••"} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif", opacity: testing ? 0.6 : 1 }}>
          {testing ? "Test en cours..." : "⚡ Tester la connexion"}
        </button>
        {testResult === "ok" && <span style={{ fontSize: 12, color: C.green }}>✓ Connexion SumUp vérifiée — pensez à Enregistrer</span>}
        {testResult === "error" && <span style={{ fontSize: 12, color: C.red }}>✗ {testMsg}</span>}
      </div>
      <SectionTitle>Confirmation instantanée des paiements en ligne</SectionTitle>
      <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)", marginBottom: 12, lineHeight: 1.8 }}>
        Optionnel. SumUp notifie l'ERP dès qu'un lien de paiement est réglé — il lui faut pour ça une adresse
        publique en HTTPS. <b>Sans URL publique (ex : ERP sur le réseau local), la synchronisation automatique
        (toutes les 15 min) confirme les paiements à sa place</b> — rien d'autre à configurer.
      </div>
      <Field label="URL publique de l'ERP" hint="Ex : https://erp.mondomaine.fr (via Nginx Proxy Manager). Laissez vide si l'ERP n'est accessible qu'en local.">
        <Input value={cfg.public_url} onChange={v => set("public_url", v)} placeholder="https://erp.mondomaine.fr" monospace />
      </Field>
      <div style={{ marginTop: 20, padding: 16, background: "rgba(0,0,0,0.2)", borderRadius: 12 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: C.gold, marginBottom: 8 }}>Comment ça fonctionne</div>
        <div style={{ fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
          <b style={{ color: C.creme }}>Terminal sur le stand :</b> les ventes sont importées automatiquement toutes les 15 min (CA réel, frais, stock) — visible dans Analytics → 💳 SumUp.<br />
          <b style={{ color: C.creme }}>Commandes à l'avance :</b> un lien de paiement SumUp est créé depuis la commande → une fois payé, la commande passe payée et le stock se déduit (instantané avec URL publique, sinon au prochain cycle de sync).<br />
          <b style={{ color: C.creme }}>Sécurité :</b> chaque notification de paiement est re-vérifiée auprès de l'API SumUp avant d'être acceptée.
        </div>
      </div>
    </div>
  );
}
function SectionBrevo({ cfg, set }) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      // Teste la clé saisie dans le champ (pas besoin d'enregistrer d'abord)
      await testerConnexionBrevo(cfg.api_key);
      setTestResult("ok");
    } catch {
      setTestResult("error");
    }
    setTesting(false);
  };
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <SectionTitle>Connexion Brevo</SectionTitle>
        <StatusBadge ok={!!cfg.api_key} labelOk="Configuré" />
      </div>
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 16, marginBottom: 22, fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
        Brevo envoie les emails automatiques : confirmation de commande, commande prête, anniversaires et relances clients inactifs. Les contacts sont synchronisés automatiquement depuis le CRM.
        <br />
        <a href="https://app.brevo.com/settings/keys/api" target="_blank" rel="noopener" style={{ color: C.gold }}>→ Créer une clé API sur app.brevo.com</a>
      </div>
      <Field label="Clé API Brevo" hint="app.brevo.com → Paramètres → Clés API (clé v3, commence par xkeysib-)">
        <Input value={cfg.api_key} onChange={v => set("api_key", v)} placeholder="xkeysib-..." type="password" monospace />
      </Field>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <Field label="Email expéditeur" hint="Doit être validé dans Brevo">
          <Input value={cfg.from_email} onChange={v => set("from_email", v)} placeholder="bonjour@kahlocafe.fr" />
        </Field>
        <Field label="Nom expéditeur">
          <Input value={cfg.from_name} onChange={v => set("from_name", v)} placeholder="Kahlo Café" />
        </Field>
      </div>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 24 }}>
        <button onClick={testConnection} disabled={testing} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif", opacity: testing ? 0.6 : 1 }}>
          {testing ? "Test en cours..." : "⚡ Tester la connexion"}
        </button>
        {testResult === "ok" && <span style={{ fontSize: 12, color: C.green }}>✓ Connexion Brevo OK</span>}
        {testResult === "error" && <span style={{ fontSize: 12, color: C.red }}>✗ Clé invalide ou compte injoignable</span>}
      </div>
      <SectionTitle>Templates d'emails</SectionTitle>
      <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)", marginBottom: 12 }}>
        IDs des templates créés dans Brevo → Campagnes → Templates. Laissez vide pour désactiver un email.
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <Field label="Template anniversaire">
          <Input value={cfg.tpl_anniversaire} onChange={v => set("tpl_anniversaire", v)} placeholder="1" monospace />
        </Field>
        <Field label="Template confirmation commande">
          <Input value={cfg.tpl_confirmation} onChange={v => set("tpl_confirmation", v)} placeholder="2" monospace />
        </Field>
        <Field label="Template commande prête">
          <Input value={cfg.tpl_prete} onChange={v => set("tpl_prete", v)} placeholder="3" monospace />
        </Field>
        <Field label="Template relance inactifs">
          <Input value={cfg.tpl_relance} onChange={v => set("tpl_relance", v)} placeholder="4" monospace />
        </Field>
      </div>
      <SectionTitle>Listes de contacts</SectionTitle>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
        <Field label="Liste clients">
          <Input value={cfg.liste_clients} onChange={v => set("liste_clients", v)} placeholder="3" monospace />
        </Field>
        <Field label="Liste VIP">
          <Input value={cfg.liste_vip} onChange={v => set("liste_vip", v)} placeholder="5" monospace />
        </Field>
        <Field label="Liste relance">
          <Input value={cfg.liste_relance} onChange={v => set("liste_relance", v)} placeholder="7" monospace />
        </Field>
      </div>
      <SectionTitle>Envois automatiques</SectionTitle>
      <Toggle value={cfg.envoi_confirmation} onChange={v => set("envoi_confirmation", v)} label="Confirmation de commande" sub="Email envoyé à la création d'une commande payée" />
      <Toggle value={cfg.envoi_prete} onChange={v => set("envoi_prete", v)} label="Commande prête" sub="Email envoyé quand la commande passe en statut « prête »" />
      <Toggle value={cfg.envoi_anniversaire} onChange={v => set("envoi_anniversaire", v)} label="Anniversaires" sub="Email automatique envoyé le matin de l'anniversaire du client" />
      <Toggle value={cfg.envoi_relance} onChange={v => set("envoi_relance", v)} label="Relance clients inactifs" sub="Relance hebdomadaire des clients sans commande depuis 45 jours" />
    </div>
  );
}
function ChampCopiable({ label, value, masque = false }) {
  const [copie, setCopie] = useState(false);
  const [visible, setVisible] = useState(!masque);
  const copier = () => {
    navigator.clipboard.writeText(value || "");
    setCopie(true);
    setTimeout(() => setCopie(false), 1800);
  };
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 10, color: "rgba(223,207,196,0.35)", textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 5 }}>{label}</div>
      <div style={{ display: "flex", gap: 8 }}>
        <div style={{ flex: 1, background: "rgba(0,0,0,0.3)", border: "1px solid rgba(193,138,74,0.15)", borderRadius: 10, padding: "10px 14px", fontFamily: "monospace", fontSize: 12, color: C.creme, overflowX: "auto", whiteSpace: "nowrap" }}>
          {visible ? (value || "—") : "••••••••••••"}
        </div>
        {masque && (
          <button onClick={() => setVisible(!visible)} style={{ background: "rgba(193,138,74,0.08)", border: "1px solid rgba(193,138,74,0.2)", borderRadius: 10, padding: "0 12px", color: C.gold, cursor: "pointer", fontSize: 12, fontFamily: "'Outfit', sans-serif" }}>
            {visible ? "Masquer" : "Voir"}
          </button>
        )}
        <button onClick={copier} style={{ background: copie ? "rgba(74,222,128,0.12)" : "rgba(193,138,74,0.08)", border: `1px solid ${copie ? "rgba(74,222,128,0.3)" : "rgba(193,138,74,0.2)"}`, borderRadius: 10, padding: "0 14px", color: copie ? C.green : C.gold, cursor: "pointer", fontSize: 12, fontWeight: 600, fontFamily: "'Outfit', sans-serif", whiteSpace: "nowrap" }}>
          {copie ? "✓ Copié" : "Copier"}
        </button>
      </div>
    </div>
  );
}

const FREQUENCES_SYNC = [
  { v: "1",    l: "⚡ Temps réel — toutes les secondes" },
  { v: "5",    l: "Toutes les 5 secondes" },
  { v: "15",   l: "Toutes les 15 secondes" },
  { v: "30",   l: "Toutes les 30 secondes" },
  { v: "60",   l: "Toutes les minutes" },
  { v: "300",  l: "Toutes les 5 minutes" },
  { v: "900",  l: "Toutes les 15 minutes" },
  { v: "1800", l: "Toutes les 30 minutes" },
];

function SectionCalendrier({ cfg, set }) {
  const qc = useQueryClient();
  const [lienApple, setLienApple] = useState(null);
  const [msg, setMsg] = useState(null);

  const { data: connexion, isLoading: loadingCx } = useQuery({
    queryKey: ["caldav-connexion"],
    queryFn: getConnexionCalDAV,
  });

  const lienMutation = useMutation({
    mutationFn: genererLienAppleCalDAV,
    onSuccess: (d) => setLienApple(d),
    onError: (err) => setMsg({ ok: false, text: extractError(err, "Impossible de générer le lien") }),
  });

  const regenMutation = useMutation({
    mutationFn: regenererMotDePasseCalDAV,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["caldav-connexion"] });
      setLienApple(null);
      setMsg({ ok: true, text: "Nouveau mot de passe généré — reconfigurez vos appareils (nouveau QR code)" });
    },
    onError: (err) => setMsg({ ok: false, text: extractError(err, "Impossible de régénérer le mot de passe") }),
  });

  return (
    <div>
      <SectionTitle>Connecter un appareil (iPhone, Mac, Android...)</SectionTitle>
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 16, marginBottom: 20, fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
        L'ERP héberge et gère son propre serveur de calendrier — <b style={{ color: C.creme }}>rien à installer,
        rien à configurer</b> : le mot de passe est généré automatiquement. Scannez le QR code (Apple) ou copiez
        les informations ci-dessous. Les marchés et rappels de l'ERP apparaissent sur vos appareils, et inversement.
      </div>

      {msg && (
        <div style={{ padding: "10px 14px", borderRadius: 10, marginBottom: 14, fontSize: 12, background: msg.ok ? "rgba(74,222,128,0.08)" : "rgba(232,160,184,0.08)", color: msg.ok ? C.green : C.red, border: `1px solid ${msg.ok ? "rgba(74,222,128,0.2)" : "rgba(232,160,184,0.2)"}` }}>
          {msg.ok ? "✓" : "✗"} {msg.text}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 20, marginBottom: 24 }}>
        {/* Infos à copier */}
        <div style={{ background: "rgba(0,0,0,0.15)", borderRadius: 14, padding: 18 }}>
          {loadingCx ? <div style={{ fontSize: 12, color: "rgba(223,207,196,0.4)" }}>Chargement...</div> : <>
            <ChampCopiable label="Adresse du serveur" value={connexion?.url} />
            <ChampCopiable label="Identifiant" value={connexion?.username} />
            <ChampCopiable label="Mot de passe (géré par l'ERP)" value={connexion?.password} masque />
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 4 }}>
              <button onClick={() => { if (window.confirm("Régénérer le mot de passe ? Les appareils déjà connectés devront être reconfigurés.")) regenMutation.mutate(); }}
                disabled={regenMutation.isPending}
                style={{ background: "rgba(232,160,184,0.08)", border: "1px solid rgba(232,160,184,0.2)", borderRadius: 10, padding: "8px 14px", color: C.red, cursor: "pointer", fontSize: 11, fontWeight: 600, fontFamily: "'Outfit', sans-serif" }}>
                ↻ Régénérer le mot de passe
              </button>
              {connexion && connexion.gestion_auto === false && (
                <span style={{ fontSize: 11, color: C.red }}>⚠ volume partagé absent — relancez : docker compose up -d --build</span>
              )}
            </div>
            <div style={{ fontSize: 11, color: "rgba(223,207,196,0.3)", marginTop: 12, lineHeight: 1.7 }}>
              <b>Android :</b> installez DAVx⁵ (gratuit, F-Droid/Play Store) → « Connexion avec URL et nom d'utilisateur » → collez les 3 champs ci-dessus.<br />
              <b>Configuration manuelle iPhone :</b> Réglages → Apps → Calendrier → Comptes → Autre → Compte CalDAV.
            </div>
          </>}
        </div>

        {/* QR code Apple */}
        <div style={{ background: "rgba(0,0,0,0.15)", borderRadius: 14, padding: 18, textAlign: "center" }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: C.gold, marginBottom: 10 }}> iPhone / iPad / Mac — automatique</div>
          {lienApple ? (
            <>
              <div style={{ background: "white", borderRadius: 12, padding: 12, display: "inline-block" }}>
                <QRCodeSVG value={lienApple.url} size={168} />
              </div>
              <div style={{ fontSize: 11, color: "rgba(223,207,196,0.45)", marginTop: 10, lineHeight: 1.7 }}>
                Scannez avec l'appareil photo → installez le profil :<br />le calendrier se configure tout seul.
                <br /><span style={{ color: "rgba(223,207,196,0.3)" }}>Lien valable {lienApple.expire_minutes} min.</span>
              </div>
              <a href={lienApple.url} style={{ display: "inline-block", marginTop: 8, fontSize: 11, color: C.gold }}>ou télécharger le profil sur cet appareil</a>
            </>
          ) : (
            <>
              <div style={{ fontSize: 40, margin: "18px 0" }}>📱</div>
              <button onClick={() => lienMutation.mutate()} disabled={lienMutation.isPending}
                style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 18px", color: "white", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
                {lienMutation.isPending ? "Génération..." : "Afficher le QR code"}
              </button>
              <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)", marginTop: 10, lineHeight: 1.7 }}>
                Un scan → le compte calendrier<br />s'installe automatiquement.
              </div>
            </>
          )}
        </div>
      </div>

      <Field label="Fréquence de synchronisation" hint="Peu coûteux même en temps réel : l'ERP vérifie d'abord une empreinte légère et ne synchronise que si quelque chose a changé. Appliqué immédiatement.">
        <select value={cfg.caldav_interval} onChange={e => set("caldav_interval", e.target.value)} style={{ background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 10, padding: "10px 14px", color: C.creme, width: "100%", fontFamily: "'Outfit', sans-serif", fontSize: 13, outline: "none" }}>
          {FREQUENCES_SYNC.map(f => <option key={f.v} value={f.v}>{f.l}</option>)}
        </select>
      </Field>
      <SectionTitle>Google Calendar (OAuth)</SectionTitle>
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 16, marginBottom: 20, fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
        Créez des identifiants OAuth sur <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener" style={{ color: C.gold }}>console.cloud.google.com</a> → API et services → Identifiants → Créer des identifiants → ID client OAuth.
        <br />Type d'application : Application Web. URI de redirection : <code style={{ fontFamily: "monospace", color: C.rose }}>http://localhost/api/auth/google/callback</code>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Field label="Client ID Google">
          <Input value={cfg.google_client_id} onChange={v => set("google_client_id", v)} placeholder="...apps.googleusercontent.com" monospace />
        </Field>
        <Field label="Client Secret Google">
          <Input value={cfg.google_client_secret} onChange={v => set("google_client_secret", v)} placeholder="GOCSPX-..." type="password" monospace />
        </Field>
      </div>
      <button style={{ background: "rgba(193,138,74,0.08)", border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 10, padding: "10px 20px", color: C.gold, fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
        🔗 Connecter Google Calendar (OAuth)
      </button>
      <div style={{ marginTop: 20 }}>
        <Toggle value={cfg.sync_marches} onChange={v => set("sync_marches", v)} label="Sync automatique des marchés" sub="Tout marché créé dans l'ERP → événement dans le calendrier" />
        <Toggle value={cfg.sync_commandes} onChange={v => set("sync_commandes", v)} label="Sync des remises de commandes" sub="Événement créé automatiquement après paiement SumUp" />
        <Toggle value={cfg.sync_fournisseurs} onChange={v => set("sync_fournisseurs", v)} label="Sync des réceptions fournisseurs" sub="Rappel J-1 avant réception d'un lot" />
      </div>
    </div>
  );
}
function SectionIA({ cfg, set }) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      // Teste la clé et le modèle saisis dans le formulaire
      await testerConnexionGemini(cfg.api_key, cfg.model);
      setTestResult("ok");
    } catch {
      setTestResult("error");
    }
    setTesting(false);
  };
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <SectionTitle>Gemini API (Google AI)</SectionTitle>
        <StatusBadge ok={cfg.api_key.startsWith("AIza")} />
      </div>
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 16, marginBottom: 22, fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
        Gemini 1.5 Flash est utilisé pour : analyse post-marché, suggestions de stock, fiches produit Instagram, résumés dashboard. Entièrement gratuit.
        <br />
        <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener" style={{ color: C.gold }}>→ Créer une clé API sur Google AI Studio (gratuit)</a>
      </div>
      <Field label="Clé API Gemini">
        <Input value={cfg.api_key} onChange={v => set("api_key", v)} placeholder="AIza..." type="password" monospace />
      </Field>
      <Field label="Modèle" hint="gemini-1.5-flash est recommandé : rapide, gratuit, excellent en français">
        <select value={cfg.model} onChange={e => set("model", e.target.value)} style={{ background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 10, padding: "10px 14px", color: C.creme, width: "100%", fontFamily: "'Outfit', sans-serif", fontSize: 13, outline: "none" }}>
          <option value="gemini-1.5-flash">gemini-1.5-flash (recommandé)</option>
          <option value="gemini-1.5-pro">gemini-1.5-pro (plus puissant, quota limité)</option>
        </select>
      </Field>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 24 }}>
        <button onClick={testConnection} disabled={testing} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
          {testing ? "Test en cours..." : "✦ Tester Gemini"}
        </button>
        {testResult === "ok" && <span style={{ fontSize: 12, color: C.green }}>✓ Gemini répond en français ✓</span>}
        {testResult === "error" && <span style={{ fontSize: 12, color: C.red }}>✗ Clé invalide ou quota dépassé</span>}
      </div>
      <SectionTitle>Fonctions IA actives</SectionTitle>
      <Toggle value={cfg.analyse_marche} onChange={v => set("analyse_marche", v)} label="Analyse post-marché" sub="Résumé narratif après chaque marché passé" />
      <Toggle value={cfg.suggestion_stock} onChange={v => set("suggestion_stock", v)} label="Suggestion stock pour les marchés" sub="Recommande les quantités à emmener" />
      <Toggle value={cfg.fiche_produit} onChange={v => set("fiche_produit", v)} label="Génération fiches produit" sub="Description + post Instagram par origine" />
      <Toggle value={cfg.analyse_dashboard} onChange={v => set("analyse_dashboard", v)} label="Analyse dashboard hebdo" sub="Envoyée par email chaque lundi matin" />
    </div>
  );
}
function SectionStock({ cfg, set }) {
  return (
    <div>
      <SectionTitle>Seuils d'alerte</SectionTitle>
      <Field label="Seuil d'alerte global (kg)" hint="Déclenche une alerte si le stock d'un lot passe en dessous de ce seuil. Peut être surchargé lot par lot.">
        <Input value={cfg.seuil_alerte} onChange={v => set("seuil_alerte", v)} placeholder="3" type="number" />
      </Field>
      <Field label="Délai d'alerte DLC (jours)" hint="Alerte si un lot atteint sa DLC dans moins de N jours">
        <Input value={cfg.alerte_dlc_jours} onChange={v => set("alerte_dlc_jours", v)} placeholder="30" type="number" />
      </Field>
      <Field label="Seuil lot vieillissant (jours depuis réception)" hint="Signale les lots reçus depuis plus de N jours sans rotation">
        <Input value={cfg.lot_vieux_jours} onChange={v => set("lot_vieux_jours", v)} placeholder="90" type="number" />
      </Field>
      <SectionTitle>FIFO</SectionTitle>
      <Toggle value={cfg.fifo_auto} onChange={v => set("fifo_auto", v)} label="FIFO automatique" sub="Les lots les plus anciens sont vendus en premier automatiquement" />
      <Toggle value={cfg.alerte_rupture} onChange={v => set("alerte_rupture", v)} label="Alerte rupture imminente" sub="Notification si un lot s'épuise dans moins de 14 jours au rythme actuel" />
      <SectionTitle>Bon de commande fournisseur</SectionTitle>
      <Toggle value={cfg.bon_commande_auto} onChange={v => set("bon_commande_auto", v)} label="Génération automatique du bon de commande" sub="Un brouillon est créé quand un stock atteint le seuil critique" />
      <Field label="Quantité minimale de réapprovisionnement (kg)">
        <Input value={cfg.qte_min_reappro} onChange={v => set("qte_min_reappro", v)} placeholder="5" type="number" />
      </Field>
    </div>
  );
}
function SectionCRM({ cfg, set }) {
  return (
    <div>
      <SectionTitle>Fidélité</SectionTitle>
      <Field label="Tampons nécessaires pour une récompense" hint="Nombre de tampons sur la carte fidélité avant récompense">
        <Input value={cfg.tampons_max} onChange={v => set("tampons_max", v)} placeholder="10" type="number" />
      </Field>
      <Field label="Récompense au palier (ex: 1 café offert)" hint="Texte affiché dans l'ERP au moment de la remise de la récompense">
        <Input value={cfg.recompense_label} onChange={v => set("recompense_label", v)} placeholder="1 café offert (250g au choix)" />
      </Field>
      <SectionTitle>Alertes clients</SectionTitle>
      <Field label="Délai inactivité (jours)" hint="Un client est considéré inactif après N jours sans commande">
        <Input value={cfg.inactivite_jours} onChange={v => set("inactivite_jours", v)} placeholder="45" type="number" />
      </Field>
      <Field label="Alerte anniversaire (jours à l'avance)">
        <Input value={cfg.anniv_jours_avant} onChange={v => set("anniv_jours_avant", v)} placeholder="14" type="number" />
      </Field>
      <SectionTitle>Scoring VIP</SectionTitle>
      <Field label="CA minimum pour le statut VIP (€)" hint="Un client avec un CA total supérieur à ce seuil passe automatiquement VIP">
        <Input value={cfg.vip_ca_seuil} onChange={v => set("vip_ca_seuil", v)} placeholder="200" type="number" />
      </Field>
      <Toggle value={cfg.vip_auto} onChange={v => set("vip_auto", v)} label="Attribution VIP automatique" sub="Basée sur le CA total et la fréquence d'achat" />
    </div>
  );
}
function SectionSecurite({ cfg, set }) {
  const [showKey, setShowKey] = useState(false);
  const [pwdForm, setPwdForm] = useState({ ancien: "", nouveau: "", confirmer: "" });
  const [pwdMsg, setPwdMsg] = useState(null);
  const [pwdLoading, setPwdLoading] = useState(false);
  const handleChangerMdp = async () => {
    if (pwdForm.nouveau !== pwdForm.confirmer) {
      setPwdMsg({ ok: false, text: "Les mots de passe ne correspondent pas" });
      return;
    }
    if (pwdForm.nouveau.length < 6) {
      setPwdMsg({ ok: false, text: "Minimum 6 caractères" });
      return;
    }
    setPwdLoading(true);
    setPwdMsg(null);
    try {
      await changerMotDePasse(pwdForm.ancien, pwdForm.nouveau, pwdForm.confirmer);
      setPwdMsg({ ok: true, text: "Mot de passe modifié avec succès" });
      setPwdForm({ ancien: "", nouveau: "", confirmer: "" });
    } catch (e) {
      setPwdMsg({ ok: false, text: e.response?.data?.detail || "Erreur lors du changement" });
    }
    setPwdLoading(false);
  };
  return (
    <div>
      <SectionTitle>Changer mon mot de passe</SectionTitle>
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 20, marginBottom: 24 }}>
        <Field label="Mot de passe actuel">
          <Input value={pwdForm.ancien} onChange={v => setPwdForm(p => ({ ...p, ancien: v }))} placeholder="Votre mot de passe actuel" type="password" />
        </Field>
        <Field label="Nouveau mot de passe" hint="Minimum 6 caractères">
          <Input value={pwdForm.nouveau} onChange={v => setPwdForm(p => ({ ...p, nouveau: v }))} placeholder="Nouveau mot de passe" type="password" />
        </Field>
        <Field label="Confirmer le nouveau mot de passe">
          <Input value={pwdForm.confirmer} onChange={v => setPwdForm(p => ({ ...p, confirmer: v }))} placeholder="Confirmer" type="password" />
        </Field>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={handleChangerMdp} disabled={pwdLoading || !pwdForm.ancien || !pwdForm.nouveau} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif", opacity: pwdLoading ? 0.6 : 1 }}>
            {pwdLoading ? "Modification..." : "Modifier le mot de passe"}
          </button>
          {pwdMsg && <span style={{ fontSize: 12, color: pwdMsg.ok ? C.green : C.red }}>{pwdMsg.ok ? "✓" : "✗"} {pwdMsg.text}</span>}
        </div>
      </div>
      <SectionTitle>Accès & cookies</SectionTitle>
      <Field label="Cookies sécurisés (HTTPS)" hint="« Auto » les active dès qu'une clé secrète de production est configurée. Choisissez « Désactivés » uniquement si vous accédez à l'ERP en HTTP sur votre réseau local (ex: http://IP:8087 sur un NAS) — sinon la connexion boucle sur la page de login. Appliqué immédiatement.">
        <select value={cfg.cookie_secure || "auto"} onChange={e => set("cookie_secure", e.target.value)} style={{ background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 10, padding: "10px 14px", color: C.creme, width: "100%", fontFamily: "'Outfit', sans-serif", fontSize: 13, outline: "none" }}>
          <option value="auto">Auto (recommandé) — sécurisés dès que l'ERP est en production</option>
          <option value="false">Désactivés — accès HTTP local (NAS/ZimaOS sans HTTPS)</option>
          <option value="true">Toujours activés — HTTPS obligatoire</option>
        </select>
      </Field>
      <Field label="Origines autorisées (CORS)" hint="Adresses web autorisées à appeler l'API, séparées par des virgules. Inutile de la modifier si vous accédez à l'ERP par son adresse directe. Appliqué au prochain redémarrage.">
        <Input value={cfg.cors_origins || ""} onChange={v => set("cors_origins", v)} placeholder="https://erp.mondomaine.fr" monospace />
      </Field>
      <SectionTitle>Sessions</SectionTitle>
      <Toggle value={cfg.session_longue} onChange={v => set("session_longue", v)} label="Sessions longues (30 jours)" sub="Désactiver pour des sessions de 8h seulement" />
      <SectionTitle style={{ marginTop: 28 }}>Clé secrète JWT</SectionTitle>
      <Field label="SECRET_KEY" hint="Utilisée pour signer les tokens de connexion. Regénérez si vous soupçonnez une compromission.">
        <div style={{ display: "flex", gap: 8 }}>
          <Input value={showKey ? cfg.secret_key : "••••••••••••••••••••••••••••••••"} onChange={v => set("secret_key", v)} monospace />
          <button onClick={() => setShowKey(!showKey)} style={{ background: "rgba(193,138,74,0.08)", border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 10, padding: "0 14px", color: C.gold, cursor: "pointer", fontSize: 12, fontFamily: "'Outfit', sans-serif", whiteSpace: "nowrap" }}>
            {showKey ? "Masquer" : "Afficher"}
          </button>
        </div>
      </Field>
    </div>
  );
}
// ============================================================
//  SECTION UTILISATEURS (admin only)
// ============================================================
function SectionUtilisateurs() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({ username: "", nom: "", email: "", password: "", role: "utilisateur" });
  const [msg, setMsg] = useState(null);
  const charger = async () => {
    setLoading(true);
    try {
      const data = await getUtilisateurs();
      setUsers(data);
    } catch (e) {
      setMsg({ ok: false, text: extractError(e, "Erreur lors du chargement des utilisateurs") });
    }
    setLoading(false);
  };
  useEffect(() => { charger(); }, []);
  const resetForm = () => {
    setForm({ username: "", nom: "", email: "", password: "", role: "utilisateur" });
    setShowForm(false);
    setEditId(null);
  };
  const handleCreate = async () => {
    setMsg(null);
    try {
      await creerUtilisateur(form);
      setMsg({ ok: true, text: `Utilisateur "${form.username}" créé` });
      resetForm();
      charger();
    } catch (e) {
      setMsg({ ok: false, text: e.response?.data?.detail || "Erreur" });
    }
  };
  const handleToggleActif = async (user) => {
    try {
      await modifierUtilisateur(user.id, { actif: !user.actif });
      charger();
    } catch (e) {
      setMsg({ ok: false, text: e.response?.data?.detail || "Erreur" });
    }
  };
  const handleChangeRole = async (user, newRole) => {
    try {
      await modifierUtilisateur(user.id, { role: newRole });
      charger();
    } catch (e) {
      setMsg({ ok: false, text: e.response?.data?.detail || "Erreur" });
    }
  };
  const handleDelete = async (user) => {
    if (!window.confirm(`Supprimer l'utilisateur "${user.username}" ?`)) return;
    try {
      await supprimerUtilisateur(user.id);
      charger();
    } catch (e) {
      setMsg({ ok: false, text: e.response?.data?.detail || "Erreur" });
    }
  };
  const roleBadge = (role) => ({
    fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 6, textTransform: "uppercase", letterSpacing: 0.5,
    background: role === "admin" ? "rgba(193,138,74,0.15)" : "rgba(223,207,196,0.08)",
    color: role === "admin" ? C.gold : "rgba(223,207,196,0.5)",
    border: `1px solid ${role === "admin" ? "rgba(193,138,74,0.3)" : "rgba(223,207,196,0.1)"}`,
  });
  return (
    <div>
      <SectionTitle>Gestion des utilisateurs</SectionTitle>
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 16, marginBottom: 20, fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
        Gérez les comptes qui ont accès à l'ERP. Les administrateurs peuvent créer d'autres utilisateurs et accéder aux paramètres. Les utilisateurs normaux accèdent au dashboard, stock, commandes et CRM.
      </div>
      {msg && (
        <div style={{ padding: "10px 14px", borderRadius: 10, marginBottom: 16, fontSize: 12, background: msg.ok ? "rgba(74,222,128,0.08)" : "rgba(232,160,184,0.08)", color: msg.ok ? C.green : C.red, border: `1px solid ${msg.ok ? "rgba(74,222,128,0.15)" : "rgba(232,160,184,0.15)"}` }}>
          {msg.ok ? "✓" : "✗"} {msg.text}
        </div>
      )}
      {/* Liste des utilisateurs */}
      {loading ? (
        <div style={{ fontSize: 12, color: "rgba(223,207,196,0.4)", padding: 20 }}>Chargement...</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
          {users.map(u => (
            <div key={u.id} style={{
              background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: "14px 16px",
              border: `1px solid rgba(193,138,74,0.08)`,
              display: "flex", justifyContent: "space-between", alignItems: "center",
              opacity: u.actif ? 1 : 0.5,
            }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{u.nom || u.username}</span>
                  <span style={roleBadge(u.role)}>{u.role}</span>
                  {!u.actif && <span style={{ fontSize: 10, color: C.red, fontWeight: 600 }}>DÉSACTIVÉ</span>}
                </div>
                <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)", marginTop: 3 }}>
                  @{u.username}{u.email ? ` · ${u.email}` : ""}
                </div>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <select
                  value={u.role}
                  onChange={e => handleChangeRole(u, e.target.value)}
                  style={{ background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 8, padding: "5px 8px", color: C.creme, fontSize: 11, fontFamily: "'Outfit', sans-serif", outline: "none" }}
                >
                  <option value="admin">Admin</option>
                  <option value="utilisateur">Utilisateur</option>
                </select>
                <button onClick={() => handleToggleActif(u)} style={{ background: "rgba(0,0,0,0.2)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 8, padding: "5px 10px", color: u.actif ? C.red : C.green, fontSize: 11, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
                  {u.actif ? "Désactiver" : "Activer"}
                </button>
                <button onClick={() => handleDelete(u)} style={{ background: "rgba(232,160,184,0.08)", border: `1px solid rgba(232,160,184,0.15)`, borderRadius: 8, padding: "5px 10px", color: C.red, fontSize: 11, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
                  Supprimer
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      {/* Formulaire de création */}
      {!showForm ? (
        <button onClick={() => setShowForm(true)} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
          + Nouvel utilisateur
        </button>
      ) : (
        <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 20, border: `1px solid rgba(193,138,74,0.15)` }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: C.gold, marginBottom: 16 }}>Créer un utilisateur</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <Field label="Identifiant">
              <Input value={form.username} onChange={v => setForm(f => ({ ...f, username: v }))} placeholder="jean.dupont" />
            </Field>
            <Field label="Nom complet">
              <Input value={form.nom} onChange={v => setForm(f => ({ ...f, nom: v }))} placeholder="Jean Dupont" />
            </Field>
            <Field label="Email">
              <Input value={form.email} onChange={v => setForm(f => ({ ...f, email: v }))} placeholder="jean@kahlocafe.fr" type="email" />
            </Field>
            <Field label="Mot de passe" hint="Min. 6 caractères">
              <Input value={form.password} onChange={v => setForm(f => ({ ...f, password: v }))} placeholder="••••••••" type="password" />
            </Field>
          </div>
          <Field label="Rôle">
            <div style={{ display: "flex", gap: 10 }}>
              {[{ v: "utilisateur", l: "Utilisateur", desc: "Accès lecture + saisie" }, { v: "admin", l: "Administrateur", desc: "Accès complet + paramètres" }].map(r => (
                <div key={r.v} onClick={() => setForm(f => ({ ...f, role: r.v }))} style={{
                  flex: 1, padding: "12px 16px", borderRadius: 10, cursor: "pointer", transition: "all 0.2s",
                  background: form.role === r.v ? "rgba(193,138,74,0.15)" : "rgba(0,0,0,0.2)",
                  border: `1px solid ${form.role === r.v ? "rgba(193,138,74,0.4)" : "rgba(193,138,74,0.1)"}`,
                }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: form.role === r.v ? C.gold : "rgba(223,207,196,0.5)" }}>{r.l}</div>
                  <div style={{ fontSize: 11, color: "rgba(223,207,196,0.3)", marginTop: 3 }}>{r.desc}</div>
                </div>
              ))}
            </div>
          </Field>
          <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
            <button onClick={handleCreate} disabled={!form.username || !form.password} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
              Créer l'utilisateur
            </button>
            <button onClick={resetForm} style={{ background: "transparent", border: `1px solid rgba(223,207,196,0.2)`, borderRadius: 10, padding: "10px 20px", color: "rgba(223,207,196,0.5)", fontSize: 13, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
              Annuler
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
// ============================================================
//  SECTION DOMAINES (admin only)
// ============================================================
function SectionDomaines() {
  const [domaines, setDomaines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ domaine: "", type: "principal", dns_valeur_attendue: "", notes: "" });
  const [msg, setMsg] = useState(null);
  const [verifying, setVerifying] = useState(null);
  const charger = async () => {
    setLoading(true);
    try {
      const data = await getDomaines();
      setDomaines(data);
    } catch (e) {
      setMsg({ ok: false, text: extractError(e, "Erreur lors du chargement des domaines") });
    }
    setLoading(false);
  };
  useEffect(() => { charger(); }, []);
  const handleAdd = async () => {
    setMsg(null);
    try {
      await ajouterDomaine(form);
      setMsg({ ok: true, text: `Domaine "${form.domaine}" ajouté` });
      setForm({ domaine: "", type: "principal", dns_valeur_attendue: "", notes: "" });
      setShowForm(false);
      charger();
    } catch (e) {
      setMsg({ ok: false, text: e.response?.data?.detail || "Erreur" });
    }
  };
  const handleVerify = async (dom) => {
    setVerifying(dom.id);
    try {
      const result = await verifierDomaine(dom.id);
      setMsg({
        ok: result.dns.valide,
        text: result.dns.valide
          ? `DNS vérifié pour ${dom.domaine} (${result.dns.type_enregistrement}: ${result.dns.valeur_trouvee})`
          : `DNS non valide pour ${dom.domaine} — ${result.dns.erreur || "Valeur trouvée: " + (result.dns.valeur_trouvee || "aucune")}`,
      });
      charger();
    } catch (e) {
      setMsg({ ok: false, text: e.response?.data?.detail || "Erreur lors de la vérification" });
    }
    setVerifying(null);
  };
  const handleDelete = async (dom) => {
    if (!window.confirm(`Supprimer le domaine "${dom.domaine}" ?`)) return;
    try {
      await supprimerDomaine(dom.id);
      charger();
    } catch (e) {
      setMsg({ ok: false, text: e.response?.data?.detail || "Erreur" });
    }
  };
  const handleToggleSSL = async (dom) => {
    try {
      await modifierDomaine(dom.id, { ssl_actif: !dom.ssl_actif });
      charger();
    } catch (e) {
      setMsg({ ok: false, text: extractError(e, "Erreur lors de la modification SSL") });
    }
  };
  const statutBadge = (statut) => {
    const map = {
      en_attente: { bg: "rgba(255,200,0,0.1)", color: "#fbbf24", border: "rgba(255,200,0,0.2)", label: "En attente" },
      verifie:    { bg: "rgba(74,222,128,0.1)", color: C.green, border: "rgba(74,222,128,0.2)", label: "Vérifié" },
      erreur:     { bg: "rgba(232,160,184,0.1)", color: C.red, border: "rgba(232,160,184,0.2)", label: "Erreur DNS" },
    };
    const s = map[statut] || map.en_attente;
    return (
      <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 6, background: s.bg, color: s.color, border: `1px solid ${s.border}` }}>
        {s.label}
      </span>
    );
  };
  return (
    <div>
      <SectionTitle>Gestion des domaines</SectionTitle>
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 16, marginBottom: 20, fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
        Configurez vos noms de domaine pour accéder à l'ERP. Ajoutez un enregistrement DNS de type A pointant vers l'IP de votre serveur, puis lancez la vérification pour confirmer la propagation.
      </div>
      {msg && (
        <div style={{ padding: "10px 14px", borderRadius: 10, marginBottom: 16, fontSize: 12, background: msg.ok ? "rgba(74,222,128,0.08)" : "rgba(232,160,184,0.08)", color: msg.ok ? C.green : C.red, border: `1px solid ${msg.ok ? "rgba(74,222,128,0.15)" : "rgba(232,160,184,0.15)"}` }}>
          {msg.ok ? "✓" : "✗"} {msg.text}
        </div>
      )}
      {/* Liste des domaines */}
      {loading ? (
        <div style={{ fontSize: 12, color: "rgba(223,207,196,0.4)", padding: 20 }}>Chargement...</div>
      ) : domaines.length === 0 ? (
        <div style={{ background: "rgba(0,0,0,0.15)", borderRadius: 12, padding: 24, textAlign: "center", marginBottom: 20 }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>◆</div>
          <div style={{ fontSize: 13, color: "rgba(223,207,196,0.4)" }}>Aucun domaine configuré</div>
          <div style={{ fontSize: 11, color: "rgba(223,207,196,0.25)", marginTop: 4 }}>Ajoutez votre premier domaine ci-dessous</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
          {domaines.map(d => (
            <div key={d.id} style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 16, border: `1px solid rgba(193,138,74,0.08)` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <span style={{ fontSize: 15, fontWeight: 600, fontFamily: "monospace" }}>{d.domaine}</span>
                    {statutBadge(d.statut)}
                    {d.ssl_actif && <span style={{ fontSize: 10, fontWeight: 600, color: C.green }}>SSL</span>}
                    <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 6, background: "rgba(223,207,196,0.05)", color: "rgba(223,207,196,0.4)", border: "1px solid rgba(223,207,196,0.08)" }}>{d.type}</span>
                  </div>
                  {d.dns_valeur_attendue && (
                    <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)", marginBottom: 4 }}>
                      Valeur attendue : <span style={{ fontFamily: "monospace", color: "rgba(223,207,196,0.5)" }}>{d.dns_valeur_attendue}</span>
                    </div>
                  )}
                  {d.dns_valeur_actuelle && (
                    <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)" }}>
                      Valeur actuelle : <span style={{ fontFamily: "monospace", color: d.statut === "verifie" ? C.green : C.red }}>{d.dns_valeur_actuelle}</span>
                    </div>
                  )}
                  {d.derniere_verif && (
                    <div style={{ fontSize: 10, color: "rgba(223,207,196,0.2)", marginTop: 4 }}>
                      Dernière vérif. : {new Date(d.derniere_verif).toLocaleString("fr-FR")}
                    </div>
                  )}
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  <button onClick={() => handleVerify(d)} disabled={verifying === d.id} style={{ background: "rgba(193,138,74,0.08)", border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 8, padding: "6px 12px", color: C.gold, fontSize: 11, cursor: "pointer", fontFamily: "'Outfit', sans-serif", fontWeight: 600 }}>
                    {verifying === d.id ? "Vérification..." : "Vérifier DNS"}
                  </button>
                  <button onClick={() => handleToggleSSL(d)} style={{ background: "rgba(0,0,0,0.2)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 8, padding: "6px 12px", color: d.ssl_actif ? C.green : "rgba(223,207,196,0.4)", fontSize: 11, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
                    {d.ssl_actif ? "SSL actif" : "Activer SSL"}
                  </button>
                  <button onClick={() => handleDelete(d)} style={{ background: "rgba(232,160,184,0.08)", border: `1px solid rgba(232,160,184,0.15)`, borderRadius: 8, padding: "6px 12px", color: C.red, fontSize: 11, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
                    Supprimer
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {/* Formulaire d'ajout */}
      {!showForm ? (
        <button onClick={() => setShowForm(true)} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
          + Ajouter un domaine
        </button>
      ) : (
        <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 20, border: `1px solid rgba(193,138,74,0.15)` }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: C.gold, marginBottom: 16 }}>Ajouter un domaine</div>
          <Field label="Nom de domaine" hint="Exemple : erp.kahlocafe.fr (sans http://)">
            <Input value={form.domaine} onChange={v => setForm(f => ({ ...f, domaine: v }))} placeholder="erp.kahlocafe.fr" monospace />
          </Field>
          <Field label="Type">
            <div style={{ display: "flex", gap: 10 }}>
              {[{ v: "principal", l: "Principal" }, { v: "alias", l: "Alias" }, { v: "redirect", l: "Redirection" }].map(t => (
                <div key={t.v} onClick={() => setForm(f => ({ ...f, type: t.v }))} style={{
                  flex: 1, padding: "10px 16px", borderRadius: 10, cursor: "pointer", textAlign: "center",
                  fontSize: 13, fontWeight: 600, transition: "all 0.2s",
                  background: form.type === t.v ? "rgba(193,138,74,0.15)" : "rgba(0,0,0,0.2)",
                  border: `1px solid ${form.type === t.v ? "rgba(193,138,74,0.4)" : "rgba(193,138,74,0.1)"}`,
                  color: form.type === t.v ? C.gold : "rgba(223,207,196,0.4)",
                }}>
                  {t.l}
                </div>
              ))}
            </div>
          </Field>
          <Field label="Adresse IP ou CNAME attendu" hint="L'adresse IP de votre serveur (ex: 89.168.xx.xx) ou un CNAME">
            <Input value={form.dns_valeur_attendue} onChange={v => setForm(f => ({ ...f, dns_valeur_attendue: v }))} placeholder="89.168.xx.xx" monospace />
          </Field>
          <Field label="Notes (optionnel)">
            <Input value={form.notes} onChange={v => setForm(f => ({ ...f, notes: v }))} placeholder="Domaine principal de production..." />
          </Field>
          <div style={{ background: "rgba(193,138,74,0.05)", borderRadius: 10, padding: 14, marginBottom: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: C.gold, marginBottom: 8 }}>Configuration DNS requise</div>
            <div style={{ fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
              Chez votre registrar (OVH, Gandi, Cloudflare...), ajoutez :<br />
              <span style={{ fontFamily: "monospace", color: C.creme }}>Type A</span> — <span style={{ fontFamily: "monospace", color: "rgba(223,207,196,0.5)" }}>{form.domaine || "votre-domaine.fr"}</span> → <span style={{ fontFamily: "monospace", color: C.green }}>{form.dns_valeur_attendue || "IP_DU_SERVEUR"}</span><br />
              <span style={{ fontSize: 11, color: "rgba(223,207,196,0.3)" }}>La propagation DNS peut prendre jusqu'à 48h (généralement 5-30 min).</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={handleAdd} disabled={!form.domaine} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
              Ajouter le domaine
            </button>
            <button onClick={() => setShowForm(false)} style={{ background: "transparent", border: `1px solid rgba(223,207,196,0.2)`, borderRadius: 10, padding: "10px 20px", color: "rgba(223,207,196,0.5)", fontSize: 13, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
              Annuler
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
function SectionSauvegarde({ cfg, set }) {
  const [backupMsg, setBackupMsg] = useState(null);
  const [backupLoading, setBackupLoading] = useState(false);
  const handleBackupNow = async () => {
    setBackupLoading(true);
    setBackupMsg(null);
    try {
      await sauvegarderMaintenant();
      setBackupMsg({ ok: true, text: "Sauvegarde effectuée avec succès" });
    } catch (e) {
      setBackupMsg({ ok: false, text: extractError(e, "Erreur lors de la sauvegarde") });
    }
    setBackupLoading(false);
  };
  return (
    <div>
      <SectionTitle>Sauvegarde automatique</SectionTitle>
      <Toggle value={cfg.backup_auto} onChange={v => set("backup_auto", v)} label="Sauvegarde automatique PostgreSQL" sub="Dump compressé de la base de données" />
      <Field label="Fréquence de sauvegarde">
        <select value={cfg.backup_freq} onChange={e => set("backup_freq", e.target.value)} style={{ background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 10, padding: "10px 14px", color: C.creme, width: "100%", fontFamily: "'Outfit', sans-serif", fontSize: 13, outline: "none" }}>
          <option value="daily">Quotidienne</option>
          <option value="weekly">Hebdomadaire</option>
          <option value="monthly">Mensuelle</option>
        </select>
      </Field>
      <Field label="Rétention (jours)" hint="Nombre de jours pendant lequel les sauvegardes sont conservées">
        <Input value={cfg.backup_retention} onChange={v => set("backup_retention", v)} placeholder="30" type="number" />
      </Field>
      <Field label="Répertoire de stockage des backups">
        <Input value={cfg.backup_path} onChange={v => set("backup_path", v)} placeholder="/backups/kahlo" monospace />
      </Field>
      <div style={{ display: "flex", gap: 12, marginTop: 8, alignItems: "center" }}>
        <button onClick={handleBackupNow} disabled={backupLoading} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif", opacity: backupLoading ? 0.7 : 1 }}>
          {backupLoading ? "Sauvegarde..." : "⬇ Sauvegarder maintenant"}
        </button>
        {backupMsg && <span style={{ fontSize: 12, color: backupMsg.ok ? C.green : C.red }}>{backupMsg.ok ? "✓" : "✗"} {backupMsg.text}</span>}
      </div>
      <SectionTitle style={{ marginTop: 28 }}>Export des données</SectionTitle>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {["Clients (CSV)", "Commandes (CSV)", "Stock (CSV)", "Tout (ZIP)"].map(label => (
          <button key={label} style={{ background: "rgba(0,0,0,0.2)", border: `1px solid rgba(193,138,74,0.12)`, borderRadius: 10, padding: "9px 16px", color: "rgba(223,207,196,0.6)", fontSize: 12, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
            ⬇ {label}
          </button>
        ))}
      </div>
    </div>
  );
}
function SectionMiseAJour() {
  const [message, setMessage] = useState(null);
  const [showTech, setShowTech] = useState(false);
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["system-update-status"],
    queryFn: getSystemUpdateStatus,
    refetchInterval: (q) => (q.state.data?.job?.running ? 2000 : false),
  });
  const checkMutation = useMutation({
    mutationFn: verifierMiseAJourSysteme,
    onSuccess: () => {
      setMessage({ ok: true, text: "Vérification terminée." });
      refetch();
    },
    onError: (err) => setMessage({ ok: false, text: extractError(err, "Impossible de vérifier les mises à jour") }),
  });
  const startMutation = useMutation({
    mutationFn: () => lancerMiseAJourSysteme(data?.remote_version),
    onSuccess: () => {
      setMessage({ ok: true, text: "Mise à jour lancée. L'application peut être temporairement indisponible." });
      refetch();
    },
    onError: (err) => {
      setMessage({ ok: false, text: extractError(err, "La mise à jour automatique n'est pas disponible.") });
      refetch();
    },
  });
  const etatLabel = {
    a_jour: "À jour",
    mise_a_jour_disponible: "Mise à jour disponible",
    verification_impossible: "Vérification impossible",
    inconnu: "Vérification non lancée",
  };
  return (
    <div>
      <SectionTitle>Mise à jour du logiciel</SectionTitle>
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 16, marginBottom: 20, fontSize: 12, color: "rgba(223,207,196,0.65)", lineHeight: 1.7 }}>
        Cette opération peut redémarrer les services et rendre l'application indisponible pendant quelques minutes. Vos données (base PostgreSQL, volumes persistants et fichier .env) ne sont pas supprimées par la procédure proposée.
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 18 }}>
        <div style={{ background: "rgba(0,0,0,0.25)", border: `1px solid rgba(193,138,74,0.12)`, borderRadius: 12, padding: 12 }}>
          <div style={{ fontSize: 11, color: "rgba(223,207,196,0.45)" }}>Version installée</div>
          <div style={{ fontSize: 16, fontWeight: 700, marginTop: 4 }}>{data?.local_version || "—"}</div>
        </div>
        <div style={{ background: "rgba(0,0,0,0.25)", border: `1px solid rgba(193,138,74,0.12)`, borderRadius: 12, padding: 12 }}>
          <div style={{ fontSize: 11, color: "rgba(223,207,196,0.45)" }}>Dernière version GitHub</div>
          <div style={{ fontSize: 16, fontWeight: 700, marginTop: 4 }}>{data?.remote_version || "—"}</div>
        </div>
      </div>
      <Field label="État de la version">
        <div style={{ fontSize: 13, color: data?.state === "a_jour" ? C.green : data?.state === "mise_a_jour_disponible" ? C.gold : C.red }}>
          {etatLabel[data?.state] || "Inconnu"}
        </div>
      </Field>
      <div style={{ display: "flex", gap: 12, marginBottom: 18 }}>
        <button onClick={() => checkMutation.mutate()} disabled={checkMutation.isPending} style={{ background: "rgba(0,0,0,0.25)", border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 10, padding: "10px 16px", color: C.creme, cursor: "pointer" }}>
          {checkMutation.isPending ? "Vérification..." : "Vérifier les mises à jour"}
        </button>
        {data?.state === "mise_a_jour_disponible" && (
          <button onClick={() => startMutation.mutate()} disabled={startMutation.isPending || data?.job?.running} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 18px", color: "white", cursor: "pointer", fontWeight: 600 }}>
            {startMutation.isPending || data?.job?.running ? "Mise à jour en cours..." : "Mettre à jour maintenant"}
          </button>
        )}
      </div>
      {message && <div style={{ fontSize: 12, color: message.ok ? C.green : C.red, marginBottom: 12 }}>{message.text}</div>}
      <SectionTitle>Avancement simplifié</SectionTitle>
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 14, marginBottom: 14 }}>
        {(data?.job?.logs || []).length === 0 ? (
          <div style={{ fontSize: 12, color: "rgba(223,207,196,0.45)" }}>Aucun log pour le moment.</div>
        ) : (
          (data?.job?.logs || []).map((line, idx) => (
            <div key={idx} style={{ fontSize: 12, marginBottom: 6, color: line.level === "error" ? C.red : line.level === "success" ? C.green : C.creme }}>
              • {line.message}
            </div>
          ))
        )}
      </div>
      {data?.job?.error && (
        <div style={{ background: "rgba(232,160,184,0.1)", border: `1px solid rgba(232,160,184,0.2)`, borderRadius: 12, padding: 12, marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: C.red, marginBottom: 8 }}>{data.job.error.friendly}</div>
          <button onClick={() => setShowTech(!showTech)} style={{ background: "transparent", border: `1px solid rgba(223,207,196,0.2)`, borderRadius: 8, color: C.creme, padding: "5px 10px", fontSize: 11, cursor: "pointer" }}>
            {showTech ? "Masquer le détail technique" : "Voir le détail technique"}
          </button>
          {showTech && <pre style={{ marginTop: 8, fontSize: 11, whiteSpace: "pre-wrap", color: "rgba(223,207,196,0.75)" }}>{data.job.error.technical}</pre>}
        </div>
      )}
      {data?.job?.manual_instructions?.length > 0 && (
        <div>
          <SectionTitle>Mode semi-automatique (si nécessaire)</SectionTitle>
          <div style={{ fontSize: 12, color: "rgba(223,207,196,0.6)", marginBottom: 8 }}>Exécutez ces commandes sur le serveur hôte :</div>
          <pre style={{ background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.12)`, borderRadius: 10, padding: 12, fontSize: 11, whiteSpace: "pre-wrap" }}>{data.job.manual_instructions.join("\n")}</pre>
        </div>
      )}
      {isLoading && <div style={{ fontSize: 12, color: "rgba(223,207,196,0.45)", marginTop: 10 }}>Chargement du statut…</div>}
    </div>
  );
}
// ============================================================
//  COMPOSANT PRINCIPAL
// ============================================================
const DEFAULT_STATE = {
  general: { nom: "Kahlo Café", ville: "Lyon, France", email: "bonjour@kahlocafe.fr", tel: "", objectif_ca: "3500", devise: "EUR", timezone: "Europe/Paris", format_date: "dd/MM/yyyy" },
  sumup: { api_key: "", merchant_email: "", webhook_secret: "", mode: "sandbox", public_url: "", configure: false },
  brevo: { api_key: "", from_email: "bonjour@kahlocafe.fr", from_name: "Kahlo Café", tpl_anniversaire: "", tpl_confirmation: "", tpl_prete: "", tpl_relance: "", liste_clients: "", liste_vip: "", liste_relance: "", envoi_anniversaire: true, envoi_relance: true, envoi_confirmation: true, envoi_prete: true },
  calendrier: { caldav_user: "kahlo", caldav_password: "", caldav_interval: "300", google_client_id: "", google_client_secret: "", sync_marches: true, sync_commandes: true, sync_fournisseurs: false },
  ia: { api_key: "", model: "gemini-1.5-flash", analyse_marche: true, suggestion_stock: true, fiche_produit: true, analyse_dashboard: false },
  stock: { seuil_alerte: "3", alerte_dlc_jours: "30", lot_vieux_jours: "90", fifo_auto: true, alerte_rupture: true, bon_commande_auto: false, qte_min_reappro: "5" },
  crm: { tampons_max: "10", recompense_label: "1 café offert (250g au choix)", inactivite_jours: "45", anniv_jours_avant: "14", vip_ca_seuil: "200", vip_auto: true },
  securite: { username: "kahlo", new_password: "", confirm_password: "", secret_key: "••••••••••••••••••••••", session_longue: true, cookie_secure: "auto", cors_origins: "" },
  sauvegarde: { backup_auto: true, backup_freq: "daily", backup_retention: "30", backup_path: "/backups/kahlo" },
};
export default function KahloParametres() {
  const qc = useQueryClient();
  const isAdmin = useAuthStore((s) => s.role) === "admin";
  const SECTIONS = SECTIONS_BASE.filter(s => !s.adminOnly || isAdmin);
  const [active, setActive] = useState("general");
  const [state, setState] = useState(DEFAULT_STATE);
  const [saved, setSaved] = useState({ ...DEFAULT_STATE });
  const [dirty, setDirty] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);
  // Charger la config depuis le backend au montage
  const { data: configServeur, isLoading } = useQuery({
    queryKey: ["parametres"],
    queryFn: getParametres,
  });
  useEffect(() => {
    if (configServeur) {
      const merged = {};
      Object.keys(DEFAULT_STATE).forEach(section => {
        merged[section] = { ...DEFAULT_STATE[section], ...(configServeur[section] || {}) };
      });
      setState(merged);
      setSaved(merged);
    }
  }, [configServeur]);
  const saveMutation = useMutation({
    mutationFn: sauvegarderParametres,
    onSuccess: () => {
      setSaved({ ...state });
      setDirty(false);
      setSaveMsg("✓ Paramètres sauvegardés sur le serveur");
      setTimeout(() => setSaveMsg(null), 3000);
      qc.invalidateQueries({ queryKey: ["parametres"] });
    },
    onError: (err) => {
      setSaveMsg(`✗ ${extractError(err, "Erreur lors de la sauvegarde")}`);
      setTimeout(() => setSaveMsg(null), 5000);
    }
  });
  const set = (section) => (key, value) => {
    const next = { ...state, [section]: { ...state[section], [key]: value } };
    setState(next);
    setDirty(JSON.stringify(next) !== JSON.stringify(saved));
  };
  const handleSave = () => saveMutation.mutate(state);
  const handleReset = () => {
    setState({ ...saved });
    setDirty(false);
  };
  const renderSection = () => {
    const s = (k, v) => set(active)(k, v);
    const cfg = state[active];
    switch (active) {
      case "general":    return <SectionGeneral cfg={cfg} set={s} />;
      case "sumup":      return <SectionSumup cfg={cfg} set={s} />;
      case "brevo":      return <SectionBrevo cfg={cfg} set={s} />;
      case "calendrier": return <SectionCalendrier cfg={cfg} set={s} />;
      case "ia":         return <SectionIA cfg={cfg} set={s} />;
      case "stock":      return <SectionStock cfg={cfg} set={s} />;
      case "crm":        return <SectionCRM cfg={cfg} set={s} />;
      case "securite":     return <SectionSecurite cfg={cfg} set={s} />;
      case "utilisateurs": return <SectionUtilisateurs />;
      case "domaines":     return <SectionDomaines />;
      case "sauvegarde":   return <SectionSauvegarde cfg={cfg} set={s} />;
      case "miseajour":    return <SectionMiseAJour />;
      default: return null;
    }
  };
  return (
    <Layout>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=Raleway:wght@300;400;700;900&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: ${C.prune}; border-radius: 2px; }
        input::placeholder { color: rgba(223,207,196,0.2); }
        input:focus, select:focus, textarea:focus {
          outline: none;
          border-color: rgba(193,138,74,0.35) !important;
          box-shadow: 0 0 0 3px rgba(193,138,74,0.1), inset 0 1px 2px rgba(0,0,0,0.2) !important;
        }
        select option { background: ${C.espresso}; }
        a { text-decoration: none; }
        a:hover { text-decoration: underline; }
      `}</style>
      {/* Sidebar paramètres (la sidebar principale est rendue par Layout) */}
      <div style={{ width: 210, background: "rgba(35,18,9,0.6)", backdropFilter: "blur(20px) saturate(180%)", WebkitBackdropFilter: "blur(20px) saturate(180%)", borderRight: `1px solid rgba(193,138,74,0.08)`, boxShadow: "inset -1px 0 0 rgba(255,255,255,0.02), 2px 0 16px rgba(0,0,0,0.2)", position: "fixed", left: 220, top: 0, height: "100vh", padding: "32px 14px", overflowY: "auto", zIndex: 9 }}>
        <div style={{ fontSize: 10, color: "rgba(223,207,196,0.25)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 16, padding: "0 6px" }}>Paramètres</div>
        {SECTIONS.map(s => (
          <div
            key={s.id}
            onClick={() => setActive(s.id)}
            style={{
              display: "flex", alignItems: "center", gap: 10, padding: "10px 14px",
              borderRadius: 10, cursor: "pointer", fontSize: 13, fontWeight: 500,
              marginBottom: 2, transition: "all 0.2s ease",
              color: active === s.id ? C.gold : "rgba(223,207,196,0.45)",
              background: active === s.id ? "rgba(193,138,74,0.15)" : "transparent",
              backdropFilter: active === s.id ? "blur(8px)" : "none",
              borderLeft: active === s.id ? `2px solid ${C.gold}` : "2px solid transparent",
              boxShadow: active === s.id ? "inset 0 1px 0 rgba(255,255,255,0.04), 0 2px 8px rgba(0,0,0,0.15)" : "none",
            }}
          >
            <span style={{ fontSize: 13 }}>{s.icon}</span>{s.label}
          </div>
        ))}
      </div>
      {/* Contenu — le main de Layout est déjà décalé de 220px (sidebar principale),
          il reste à compenser la sidebar paramètres (210px) */}
      <div style={{ marginLeft: 210, padding: "40px 40px 100px", maxWidth: 720, fontFamily: "'Outfit', sans-serif", color: C.creme }}>
        {/* Header section */}
        <div style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h1 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 22, color: C.creme }}>
                {SECTIONS.find(s => s.id === active)?.icon} {SECTIONS.find(s => s.id === active)?.label}
              </h1>
              <p style={{ color: "rgba(223,207,196,0.35)", fontSize: 12, marginTop: 4 }}>
                Tout se configure ici — aucun fichier à éditer. Enregistré sur le serveur, appliqué immédiatement et conservé après redémarrage.
              </p>
            </div>
            {isLoading && <span style={{ fontSize: 12, color: "rgba(223,207,196,0.4)" }}>Chargement...</span>}
        {saveMsg && (
              <span style={{ fontSize: 12, color: saveMsg.startsWith("✗") ? C.red : C.green, fontWeight: 600 }}>{saveMsg}</span>
            )}
          </div>
        </div>
        {/* Contenu de la section */}
        {renderSection()}
      </div>
      {/* Barre de sauvegarde flottante */}
      <SaveBar dirty={dirty} onSave={handleSave} onReset={handleReset} saving={saveMutation.isPending} />
    </Layout>
  );
}
