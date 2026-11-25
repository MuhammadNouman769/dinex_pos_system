"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, CheckCircle2, CircleDashed, ClipboardList, Clock, Flame, PackageCheck } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { Badge, Card, PageHeader, Spinner, Stat } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { Order, Paginated, StockRow } from "@/lib/types";
import { statusTone } from "@/lib/orderStatus";

interface Stats { total_orders: number; total_amount: number; today_orders: number; pending_orders: number; preparing_orders: number; ready_orders: number; completed_orders: number; cancelled_orders: number }

export default function DashboardPage() {
  const { me, location, currency } = useAuth();
  const router = useRouter();
  useEffect(() => { if (me?.role === "PLATFORM") router.replace("/admin"); }, [me, router]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [low, setLow] = useState<StockRow[]>([]);
  const [recent, setRecent] = useState<Order[]>([]);
  const [setup, setSetup] = useState<{ label: string; done: boolean; href: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!me?.organization || !location) { setLoading(false); return; }
    const loc = location.id;
    (async () => {
      const count = async (path: string, q: Record<string, string | number> = {}) => (await api.get<Paginated<unknown>>(path, { page_size: 1, ...q })).count;
      const [s, lowRows, orders, floors, tables, products, ingredients] = await Promise.all([
        api.get<Stats>("/orders/stats/", { location: loc }).catch(() => null),
        api.get<{ results: StockRow[] }>("/inventory/stock/", { location: loc, low: "true" }).then((r) => r.results).catch(() => []),
        api.list<Order>("/orders/", { location: loc, page_size: 6 }).catch(() => []),
        count("/orders/floors/", { location: loc }).catch(() => 0),
        count("/orders/tables/", { location: loc }).catch(() => 0),
        count("/catalog/products/").catch(() => 0),
        count("/inventory/ingredients/").catch(() => 0),
      ]);
      setStats(s); setLow(lowRows); setRecent(orders.slice(0, 6));
      setSetup([
        { label: "Add floors and tables", done: floors > 0 && tables > 0, href: "/setup?step=floors" },
        { label: "Build your menu", done: products > 0, href: "/setup?step=menu" },
        { label: "Add ingredients", done: ingredients > 0, href: "/setup?step=ingredients" },
        { label: "Write recipes so stock updates itself", done: false, href: "/setup?step=recipes" },
      ]);
      setLoading(false);
    })();
  }, [me, location]);

  if (me && !me.organization) return <PlatformNotice />;
  if (loading) return <Spinner label="Loading your day…" />;

  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const cards = [
    { label: "Orders today", value: stats?.today_orders ?? 0, icon: ClipboardList, tone: "text-brand bg-brand-soft" },
    { label: "Waiting", value: stats?.pending_orders ?? 0, icon: Clock, tone: "text-warn bg-warn-soft" },
    { label: "In kitchen", value: (stats?.preparing_orders ?? 0) + (stats?.ready_orders ?? 0), icon: Flame, tone: "text-brand bg-brand-soft" },
    { label: "Completed", value: stats?.completed_orders ?? 0, icon: PackageCheck, tone: "text-good bg-good-soft" },
  ];
  const showChecklist = me?.is_owner && setup.some((s) => !s.done);

  return (
    <>
      <PageHeader title={`${greet}, ${me?.first_name || me?.username}`} subtitle={`${me?.organization?.name} · ${location?.name}`} />

      <div className="grid grid-cols-2 gap-3 md:gap-4 lg:grid-cols-4">
        {cards.map(({ label, value, icon: Icon, tone }) => (
          <Stat key={label} label={label} value={value} icon={<Icon className="h-[18px] w-[18px]" />} tone={tone.includes("good") ? "good" : tone.includes("warn") ? "warn" : "brand"} />
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <h2 className="font-display font-bold">Recent orders</h2>
            <Link href="/orders" className="flex items-center gap-1 text-sm font-semibold text-brand">All orders <ArrowRight className="h-4 w-4" /></Link>
          </div>
          {recent.length === 0 ? <p className="px-5 py-10 text-center text-sm text-muted">No orders yet. Open the POS to take the first one.</p> : (
            <ul className="divide-y divide-line">
              {recent.map((o) => (
                <li key={o.id} className="flex items-center justify-between gap-3 px-5 py-3.5 transition hover:bg-sunken/60">
                  <div className="min-w-0">
                    <p className="font-semibold">{o.order_number}</p>
                    <p className="truncate text-xs text-muted">{o.order_type_display} · {o.items.length} item{o.items.length === 1 ? "" : "s"} · {new Date(o.created_at).toLocaleTimeString("en-PK", { hour: "2-digit", minute: "2-digit" })}</p>
                  </div>
                  <div className="flex items-center gap-3"><span className="num text-sm font-semibold">{money(o.total_amount, currency)}</span><Badge tone={statusTone(o.status)}>{o.status_display}</Badge></div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-6">
          {showChecklist && (
            <Card className="p-5">
              <h2 className="font-display font-bold">Finish setting up</h2>
              <p className="mb-3 text-sm text-muted">A few steps and your restaurant is ready.</p>
              <ul className="space-y-1">
                {setup.map((s) => (
                  <li key={s.label}>
                    <Link href={s.href} className="flex items-center gap-3 rounded-xl px-2 py-2 text-sm hover:bg-sunken">
                      {s.done ? <CheckCircle2 className="h-5 w-5 text-good" /> : <CircleDashed className="h-5 w-5 text-muted" />}
                      <span className={s.done ? "text-muted line-through" : "font-medium"}>{s.label}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          )}
          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between"><h2 className="font-display font-bold">Low stock</h2>{low.length > 0 && <Badge tone="warn">{low.length}</Badge>}</div>
            {low.length === 0 ? <p className="text-sm text-muted">Everything is above its reorder level.</p> : (
              <ul className="space-y-2">
                {low.slice(0, 6).map((r) => (
                  <li key={r.ingredient} className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-warn" />{r.ingredient_name}</span>
                    <span className="font-semibold">{Number(r.quantity).toLocaleString()} {r.base_unit.toLowerCase()}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
