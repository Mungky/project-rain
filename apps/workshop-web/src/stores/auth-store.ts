import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AuthUser {
  id: string;
  username: string;
  email: string | null;
  role: "admin" | "user";
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  setAuth: (token: string, user: AuthUser) => void;
  clearAuth: () => void;
  isAdmin: () => boolean;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,

      setAuth: (token, user) => set({ token, user }),
      clearAuth: () => set({ token: null, user: null }),

      isAdmin: () => get().user?.role === "admin",
      isAuthenticated: () => !!get().token,
    }),
    {
      name: "rain-auth",
      partialize: (s) => ({ token: s.token, user: s.user }),
    },
  ),
);
