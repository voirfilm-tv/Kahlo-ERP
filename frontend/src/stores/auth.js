// stores/auth.js — Zustand store pour l'authentification
import { create } from "zustand";

export const useAuthStore = create((set) => ({
  token: localStorage.getItem("kahlo_token"),
  role: localStorage.getItem("kahlo_role") || null,
  username: localStorage.getItem("kahlo_username") || null,
  login: (token, role, username) => {
    localStorage.setItem("kahlo_token", token);
    if (role) localStorage.setItem("kahlo_role", role);
    if (username) localStorage.setItem("kahlo_username", username);
    set({ token, role: role || null, username: username || null });
  },
  logout: () => {
    localStorage.removeItem("kahlo_token");
    localStorage.removeItem("kahlo_role");
    localStorage.removeItem("kahlo_username");
    set({ token: null, role: null, username: null });
  },
  isAdmin: () => localStorage.getItem("kahlo_role") === "admin",
}));
