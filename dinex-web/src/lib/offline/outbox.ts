"use client";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Order, OrderType } from "@/lib/types";
import { idb } from "./idb";
import { isOnline, uuid } from "./status";

/** An order taken on this device that the server has not confirmed yet. */
export interface SyncPayment { method: "CASH" | "CARD" | "WALLET" | "BANK"; amount: string; tendered?: string; reference?: string }
export interface SyncPayload {
  client_uuid: string; location: number; order_type: OrderType; table?: number | null; waiter?: number | null;
  customer_name?: string; customer_phone?: string; customer_email?: string; delivery_address?: string; notes?: string;
  placed_at: string; offline: boolean;
  items: { product_variant: number; quantity: number; notes?: string; modifiers?: number[] }[]; deals: { deal: number; quantity: number }[]; payments: SyncPayment[];
}
export type OutboxStatus = "queued" | "blocked" | "failed";
export interface OutboxEntry {
  client_uuid: string; org: number; location: number; payload: SyncPayload;
  /** What the cashier saw: used for the local bill and the "waiting to sync" list. */
  display: { number: string; type_label: string; total: number; lines: { name: string; qty: number; price: number; mods?: string[]; notes?: string }[]; subtotal: number; tax: number; service: number; discount: number; customer: string };
  status: OutboxStatus; error?: string; attempts: number; created_at: string; table_label?: string;
}
export interface SyncResult { order: Order; created: boolean; stock_warnings: string[]; payment_warnings: string[] }

const EVT = "dinex:outbox";
const changed = () => { if (typeof window !== "undefined") window.dispatchEvent(new Event(EVT)); };

export const outbox = {
  all: () => idb.all<OutboxEntry>("outbox").then((r) => r.sort((a, b) => a.created_at.localeCompare(b.created_at))),
  async add(e: OutboxEntry) { const ok = await idb.put("outbox", e); changed(); if (!ok) throw new Error("This device could not save the order. Free some space or use another browser."); },
  async update(e: OutboxEntry) { await idb.put("outbox", e); changed(); },
  async remove(id: string) { await idb.del("outbox", id); changed(); },
};

/** Temporary bill number for an order made offline, e.g. OFF-1122-003. Replaced by the real number after sync. */
export async function nextOfflineNumber(): Promise<string> {
  const d = new Date();
  const day = `${String(d.getMonth() + 1).padStart(2, "0")}${String(d.getDate()).padStart(2, "0")}`;
  const cur = await idb.get<{ day: string; n: number }>("kv", "offline_counter");
  const n = cur && cur.day === day ? cur.n + 1 : 1;
  await idb.put("kv", { day, n }, "offline_counter");
  return `OFF-${day}-${String(n).padStart(3, "0")}`;
}

export const newOrderId = uuid;

/** Send ONE whole order. Repeating the same client_uuid is safe: the server returns the order it already made. */
export function sendOrder(payload: SyncPayload, timeoutMs?: number) {
  return api.post<SyncResult>("/orders/sync/", payload, timeoutMs ? { timeoutMs } : undefined);
}

let flushing = false;
const listeners = new Set<(r: { synced: number; failed: number }) => void>();
export const onSynced = (f: (r: { synced: number; failed: number }) => void) => { listeners.add(f); return () => { listeners.delete(f); }; };

/** Try to send everything waiting for this restaurant. Stops at the first network problem. */
export async function flush(orgId: number): Promise<{ synced: number; failed: number }> {
  const out = { synced: 0, failed: 0 };
  if (flushing || !isOnline()) return out;
  const run = async () => {
    flushing = true;
    try {
      for (const e of await outbox.all()) {
        if (e.org !== orgId || e.status === "failed") continue;
        try {
          await sendOrder(e.payload, 20000);
          await outbox.remove(e.client_uuid);
          out.synced++;
        } catch (err) {
          if (err instanceof ApiError && err.status === 0) break;                          // still offline: keep everything, try later
          if (err instanceof ApiError && err.status === 402) { await outbox.update({ ...e, status: "blocked", error: err.message, attempts: e.attempts + 1 }); break; }
          if (err instanceof ApiError && (err.status >= 500 || err.status === 429)) { await outbox.update({ ...e, attempts: e.attempts + 1, error: err.message }); break; }
          if (err instanceof ApiError && err.status === 401) break;                         // signed out: keep the order, retry after login
          await outbox.update({ ...e, status: "failed", error: err instanceof Error ? err.message : "Rejected by the server", attempts: e.attempts + 1 });
          out.failed++;
        }
      }
    } finally { flushing = false; }
  };
  // Two browser tabs must not send at the same time (the server would still de-duplicate, this just avoids wasted calls).
  const locks = typeof navigator !== "undefined" ? (navigator as Navigator & { locks?: LockManager }).locks : undefined;
  if (locks) await locks.request("dinex-sync", { ifAvailable: true }, async (lock) => { if (lock) await run(); });
  else await run();
  if (out.synced || out.failed) listeners.forEach((f) => f(out));
  return out;
}

/** Entries of this restaurant, live. */
export function useOutbox(orgId: number | undefined) {
  const [rows, setRows] = useState<OutboxEntry[]>([]);
  const refresh = useCallback(() => { outbox.all().then((r) => setRows(orgId ? r.filter((e) => e.org === orgId) : [])); }, [orgId]);
  useEffect(() => {
    refresh();
    window.addEventListener(EVT, refresh);
    window.addEventListener("storage", refresh);
    return () => { window.removeEventListener(EVT, refresh); window.removeEventListener("storage", refresh); };
  }, [refresh]);
  return { rows, pending: rows.filter((r) => r.status !== "failed").length, failed: rows.filter((r) => r.status === "failed").length, refresh };
}

/** Pending count across ALL restaurants on this device (used to warn before logging out). */
export async function pendingCount() { return (await outbox.all()).filter((e) => e.status !== "failed").length; }
