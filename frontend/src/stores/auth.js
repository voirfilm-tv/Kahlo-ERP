// stores/auth.js — Zustand store pour l'authentification
import { create } from "zustand";

export const useAuthStore = create((set) => ({
  token: localStorage.getItem("kahlo_token"),
  login: (token) => {
    localStorage.setItem("kahlo_token", token);
    set({ token });
  },
  logout: () => {
    localStorage.removeItem("kahlo_token");
    set({ token: null });
  },
}));
