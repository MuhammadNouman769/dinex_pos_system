"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChefHat, Maximize2, Volume2, VolumeX } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { Badge, Button, EmptyState, PageHeader, Spinner, cn, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import type { Order, TableT } from "@/lib/types";

const COLS = [
  { key: "NEW", title: "New", statuses: ["PENDING", "CONFIRMED"], tone: "warn" as const },
  { key: "PREPARING", title: "Cooking", statuses: ["PREPARING"], tone: "brand" as const },
  { key: "READY", title: "Ready to serve", statuses: ["READY"], tone: "good" as const },
];
const mins = (iso: string, now: number) => Math.max(0, Math.floor((now - new Date(iso).getTime()) / 60000));

function beep() {
  try {
    const C = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const c = new C(), o = c.createOscillator(), g = c.createGain();
    o.connect(g); g.connect(c.destination); o.frequency.value = 880; g.gain.setValueAtTime(0.15, c.currentTime); g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + 0.5);
    o.start(); o.stop(c.currentTime + 0.5);
  } catch { /* sound is optional */ }
}

export default function KitchenPage() {
  const { me, location } = useAuth();
  const { run } = useAction();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [tables, setTables] = useState<TableT[]>([]);
  const [now, setNow] = useState(() => Date.now());
  const [sound, setSound] = useState(true);
  const seen = useRef<Set<number> | null>(null);

  const load = useCallback(async () => {
    if (!location) return;
    const [o, t] = await Promise.all([api.list<Order>("/orders/", { location: location.id }), api.list<TableT>("/orders/tables/", { location: location.id }).catch(() => [] as TableT[])]);
    const live = o.filter((x) => ["PENDING", "CONFIRMED", "PREPARING", "READY"].includes(x.status)).sort((a, b) => a.created_at.localeCompare(b.created_at));
    if (seen.current && sound && live.some((x) => !seen.current!.has(x.id))) beep();
    seen.current = new Set(live.map((x) => x.id));
    setOrders(live); setTables(t); setNow(Date.now());
  }, [location, sound]);
  useEffect(() => { load().catch(() => setOrders([])); const i = setInterval(() => load().catch(() => {}), 8000); return () => clearInterval(i); }, [load]);
  useEffect(() => { const i = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(i); }, []);

  const advance = async (o: Order) => {
    const steps = o.status === "PENDING" ? ["CONFIRMED", "PREPARING"] : o.status === "CONFIRMED" ? ["PREPARING"] : ["READY"];
    const r = await run(async () => { for (const s of steps) await api.post(`/orders/${o.id}/status/`, { status: s }); return true; });
    if (r) load();
  };
  const full = () => { try { void document.documentElement.requestFullscreen?.(); } catch { /* ignore */ } };

  if (me && !me.organization) return <PlatformNotice />;
  return (
    <>
      <PageHeader title="Kitchen" subtitle={`${location?.name} · live tickets, refreshes every few seconds`}
        actions={<><Button variant="ghost" size="sm" onClick={() => setSound((s) => !s)} aria-label={sound ? "Mute new-order sound" : "Unmute"} data-testid="kds-sound">{sound ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}</Button>
          <Button variant="secondary" size="sm" onClick={full}><Maximize2 className="h-4 w-4" />Full screen</Button></>} />
      {orders === null ? <Spinner /> : orders.length === 0 ? <EmptyState icon={<ChefHat className="h-8 w-8" />} title="No orders in the kitchen" hint="New orders from the POS appear here by themselves." /> : (
        <div className="grid gap-4 lg:grid-cols-3" data-testid="kds">
          {COLS.map((c) => {
            const list = orders.filter((o) => c.statuses.includes(o.status));
            return (
              <section key={c.key} data-testid={`kds-col-${c.key}`}>
                <h2 className="mb-2 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-muted">{c.title}<Badge tone={c.tone}>{list.length}</Badge></h2>
                <div className="space-y-3">
                  {list.map((o) => {
                    const age = mins(o.created_at, now);
                    const table = tables.find((t) => t.id === o.table)?.table_number;
                    return (
                      <article key={o.id} data-testid={`kds-${o.order_number}`} className={cn("rounded-2xl border-2 bg-surface p-4 shadow-card", age >= 20 ? "border-bad" : age >= 10 ? "border-warn" : "border-line")}>
                        <div className="flex items-start justify-between gap-2">
                          <div><p className="num text-lg font-extrabold">{o.order_number}</p><p className="text-xs font-medium text-muted">{o.order_type_display}{table ? ` · Table ${table}` : ""}</p></div>
                          <span className={cn("num rounded-full px-2.5 py-1 text-sm font-bold", age >= 20 ? "bg-bad-soft text-bad" : age >= 10 ? "bg-warn-soft text-warn" : "bg-sunken text-muted")}>{age} min</span>
                        </div>
                        <ul className="mt-3 space-y-2">
                          {o.items.map((i) => (
                            <li key={i.id}>
                              <p className="text-base font-bold"><span className="num mr-1.5 text-brand">{i.quantity}×</span>{i.product_name || i.deal_name}{i.variant_name && i.variant_name !== "Regular" ? <small className="font-medium text-muted"> ({i.variant_name})</small> : null}</p>
                              {(i.modifiers ?? []).length > 0 && <p className="pl-7 text-sm text-muted">+ {(i.modifiers ?? []).map((m) => m.name).join(", ")}</p>}
                              {i.notes && <p className="pl-7 text-sm font-bold text-warn">“{i.notes}”</p>}
                            </li>
                          ))}
                        </ul>
                        {o.status !== "READY" && <Button className="mt-4 w-full" size="lg" onClick={() => advance(o)} data-testid="kds-advance">{o.status === "PREPARING" ? "Mark ready" : "Start cooking"}</Button>}
                      </article>
                    );
                  })}
                  {list.length === 0 && <p className="rounded-2xl border border-dashed border-line py-8 text-center text-sm text-muted">Nothing here</p>}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </>
  );
}
