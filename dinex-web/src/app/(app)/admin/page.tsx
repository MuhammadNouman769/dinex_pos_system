"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, Banknote, Clock, Plus, Receipt, Store, TrendingUp } from "lucide-react";
import { AddRestaurantModal } from "@/components/AddRestaurantModal";
import { StatusBadge, ago, fmtDate } from "@/components/Platform";
import { Badge, Button, Card, EmptyState, PageHeader, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { PlatformOverview } from "@/lib/types";

export default function AdminOverview() {
  const { me } = useAuth();
  const [d, setD] = useState<PlatformOverview | null>(null);
  const [error, setError] = useState("");
  const [add, setAdd] = useState(false);
  const load = () => api.get<PlatformOverview>("/platform/overview/").then(setD).catch((e) => setError(e.message));
  useEffect(() => { if (me?.role === "PLATFORM") load(); }, [me]);

  if (me && me.role !== "PLATFORM") return <EmptyState title="DineX Admin is for XverLabs staff" />;
  if (error) return <EmptyState title="Could not load" hint={error} />;
  if (!d) return <Spinner label="Loading platform…" />;

  const s = d.by_status;
  const kpis = [
    { label: "Monthly recurring revenue", value: money(d.mrr), sub: `${s.ACTIVE + s.PAST_DUE} paying restaurants`, icon: TrendingUp, accent: true },
    { label: "Restaurants", value: String(d.restaurants), sub: `${d.new_this_month} new this month`, icon: Store },
    { label: "Collected this month", value: money(d.collected_this_month), sub: "invoices paid", icon: Banknote },
    { label: "Overdue", value: money(d.overdue.amount), sub: `${d.overdue.count} invoice${d.overdue.count === 1 ? "" : "s"}`, icon: AlertTriangle, warn: d.overdue.count > 0 },
  ];

  return (
    <>
      {d.pending_payments > 0 && (
        <Link href="/admin/payments" className="mb-5 flex items-center justify-between gap-3 rounded-2xl border border-warn/40 bg-warn-soft px-4 py-3 text-sm font-semibold text-warn">
          <span>{d.pending_payments} payment{d.pending_payments === 1 ? "" : "s"} waiting to be checked</span><ArrowRight className="h-4 w-4" />
        </Link>
      )}
      <PageHeader title="DineX Admin" subtitle="All restaurants on the platform" actions={<Button onClick={() => setAdd(true)}><Plus className="h-4 w-4" />Add restaurant</Button>} />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {kpis.map(({ label, value, sub, icon: Icon, accent, warn }) => (
          <Card key={label} className={accent ? "border-brand/40 bg-brand-soft p-5" : "p-5"}>
            <div className={`mb-3 grid h-10 w-10 place-items-center rounded-xl ${accent ? "bg-brand text-white" : warn ? "bg-warn-soft text-warn" : "bg-sunken text-muted"}`}><Icon className="h-5 w-5" /></div>
            <p className={`text-2xl font-bold tracking-tight ${accent ? "text-brand" : warn ? "text-warn" : ""}`}>{value}</p>
            <p className="mt-0.5 text-sm text-muted">{label}</p><p className="text-xs text-muted/80">{sub}</p>
          </Card>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {(["ACTIVE", "TRIAL", "PAST_DUE", "SUSPENDED", "CANCELLED"] as const).map((k) => (
          <Link key={k} href={`/admin/restaurants?status=${k}`} className="flex items-center justify-between rounded-xl border border-line bg-surface px-4 py-3 transition hover:border-brand">
            <StatusBadge status={k} /><span className="text-xl font-bold">{s[k]}</span>
          </Link>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="flex items-center justify-between border-b border-line px-5 py-4"><h2 className="font-bold">Newest restaurants</h2><Link href="/admin/restaurants" className="flex items-center gap-1 text-sm font-semibold text-brand">All <ArrowRight className="h-4 w-4" /></Link></div>
          <ul className="divide-y divide-line">
            {d.recent.map((r) => (
              <li key={r.id}>
                <Link href={`/admin/restaurants/${r.id}`} className="flex items-center justify-between gap-3 px-5 py-3.5 hover:bg-sunken/50">
                  <div className="min-w-0"><p className="font-semibold">{r.name}</p><p className="truncate text-xs text-muted">{r.owner?.name} · joined {fmtDate(r.created_at)} · last order {ago(r.usage.last_order_at)}</p></div>
                  <div className="flex items-center gap-2"><Badge>{r.subscription?.plan_name ?? "-"}</Badge><StatusBadge status={r.subscription?.status} /></div>
                </Link>
              </li>
            ))}
            {d.recent.length === 0 && <li className="px-5 py-10 text-center text-sm text-muted">No restaurants yet.</li>}
          </ul>
        </Card>

        <div className="space-y-6">
          <Card className="p-5">
            <div className="mb-3 flex items-center gap-2"><Clock className="h-4 w-4 text-warn" /><h2 className="font-bold">Trials ending soon</h2></div>
            {d.trials_ending.length === 0 ? <p className="text-sm text-muted">None in the next 7 days.</p> : (
              <ul className="space-y-2 text-sm">{d.trials_ending.map((t) => <li key={t.id}><Link href={`/admin/restaurants/${t.id}`} className="flex justify-between hover:text-brand"><span className="font-semibold">{t.name}</span><span className="text-muted">{fmtDate(t.ends)}</span></Link></li>)}</ul>
            )}
          </Card>
          <Card className="p-5">
            <div className="mb-3 flex items-center gap-2"><Receipt className="h-4 w-4 text-bad" /><h2 className="font-bold">Overdue invoices</h2></div>
            {d.overdue_list.length === 0 ? <p className="text-sm text-muted">Nobody is behind on payment.</p> : (
              <ul className="space-y-2 text-sm">{d.overdue_list.map((i) => <li key={i.id}><Link href={`/admin/restaurants/${i.organization}`} className="flex justify-between hover:text-brand"><span><b>{i.organization_name}</b><span className="block text-xs text-muted">{i.number} · due {fmtDate(i.due_date)}</span></span><span className="font-semibold text-bad">{money(i.amount)}</span></Link></li>)}</ul>
            )}
          </Card>
          <Card className="p-5"><p className="text-sm text-muted">Platform activity, last 30 days</p><p className="mt-1 text-2xl font-bold">{d.orders_30d.toLocaleString()} <span className="text-sm font-medium text-muted">orders</span></p><p className="text-sm text-muted">{money(d.sales_processed_30d)} sales processed</p></Card>
        </div>
      </div>

      <AddRestaurantModal open={add} onClose={() => setAdd(false)} onCreated={load} />
    </>
  );
}
