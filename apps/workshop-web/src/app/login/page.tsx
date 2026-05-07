"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { apiUrl, ApiError } from "@/lib/api-client";
import { useAuthStore, type AuthUser } from "@/stores/auth-store";
import { RainBackdrop } from "@/components/identity/rain-backdrop";
import { GlassPanel } from "@/components/identity/glass-panel";

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      // OAuth2 form login
      const form = new URLSearchParams();
      form.set("username", username);
      form.set("password", password);

      const tokenRes = await fetch(apiUrl("/v1/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form.toString(),
      });

      if (!tokenRes.ok) {
        setError("Username atau password salah.");
        return;
      }

      const { access_token } = (await tokenRes.json()) as { access_token: string };

      // Fetch user profile
      const meRes = await fetch(apiUrl("/v1/auth/me"), {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      const user = (await meRes.json()) as AuthUser;

      setAuth(access_token, user);
      router.replace("/chat");
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Terjadi kesalahan. Coba lagi.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center">
      <RainBackdrop />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-sm px-4"
      >
        <GlassPanel className="p-8 border-white/10 bg-white/5 backdrop-blur-3xl">
          {/* Logo / title */}
          <div className="mb-8 text-center">
            <p className="text-[10px] font-mono uppercase tracking-[0.4em] text-white/30 mb-3">
              Rain OS
            </p>
            <h1 className="text-3xl font-bold tracking-tighter text-white">
              Sign in
            </h1>
            <p className="text-xs text-white/40 mt-2">
              Enter your credentials to continue
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/30">
                Username
              </label>
              <input
                type="text"
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-white/30 transition-all"
                placeholder="username"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/30">
                Password
              </label>
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-white/30 transition-all"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-xs text-rose-400 text-center py-2 px-3 rounded-lg bg-rose-500/10 border border-rose-500/20"
              >
                {error}
              </motion.p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-xl bg-white text-black text-sm font-bold hover:bg-white/90 disabled:opacity-50 transition-all mt-2"
            >
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        </GlassPanel>
      </motion.div>
    </div>
  );
}
