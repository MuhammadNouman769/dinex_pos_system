"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, tokens } from "./api";
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

  const reload = useCallback(async () => {
    if (!tokens.access) { setMe(null); setLoading(false); return; }
    try {
      setMe(await api.get<Me>("/auth/me/"));
    } catch {
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, []);

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
    await reload();
  }, [reload]);

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
