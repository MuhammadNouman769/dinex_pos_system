"use client";
import { useEffect } from "react";

/** Registers the service worker (production only, needs HTTPS or localhost). */
export function ServiceWorker() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    const v = process.env.NEXT_PUBLIC_BUILD_ID ?? "0";
    navigator.serviceWorker.register(`/sw.js?v=${v}`, { scope: "/" }).catch(() => undefined);
  }, []);
  return null;
}
