// stores/auth.js — Zustand store pour l'authentification
// Le JWT est stocké dans un cookie HttpOnly (géré par le backend).
// Seuls role et username sont en mémoire/localStorage (affichage UI).
import { create } from "zustand";

function _getCookie(name) {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

export const useAuthStore = create((set, get) => ({
  // Le token n'est plus accessible au JS — seule la présence du cookie CSRF indique une session active
  isAuthenticated: !!_getCookie("kahlo_csrf"),
  role: localStorage.getItem("kahlo_role") || null,
  username: localStorage.getItem("kahlo_username") || null,

  login: (role, username) => {
    if (role) localStorage.setItem("kahlo_role", role);
    if (username) localStorage.setItem("kahlo_username", username);
    set({ isAuthenticated: true, role: role || null, username: username || null });
  },

  logout: () => {
    localStorage.removeItem("kahlo_role");
    localStorage.removeItem("kahlo_username");
    set({ isAuthenticated: false, role: null, username: null });
  },

  isAdmin: () => get().role === "admin",
}));
