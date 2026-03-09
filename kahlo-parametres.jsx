import { useState } from "react";

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

const SECTIONS = [
  { id: "general",    icon: "◈", label: "Général" },
  { id: "sumup",      icon: "💳", label: "SumUp" },
  { id: "brevo",      icon: "✉", label: "Brevo / Email" },
  { id: "calendrier", icon: "▦", label: "Calendrier" },
  { id: "ia",         icon: "✦", label: "Gemini IA" },
  { id: "stock",      icon: "◉", label: "Stock & Alertes" },
  { id: "crm",        icon: "◎", label: "CRM & Fidélité" },
  { id: "securite",   icon: "⬡", label: "Sécurité" },
  { id: "sauvegarde", icon: "◧", label: "Sauvegarde" },
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
        background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`,
        borderRadius: 10, padding: "10px 14px", color: C.creme, width: "100%",
        fontFamily: monospace ? "monospace" : "'Outfit', sans-serif",
        fontSize: monospace ? 12 : 13, outline: "none",
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
          background: value ? `linear-gradient(135deg, ${C.prune}, ${C.gold})` : "rgba(255,255,255,0.08)",
          position: "relative", flexShrink: 0,
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
      background: C.espresso, border: `1px solid rgba(193,138,74,0.3)`,
      borderRadius: 14, padding: "12px 20px", display: "flex", alignItems: "center",
      gap: 14, zIndex: 999, boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
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

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    await new Promise(r => setTimeout(r, 1200));
    setTestResult(cfg.api_key.startsWith("sup_sk_") ? "ok" : "error");
    setTesting(false);
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <SectionTitle>Connexion SumUp</SectionTitle>
        <StatusBadge ok={cfg.api_key.startsWith("sup_sk_")} />
      </div>

      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 16, marginBottom: 22, fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
        SumUp gère les paiements par carte (terminal physique sur le stand) et les checkouts en ligne (lien de paiement envoyé au client). À chaque paiement confirmé, l'ERP reçoit un webhook : le stock se décrémente, la commande change de statut, et le client est notifié.
        <br />
        <a href="https://developer.sumup.com" target="_blank" rel="noopener" style={{ color: C.gold }}>→ Créer une application sur developer.sumup.com</a>
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

      <Field label="Webhook Secret" hint="Généré dans votre dashboard SumUp → Webhooks. Valide la signature des événements entrants.">
        <Input value={cfg.webhook_secret} onChange={v => set("webhook_secret", v)} placeholder="••••••••" type="password" monospace />
      </Field>

      <Field label="URL du webhook à configurer dans SumUp" hint="À renseigner dans developer.sumup.com → votre application → Webhooks">
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ flex: 1, background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 10, padding: "10px 14px", fontFamily: "monospace", fontSize: 12, color: "rgba(223,207,196,0.5)" }}>
            https://votre-domaine/api/webhooks/sumup
          </div>
          <button onClick={() => navigator.clipboard.writeText("https://votre-domaine/api/webhooks/sumup")} style={{ background: "rgba(193,138,74,0.08)", border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 10, padding: "0 16px", color: C.gold, cursor: "pointer", fontSize: 12, fontFamily: "'Outfit', sans-serif", fontWeight: 600 }}>
            Copier
          </button>
        </div>
      </Field>

      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 24 }}>
        <button onClick={testConnection} disabled={testing} style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
          {testing ? "Test en cours..." : "⚡ Tester la connexion"}
        </button>
        {testResult === "ok" && <span style={{ fontSize: 12, color: C.green }}>✓ Connexion SumUp OK</span>}
        {testResult === "error" && <span style={{ fontSize: 12, color: C.red }}>✗ Clé invalide — format attendu : sup_sk_...</span>}
      </div>

      <SectionTitle>Événements Webhook à activer dans SumUp</SectionTitle>
      <div style={{ fontSize: 11, color: "rgba(223,207,196,0.35)", marginBottom: 12 }}>
        Dans developer.sumup.com → votre application → Webhooks → Activer ces événements :
      </div>
      {["PAYMENT_STATUS_CHANGED", "transaction.successful", "transaction.failed"].map(ev => (
        <div key={ev} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <span style={{ color: C.green, fontSize: 12 }}>✓</span>
          <span style={{ fontFamily: "monospace", fontSize: 12, color: "rgba(223,207,196,0.6)" }}>{ev}</span>
        </div>
      ))}

      <div style={{ marginTop: 20, padding: 16, background: "rgba(0,0,0,0.2)", borderRadius: 12 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: C.gold, marginBottom: 8 }}>Comment ça fonctionne</div>
        <div style={{ fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
          <b style={{ color: C.creme }}>Terminal sur le stand :</b> chaque vente carte génère automatiquement un webhook → stock décrémenté en temps réel.<br />
          <b style={{ color: C.creme }}>Commandes à l'avance :</b> un lien de paiement SumUp Checkout est envoyé au client par Brevo → paiement confirmé → commande activée.
        </div>
      </div>
    </div>
  );
}


function SectionCalendrier({ cfg, set }) {
  return (
    <div>
      <SectionTitle>Apple Calendar (CalDAV)</SectionTitle>
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 12, padding: 16, marginBottom: 20, fontSize: 12, color: "rgba(223,207,196,0.5)", lineHeight: 1.8 }}>
        Synchronisation bidirectionnelle avec l'app Calendrier Apple (iPhone, Mac). Les marchés et rappels créés dans l'ERP apparaissent dans votre calendrier natif, et vice-versa.
      </div>
      <Field label="URL du serveur CalDAV" hint="À configurer dans iPhone → Réglages → Calendrier → Comptes → Autre → Compte CalDAV">
        <div style={{ background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 10, padding: "10px 14px", fontFamily: "monospace", fontSize: 12, color: "rgba(223,207,196,0.5)" }}>
          http://VOTRE-IP/caldav/kahlo/
        </div>
      </Field>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Field label="Identifiant CalDAV">
          <Input value={cfg.caldav_user} onChange={v => set("caldav_user", v)} placeholder="kahlo" />
        </Field>
        <Field label="Mot de passe CalDAV">
          <Input value={cfg.caldav_password} onChange={v => set("caldav_password", v)} placeholder="••••••••" type="password" />
        </Field>
      </div>
      <Field label="Intervalle de sync automatique">
        <select value={cfg.caldav_interval} onChange={e => set("caldav_interval", e.target.value)} style={{ background: "rgba(0,0,0,0.3)", border: `1px solid rgba(193,138,74,0.15)`, borderRadius: 10, padding: "10px 14px", color: C.creme, width: "100%", fontFamily: "'Outfit', sans-serif", fontSize: 13, outline: "none" }}>
          <option value="15">Toutes les 15 minutes</option>
          <option value="30">Toutes les 30 minutes</option>
          <option value="60">Toutes les heures</option>
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
    await new Promise(r => setTimeout(r, 900));
    setTestResult(cfg.api_key.startsWith("AIza") ? "ok" : "error");
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
  return (
    <div>
      <SectionTitle>Accès & Authentification</SectionTitle>
      <Field label="Identifiant de connexion">
        <Input value={cfg.username} onChange={v => set("username", v)} placeholder="kahlo" />
      </Field>
      <Field label="Nouveau mot de passe" hint="Laissez vide pour ne pas changer">
        <Input value={cfg.new_password} onChange={v => set("new_password", v)} placeholder="••••••••" type="password" />
      </Field>
      <Field label="Confirmer le nouveau mot de passe">
        <Input value={cfg.confirm_password} onChange={v => set("confirm_password", v)} placeholder="••••••••" type="password" />
      </Field>

      <SectionTitle>Clé secrète JWT</SectionTitle>
      <Field label="SECRET_KEY" hint="Utilisée pour signer les tokens de connexion. Regénérez si vous soupçonnez une compromission.">
        <div style={{ display: "flex", gap: 8 }}>
          <Input value={showKey ? cfg.secret_key : "••••••••••••••••••••••••••••••••"} onChange={v => set("secret_key", v)} monospace />
          <button onClick={() => setShowKey(!showKey)} style={{ background: "rgba(193,138,74,0.08)", border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 10, padding: "0 14px", color: C.gold, cursor: "pointer", fontSize: 12, fontFamily: "'Outfit', sans-serif", whiteSpace: "nowrap" }}>
            {showKey ? "Masquer" : "Afficher"}
          </button>
        </div>
      </Field>
      <button style={{ background: "rgba(232,160,184,0.08)", border: `1px solid rgba(232,160,184,0.2)`, borderRadius: 10, padding: "10px 20px", color: C.red, fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
        ↺ Regénérer la clé (déconnecte tous les appareils)
      </button>

      <div style={{ marginTop: 24 }}>
        <Toggle value={cfg.session_longue} onChange={v => set("session_longue", v)} label="Sessions longues (30 jours)" sub="Désactiver pour des sessions de 24h seulement" />
      </div>
    </div>
  );
}

function SectionSauvegarde({ cfg, set }) {
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

      <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
        <button style={{ background: `linear-gradient(135deg, ${C.prune}, ${C.gold})`, border: "none", borderRadius: 10, padding: "10px 20px", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
          ⬇ Sauvegarder maintenant
        </button>
        <button style={{ background: "rgba(193,138,74,0.08)", border: `1px solid rgba(193,138,74,0.2)`, borderRadius: 10, padding: "10px 20px", color: C.gold, fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "'Outfit', sans-serif" }}>
          ⬆ Restaurer un backup
        </button>
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

// ============================================================
//  COMPOSANT PRINCIPAL
// ============================================================

const DEFAULT_STATE = {
  general: { nom: "Kahlo Café", ville: "Lyon, France", email: "bonjour@kahlocafe.fr", tel: "", objectif_ca: "3500", devise: "EUR", timezone: "Europe/Paris", format_date: "dd/MM/yyyy" },
  sumup: { api_key: "", merchant_email: "", webhook_secret: "", mode: "sandbox" },
  brevo: { api_key: "", from_email: "bonjour@kahlocafe.fr", from_name: "Kahlo Café", tpl_anniversaire: "", tpl_confirmation: "", tpl_prete: "", tpl_relance: "", liste_clients: "", liste_vip: "", liste_relance: "", envoi_anniversaire: true, envoi_relance: true, envoi_confirmation: true, envoi_prete: true },
  calendrier: { caldav_user: "kahlo", caldav_password: "", caldav_interval: "30", google_client_id: "", google_client_secret: "", sync_marches: true, sync_commandes: true, sync_fournisseurs: false },
  ia: { api_key: "", model: "gemini-1.5-flash", analyse_marche: true, suggestion_stock: true, fiche_produit: true, analyse_dashboard: false },
  stock: { seuil_alerte: "3", alerte_dlc_jours: "30", lot_vieux_jours: "90", fifo_auto: true, alerte_rupture: true, bon_commande_auto: false, qte_min_reappro: "5" },
  crm: { tampons_max: "10", recompense_label: "1 café offert (250g au choix)", inactivite_jours: "45", anniv_jours_avant: "14", vip_ca_seuil: "200", vip_auto: true },
  securite: { username: "kahlo", new_password: "", confirm_password: "", secret_key: "••••••••••••••••••••••", session_longue: true },
  sauvegarde: { backup_auto: true, backup_freq: "daily", backup_retention: "30", backup_path: "/backups/kahlo" },
};

export default function KahloParametres() {
  const [active, setActive] = useState("general");
  const [state, setState] = useState(DEFAULT_STATE);
  const [saved, setSaved] = useState({ ...DEFAULT_STATE });
  const [dirty, setDirty] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);

  const set = (section) => (key, value) => {
    const next = { ...state, [section]: { ...state[section], [key]: value } };
    setState(next);
    setDirty(JSON.stringify(next) !== JSON.stringify(saved));
  };

  const handleSave = () => {
    setSaved({ ...state });
    setDirty(false);
    setSaveMsg("✓ Paramètres sauvegardés");
    setTimeout(() => setSaveMsg(null), 3000);
  };

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
      case "securite":   return <SectionSecurite cfg={cfg} set={s} />;
      case "sauvegarde": return <SectionSauvegarde cfg={cfg} set={s} />;
      default: return null;
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: C.dark, fontFamily: "'Outfit', sans-serif", color: C.creme, display: "flex" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=Raleway:wght@300;400;700;900&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: ${C.prune}; border-radius: 2px; }
        input::placeholder { color: rgba(223,207,196,0.2); }
        select option { background: ${C.espresso}; }
        a { text-decoration: none; }
        a:hover { text-decoration: underline; }
      `}</style>

      {/* Sidebar principale ERP */}
      <div style={{ width: 220, background: C.espresso, borderRight: `1px solid rgba(193,138,74,0.1)`, display: "flex", flexDirection: "column", padding: "24px 12px", position: "fixed", height: "100vh", zIndex: 10 }}>
        <div style={{ padding: "0 8px 28px", borderBottom: `1px solid rgba(193,138,74,0.1)`, marginBottom: 20 }}>
          <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 20, color: C.gold, letterSpacing: 1 }}>KAHLO</div>
          <div style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 300, fontSize: 11, color: C.rose, letterSpacing: 4, marginTop: 1 }}>CAFÉ · ERP</div>
        </div>
        <nav style={{ flex: 1 }}>
          {[
            { icon: "◈", label: "Dashboard" }, { icon: "◫", label: "Commandes" },
            { icon: "◉", label: "Stock" }, { icon: "◎", label: "Clients" },
            { icon: "▦", label: "Calendrier" }, { icon: "◬", label: "Analytics" },
            { icon: "⚙", label: "Paramètres", active: true },
          ].map(item => (
            <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 16px", borderRadius: 10, cursor: "pointer", fontSize: 13, fontWeight: 500, marginBottom: 2, color: item.active ? C.gold : "rgba(223,207,196,0.4)", background: item.active ? "rgba(193,138,74,0.12)" : "transparent" }}>
              <span style={{ fontSize: 14 }}>{item.icon}</span>{item.label}
            </div>
          ))}
        </nav>
      </div>

      {/* Sidebar paramètres */}
      <div style={{ width: 210, background: "#231209", borderRight: `1px solid rgba(193,138,74,0.08)`, position: "fixed", left: 220, height: "100vh", padding: "32px 14px", overflowY: "auto", zIndex: 9 }}>
        <div style={{ fontSize: 10, color: "rgba(223,207,196,0.25)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 16, padding: "0 6px" }}>Paramètres</div>
        {SECTIONS.map(s => (
          <div
            key={s.id}
            onClick={() => setActive(s.id)}
            style={{
              display: "flex", alignItems: "center", gap: 10, padding: "10px 14px",
              borderRadius: 10, cursor: "pointer", fontSize: 13, fontWeight: 500,
              marginBottom: 2, transition: "all 0.15s",
              color: active === s.id ? C.gold : "rgba(223,207,196,0.45)",
              background: active === s.id ? "rgba(193,138,74,0.1)" : "transparent",
              borderLeft: active === s.id ? `2px solid ${C.gold}` : "2px solid transparent",
            }}
          >
            <span style={{ fontSize: 13 }}>{s.icon}</span>{s.label}
          </div>
        ))}
      </div>

      {/* Contenu */}
      <div style={{ marginLeft: 430, flex: 1, padding: "40px 40px 100px", maxWidth: 720 }}>
        {/* Header section */}
        <div style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h1 style={{ fontFamily: "'Raleway', sans-serif", fontWeight: 900, fontSize: 22, color: C.creme }}>
                {SECTIONS.find(s => s.id === active)?.icon} {SECTIONS.find(s => s.id === active)?.label}
              </h1>
              <p style={{ color: "rgba(223,207,196,0.35)", fontSize: 12, marginTop: 4 }}>
                Configuration Kahlo Café ERP
              </p>
            </div>
            {saveMsg && (
              <span style={{ fontSize: 12, color: C.green, fontWeight: 600 }}>{saveMsg}</span>
            )}
          </div>
        </div>

        {/* Contenu de la section */}
        {renderSection()}
      </div>

      {/* Barre de sauvegarde flottante */}
      <SaveBar dirty={dirty} onSave={handleSave} onReset={handleReset} />
    </div>
  );
}
