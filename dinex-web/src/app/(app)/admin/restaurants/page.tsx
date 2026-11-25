"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { Plus, Search, Store } from "lucide-react";
import { AddRestaurantModal } from "@/components/AddRestaurantModal";
import { STATUS_LABEL, StatusBadge, ago, fmtDate } from "@/components/Platform";
import { Badge, Button, Card, EmptyState, Input, PageHeader, Spinner, cn } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { Paginated, RestaurantRow, SubStatus } from "@/lib/types";

function List() {
  const { me } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const status = (params.get("status") ?? "") as SubStatus | "";
  const [search, setSearch] = useState("");
  const [rows, setRows] = useState<RestaurantRow[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [add, setAdd] = useState(false);

  const load = useCallback(async () => {
    const r = await api.get<Paginated<RestaurantRow>>("/platform/restaurants/", { search, status, page_size: 50 });
    setRows(r.results); setCount(r.count); setLoading(false);
  }, [search, status]);
  useEffect(() => { if (me?.role !== "PLATFORM") return; const t = setTimeout(() => load().catch(() => setLoading(false)), 250); return () => clearTimeout(t); }, [load, me]);

  if (me && me.role !== "PLATFORM") return <EmptyState title="DineX Admin is for XverLabs staff" />;
  const chips: (SubStatus | "")[] = ["", "ACTIVE", "TRIAL", "PAST_DUE", "SUSPENDED", "CANCELLED"];

  return (
    <>
      <PageHeader title="Restaurants" subtitle={`${count} on the platform`} actions={<Button onClick={() => setAdd(true)}><Plus className="h-4 w-4" />Add restaurant</Button>} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] flex-1 sm:max-w-sm"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input aria-label="Search" placeholder="Search name, owner, email…" className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} /></div>
        <div className="flex flex-wrap gap-2">
          {chips.map((c) => (
            <button key={c || "all"} onClick={() => router.push(c ? `/admin/restaurants?status=${c}` : "/admin/restaurants")} className={cn("rounded-full border px-3.5 py-1.5 text-sm font-semibold transition", status === c ? "border-brand bg-brand text-white" : "border-line bg-surface text-muted hover:text-ink")}>{c ? STATUS_LABEL[c] : "All"}</button>
          ))}
        </div>
      </div>

      {loading ? <Spinner /> : rows.length === 0 ? <EmptyState icon={<Store className="h-8 w-8" />} title="No restaurants found" hint="Try another filter, or add the first restaurant." /> : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Restaurant</th><th className="px-5 py-3">Plan</th><th className="px-5 py-3">Status</th><th className="px-5 py-3 text-right">Branches / users</th><th className="px-5 py-3 text-right">Orders (30d)</th><th className="px-5 py-3 text-right">Sales (30d)</th><th className="px-5 py-3">Last order</th></tr></thead>
            <tbody className="divide-y divide-line">
              {rows.map((r) => (
                <tr key={r.id} className="cursor-pointer hover:bg-sunken/50" onClick={() => router.push(`/admin/restaurants/${r.id}`)}>
                  <td className="px-5 py-3"><Link href={`/admin/restaurants/${r.id}`} className="font-semibold hover:text-brand">{r.name}</Link><p className="text-xs text-muted">{r.owner?.name} · joined {fmtDate(r.created_at)}</p></td>
                  <td className="px-5 py-3"><Badge>{r.subscription?.plan_name ?? "-"}</Badge></td>
                  <td className="px-5 py-3"><StatusBadge status={r.subscription?.status} />{r.invoices_due > 0 && <span className="ml-2 text-xs text-warn">{r.invoices_due} due</span>}{!r.is_active && <Badge tone="bad" className="ml-2">Disabled</Badge>}</td>
                  <td className="px-5 py-3 text-right">{r.usage.locations} / {r.usage.users}</td>
                  <td className="px-5 py-3 text-right">{r.usage.orders_30d.toLocaleString()}</td>
                  <td className="px-5 py-3 text-right font-semibold">{money(r.usage.sales_30d)}</td>
                  <td className="px-5 py-3 text-muted">{ago(r.usage.last_order_at)}</td>
                </tr>
              ))}
            </tbody></table></div>
        </Card>
      )}
      <AddRestaurantModal open={add} onClose={() => setAdd(false)} onCreated={load} />
    </>
  );
}

export default function RestaurantsPage() { return <Suspense fallback={<Spinner />}><List /></Suspense>; }
