"use client";
import { useEffect, useState } from "react";

/**
 * Is the server reachable? `navigator.onLine` only says "connected to wifi", not "internet works",
 * so the result of real requests is used too: a failed fetch marks us offline, a good one marks us online.
 */
let reachable = true;
const subs = new Set<() => void>();
const emit = () => subs.forEach((f) => f());

export function markReachable(ok: boolean) { if (reachable !== ok) { reachable = ok; emit(); } }
export function isOnline(): boolean { return reachable && (typeof navigator === "undefined" || navigator.onLine !== false); }

if (typeof window !== "undefined") {
  window.addEventListener("online", () => { reachable = true; emit(); });
  window.addEventListener("offline", () => { reachable = false; emit(); });
}

export function useOnline(): boolean {
  const [v, setV] = useState(true);
  useEffect(() => { const f = () => setV(isOnline()); f(); subs.add(f); return () => { subs.delete(f); }; }, []);
  return v;
}

export function uuid(): string {
  const c: Crypto = crypto;
  if (typeof c.randomUUID === "function") return c.randomUUID();
  const b = new Uint8Array(16); c.getRandomValues(b);
  b[6] = (b[6] & 0x0f) | 0x40; b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0"));
  return `${h.slice(0, 4).join("")}-${h.slice(4, 6).join("")}-${h.slice(6, 8).join("")}-${h.slice(8, 10).join("")}-${h.slice(10).join("")}`;
}
