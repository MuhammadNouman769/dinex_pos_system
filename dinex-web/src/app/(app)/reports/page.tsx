"use client";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Ban, BarChart3, Undo2 } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { Badge, Button, Card, EmptyState, Input, PageHeader, Spinner, cn } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { AuditRow, Paginated, PayMethod, SalesReport } from "@/lib/types";

const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const daysAgo = (n: number) => { const d = new Date(); d.setDate(d.getDate() - n); return iso(d); };
const PRESETS = [
  { label: "Today", from: () => iso(new Date()), to: () => iso(new Date()) },
  { label: "Yesterday", from: () => daysAgo(1), to: () => daysAgo(1) },
  { label: "Last 7 days", from: () => daysAgo(6), to: () => iso(new Date()) },
  { label: "Last 30 days", from: () => daysAgo(29), to: () => iso(new Date()) },
];
const METHOD: Record<PayMethod, string> = { CASH: "Cash", CARD: "Card", WALLET: "JazzCash / Easypaisa", BANK: "Bank transfer" };
const dt = (s: string) => new Date(s).toLocaleString("en-PK", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const ACTION: Record<string, string> = {
  refund: "Refund given", order_cancelled: "Order cancelled", discount: "Discount applied", shift_opened: "Shift opened", shift_closed: "Shift closed",
  shift_reopened: "Shift reopened", cash_expense: "Expense from drawer", cash_cash_out: "Cash taken out", cash_safe_drop: "Moved to safe", cash_cash_in: "Cash added",
};

export default function ReportsPage() {
  const { me, location, currency } = useAuth();
  const [tab, setTab] = useState<"sales" | "audit">("sales");
  const [from, setFrom] = useState(iso(new Date()));
  const [to, setTo] = useState(iso(new Date()));
  const [data, setData] = useState<SalesReport | null>(null);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!location) return;
    setLoading(true); setError("");
    try {
      if (tab === "sales") setData(await api.get<SalesReport>("/cash/reports/sales/", { location: location.id, from, to }));
      else setAudit((await api.get<Paginated<AuditRow>>("/cash/audit/", { page_size: 60 })).results);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load the report."); }
    finally { setLoading(false); }
  }, [location, from, to, tab]);
  useEffect(() => { load(); }, [load]);

  if (me && !me.organization) return <PlatformNotice />;
  if (!me?.can_view_reports) return <EmptyState title="Reports are for owners and managers" />;

  const s = data?.summary;
  const hours = data ? data.by_hour.filter((h) => h.orders > 0) : [];
  const hFrom = hours.length ? hours[0].hour : 0, hTo = hours.length ? hours[hours.length - 1].hour : 0;
  const hourRows = data ? data.by_hour.filter((h) => h.hour >= hFrom && h.hour <= hTo) : [];
  const maxHour = Math.max(1, ...hourRows.map((h) => h.orders));
  const maxDay = Math.max(1, ...(data?.by_day.map((d) => Number(d.net)) ?? [1]));

  return (
    <>
      <PageHeader title="Reports" subtitle={`${location?.name} · sales, profit and anything unusual`} />
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-xl bg-sunken p-1">
          {([["sales", "Sales"], ["audit", "Audit log"]] as const).filter(([id]) => id === "sales" || me.is_owner).map(([id, label]) => (
            <button key={id} onClick={() => setTab(id)} className={cn("rounded-lg px-4 py-2 text-sm font-semibold transition", tab === id ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink")}>{label}</button>
          ))}
        </div>
        {tab === "sales" && (
          <div className="flex flex-wrap items-center gap-2">
            {PRESETS.map((p) => <button key={p.label} onClick={() => { setFrom(p.from()); setTo(p.to()); }} className={cn("rounded-full border px-3.5 py-1.5 text-sm font-semibold transition", from === p.from() && to === p.to() ? "border-brand bg-brand text-white" : "border-line bg-surface text-muted hover:text-ink")}>{p.label}</button>)}
            <Input aria-label="From" type="date" className="w-40" value={from} max={to} onChange={(e) => setFrom(e.target.value)} />
            <Input aria-label="To" type="date" className="w-40" value={to} min={from} onChange={(e) => setTo(e.target.value)} />
          </div>
        )}
      </div>

      {error ? <EmptyState title="Could not load" hint={error} action={<Button onClick={load}>Try again</Button>} /> : loading ? <Spinner label="Crunching the numbers…" /> : tab === "audit" ? (
        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4"><h2 className="font-bold">Audit log</h2><p className="text-sm text-muted">Every refund, cancellation, discount and shift. It cannot be edited.</p></div>
          <ul className="divide-y divide-line">
            {audit.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm">
                <div><p className="font-semibold">{ACTION[a.action] ?? a.action}{a.details.order_number ? ` · ${String(a.details.order_number)}` : ""}</p>
                  <p className="text-xs text-muted">{a.user ?? "system"} · {a.location}{a.details.reason ? ` · “${String(a.details.reason)}”` : ""}{a.details.difference !== undefined ? ` · difference ${String(a.details.difference)}` : ""}{a.details.amount !== undefined ? ` · ${money(String(a.details.amount), currency)}` : ""}</p></div>
                <span className="text-xs text-muted">{dt(a.created_at)}</span>
              </li>
            ))}
            {audit.length === 0 && <li className="px-5 py-10 text-center text-sm text-muted">Nothing recorded yet.</li>}
          </ul>
        </Card>
      ) : data && s ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Kpi label="Net sales" value={money(s.net_sales, currency)} sub={Number(s.refunds) > 0 ? `after ${money(s.refunds, currency)} refunds` : `${s.orders} orders`} accent />
            <Kpi label="Orders" value={String(s.orders)} sub={`avg ${money(s.average_order, currency)}`} />
            <Kpi label="Food cost" value={money(s.food_cost, currency)} sub="from your recipes" />
            <Kpi label="Food profit" value={money(s.food_profit, currency)} sub={Number(s.food_cost) > 0 ? "sales − discounts − food cost" : "add recipes for accurate profit"} />
          </div>

          {data.items_without_recipe.length > 0 && (
            <div className="flex items-start gap-3 rounded-2xl bg-warn-soft p-4 text-sm text-warn"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              <p><b>Profit is overstated.</b> These dishes sold but have no recipe yet: {data.items_without_recipe.slice(0, 6).join(", ")}{data.items_without_recipe.length > 6 ? "…" : ""}. Add recipes in Setup so food cost is counted.</p></div>
          )}

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="p-5">
              <h2 className="mb-3 font-bold">How customers paid</h2>
              {(Object.keys(METHOD) as PayMethod[]).map((m) => {
                const v = Number(data.by_method[m]); const pct = Number(s.net_sales) > 0 ? Math.max(0, (v / Number(s.net_sales)) * 100) : 0;
                return <div key={m} className="mb-3"><div className="mb-1 flex justify-between text-sm"><span className="text-muted">{METHOD[m]}</span><span className="font-semibold">{money(v, currency)}</span></div><div className="h-2 overflow-hidden rounded-full bg-sunken"><div className="h-full rounded-full bg-brand" style={{ width: `${pct}%` }} /></div></div>;
              })}
              <dl className="mt-4 space-y-1.5 border-t border-line pt-3 text-sm text-muted">
                <div className="flex justify-between"><dt>Tax collected</dt><dd className="font-medium text-ink">{money(s.tax, currency)}</dd></div>
                <div className="flex justify-between"><dt>Service charge</dt><dd className="font-medium text-ink">{money(s.service_charge, currency)}</dd></div>
                <div className="flex justify-between"><dt>Discounts given</dt><dd className="font-medium text-ink">{money(s.discounts, currency)}</dd></div>
              </dl>
            </Card>

            <Card className="p-5 lg:col-span-2">
              <h2 className="mb-4 font-bold">{data.by_day.length > 1 ? "Sales by day" : "Busy hours"}</h2>
              {data.by_day.length > 1 ? (
                <div className="flex h-44 items-end gap-1.5 overflow-x-auto pb-1">
                  {data.by_day.map((d) => (
                    <div key={d.date} className="flex min-w-[28px] flex-1 flex-col items-center justify-end gap-1" title={`${d.date}: ${money(d.net, currency)}`}>
                      <div className="w-full rounded-t-lg bg-brand/80 transition hover:bg-brand" style={{ height: `${Math.max(3, (Number(d.net) / maxDay) * 150)}px` }} />
                      <span className="text-[10px] text-muted">{d.date.slice(8)}</span>
                    </div>
                  ))}
                </div>
              ) : hourRows.length === 0 ? <p className="py-10 text-center text-sm text-muted">No sales in this period.</p> : (
                <div className="flex h-44 items-end gap-1.5">
                  {hourRows.map((h) => (
                    <div key={h.hour} className="flex flex-1 flex-col items-center justify-end gap-1" title={`${h.hour}:00 · ${h.orders} orders`}>
                      <span className="text-[10px] font-semibold">{h.orders || ""}</span>
                      <div className="w-full rounded-t-lg bg-brand/80" style={{ height: `${Math.max(3, (h.orders / maxHour) * 120)}px` }} />
                      <span className="text-[10px] text-muted">{h.hour}h</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          <Card className="overflow-hidden">
            <div className="border-b border-line px-5 py-4"><h2 className="font-bold">Best sellers</h2></div>
            <div className="overflow-x-auto"><table className="w-full text-sm">
              <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Dish</th><th className="px-5 py-3 text-right">Sold</th><th className="px-5 py-3 text-right">Revenue</th><th className="px-5 py-3 text-right">Food cost</th><th className="px-5 py-3 text-right">Profit</th></tr></thead>
              <tbody className="divide-y divide-line">
                {data.top_items.map((i, k) => (
                  <tr key={k}><td className="px-5 py-3 font-semibold">{i.name}{i.variant !== "Regular" ? ` · ${i.variant}` : ""}</td><td className="px-5 py-3 text-right">{i.quantity}</td><td className="px-5 py-3 text-right">{money(i.revenue, currency)}</td>
                    <td className="px-5 py-3 text-right text-muted">{i.cost !== null ? money(i.cost, currency) : <Badge tone="warn">no recipe</Badge>}</td><td className="px-5 py-3 text-right font-semibold text-good">{i.profit !== null ? money(i.profit, currency) : "-"}</td></tr>
                ))}
                {data.top_items.length === 0 && <tr><td colSpan={5} className="px-5 py-8 text-center text-muted">No sales in this period.</td></tr>}
              </tbody></table></div>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="overflow-hidden">
              <div className="flex items-center gap-2 border-b border-line px-5 py-4"><Ban className="h-4 w-4 text-bad" /><h2 className="font-bold">Cancelled orders</h2><Badge tone={data.exceptions.cancelled.count ? "bad" : "good"}>{data.exceptions.cancelled.count} · {money(data.exceptions.cancelled.total, currency)}</Badge></div>
              <ul className="divide-y divide-line text-sm">
                {data.exceptions.cancelled.orders.map((o) => <li key={o.order_number} className="px-5 py-3"><div className="flex justify-between"><span className="font-semibold">{o.order_number}</span><span>{money(o.total, currency)}</span></div><p className="text-xs text-muted">{o.by ?? "?"} · {dt(o.at)} · “{o.reason}”</p></li>)}
                {data.exceptions.cancelled.orders.length === 0 && <li className="px-5 py-8 text-center text-muted">None. 👌</li>}
              </ul>
            </Card>
            <Card className="overflow-hidden">
              <div className="flex items-center gap-2 border-b border-line px-5 py-4"><Undo2 className="h-4 w-4 text-warn" /><h2 className="font-bold">Refunds</h2><Badge tone={data.exceptions.refunds.count ? "warn" : "good"}>{data.exceptions.refunds.count} · {money(data.exceptions.refunds.total, currency)}</Badge></div>
              <ul className="divide-y divide-line text-sm">
                {data.exceptions.refunds.list.map((r, i) => <li key={i} className="px-5 py-3"><div className="flex justify-between"><span className="font-semibold">{r.order_number}</span><span>{money(r.amount, currency)} · {METHOD[r.method]}</span></div><p className="text-xs text-muted">{r.by} · {dt(r.at)} · “{r.reason}”</p></li>)}
                {data.exceptions.refunds.list.length === 0 && <li className="px-5 py-8 text-center text-muted">None. 👌</li>}
              </ul>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="overflow-hidden">
              <div className="border-b border-line px-5 py-4"><h2 className="font-bold">By cashier</h2></div>
              <table className="w-full text-sm"><thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Cashier</th><th className="px-5 py-3 text-right">Net sales</th><th className="px-5 py-3 text-right">Refunds</th><th className="px-5 py-3 text-right">Cancels</th></tr></thead>
                <tbody className="divide-y divide-line">{data.cashiers.map((c) => <tr key={c.username}><td className="px-5 py-3 font-semibold">{c.username}</td><td className="px-5 py-3 text-right">{money(c.net_sales, currency)}</td><td className="px-5 py-3 text-right">{c.refunds}</td><td className="px-5 py-3 text-right">{c.cancellations}</td></tr>)}
                  {data.cashiers.length === 0 && <tr><td colSpan={4} className="px-5 py-8 text-center text-muted">No activity.</td></tr>}</tbody></table>
            </Card>
            <Card className="overflow-hidden">
              <div className="border-b border-line px-5 py-4"><h2 className="font-bold">Cash drawer differences</h2></div>
              <ul className="divide-y divide-line text-sm">
                {data.shift_differences.map((d) => <li key={d.id} className="flex items-center justify-between px-5 py-3"><div><p className="font-semibold">{d.cashier}</p><p className="text-xs text-muted">{dt(d.closed_at)} · expected {money(d.expected, currency)}, counted {money(d.counted, currency)}</p></div><Badge tone={Number(d.difference) < 0 ? "bad" : "warn"}>{Number(d.difference) > 0 ? "+" : "−"}{money(Math.abs(Number(d.difference)), currency)}</Badge></li>)}
                {data.shift_differences.length === 0 && <li className="px-5 py-8 text-center text-muted">Every closed shift balanced. 👌</li>}
              </ul>
            </Card>
          </div>
        </div>
      ) : <EmptyState icon={<BarChart3 className="h-8 w-8" />} title="No data" />}
    </>
  );
}

function Kpi({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return <Card className={cn("p-5", accent && "border-brand/40 bg-brand-soft")}><p className={cn("text-sm font-medium", accent ? "text-brand" : "text-muted")}>{label}</p><p className={cn("mt-1 text-2xl font-bold tracking-tight", accent && "text-brand")}>{value}</p>{sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}</Card>;
}
