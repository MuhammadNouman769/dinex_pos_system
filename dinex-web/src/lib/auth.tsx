"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError, tokens } from "./api";
import type { LocationInfo, Me } from "./types";

interface AuthState {
  me: Me | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  reload: () => Promise<void>;
  /** The location the user is currently working at (POS, orders, stock). */
  location: LocationInfo | null;
  setLocationId: (id: number) => void;
  currency: string;
}

const Ctx = createContext<AuthState | null>(null);
const LOC_KEY = "dinex_location";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [locationId, setLocId] = useState<number | null>(null);

  const loadMe = useCallback(async (): Promise<boolean> => {
    if (!tokens.access) { setMe(null); setLoading(false); return false; }
    // Only a real "not signed in" answer (401/403) may send the user back to the login page.
    // A slow or busy server (network error, 429, 5xx, "database is locked") is retried instead, so a hiccup never looks like a logout.
    const wait = [0, 800, 2000, 4000];
    for (let i = 0; i < wait.length; i++) {
      if (wait[i]) await new Promise((r) => setTimeout(r, wait[i]));
      try {
        setMe(await api.get<Me>("/auth/me/"));
        setLoading(false);
        return true;
      } catch (e) {
        const st = e instanceof ApiError ? e.status : 0;
        if (st === 401 || st === 403 || !tokens.access) { setMe(null); setLoading(false); return false; }
      }
    }
    setLoading(false);   // still unreachable: keep the saved login (tokens stay), the next screen load tries again
    return false;
  }, []);
  const reload = useCallback(async () => { await loadMe(); }, [loadMe]);

  useEffect(() => {
    const saved = Number(localStorage.getItem(LOC_KEY));
    if (saved) setLocId(saved);
    reload();
    const onLogout = () => setMe(null);
    window.addEventListener("dinex:logout", onLogout);
    return () => window.removeEventListener("dinex:logout", onLogout);
  }, [reload]);

  const login = useCallback(async (username: string, password: string) => {
    const t = await api.post<{ access: string; refresh: string }>("/auth/token/", { username, password });
    tokens.set(t.access, t.refresh);
    setLoading(true);
    if (!(await loadMe())) throw new ApiError(0, "Could not load your account. Please press Sign in again.", null);
  }, [loadMe]);

  const logout = useCallback(() => { tokens.clear(); setMe(null); }, []);

  const setLocationId = useCallback((id: number) => { setLocId(id); localStorage.setItem(LOC_KEY, String(id)); }, []);

  const location = useMemo(() => {
    if (!me || me.locations.length === 0) return null;
    return me.locations.find((l) => l.id === locationId) ?? me.locations.find((l) => l.is_primary) ?? me.locations[0];
  }, [me, locationId]);

  const value: AuthState = { me, loading, login, logout, reload, location, setLocationId, currency: me?.organization?.currency ?? "PKR" };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside AuthProvider");
  return v;
}
