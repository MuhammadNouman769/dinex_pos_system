"use client";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Banknote, ChevronLeft, ChevronRight, Printer, Receipt, ShoppingBasket, TrendingUp } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { Badge, Button, Card, PageHeader, Spinner, Stat, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import { downloadCsv } from "@/lib/csv";
import { printZReport } from "@/lib/zreport";
import type { DayReport } from "@/lib/types";

const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const METHODS: Record<string, string> = { CASH: "Cash", CARD: "Card", WALLET: "JazzCash / Easypaisa", BANK: "Bank transfer" };
const t = (iso: string | null) => (iso ? new Date(iso).toLocaleTimeString("en-PK", { hour: "numeric", minute: "2-digit" }) : "now");

export default function DayReportPage() {
  const { me, location, currency } = useAuth();
  const toast = useToast();
  const [day, setDay] = useState(() => new Date());
  const [r, setR] = useState<DayReport | null>(null);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    if (!location) return;
    setR(null); setErr("");
    try { setR(await api.get<DayReport>("/operations/reports/day/", { location: location.id, date: ymd(day) })); } catch (e) { setErr((e as Error).message); }
  }, [location, day]);
  useEffect(() => { load(); }, [load]);
  const shift = (n: number) => setDay((d) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; });
  const isToday = ymd(day) === ymd(new Date());

  if (me && !me.organization) return <PlatformNotice />;
  const print = () => { if (r && !printZReport(r, { business: me?.organization?.name ?? "", currency })) toast.err("Allow pop-ups to print."); };

  const csv = () => { if (!r) return; downloadCsv(`end-of-day-${r.date}.csv`, [
    ["End of day", r.date, r.locations.join(" / ")], [],
    ["Sales", "Amount"], ...Object.entries(r.by_method).map(([k, v]) => [METHODS[k] ?? k, v]), ["Gross sales", r.sales.gross_sales], ["Refunds", r.sales.refunds], ["Net sales", r.sales.net_sales], ["Orders", r.sales.orders], [],
    ["Expenses", "Amount"], ...r.expenses.by_category.map((c) => [c.category, c.amount]), ["Total expenses", r.expenses.total], [],
    ["Purchases total", r.purchases.total], ["Purchases paid", r.purchases.paid], ["Net after costs", r.net_after_costs], [],
    ["Cashier", "Expected", "Counted", "Difference"], ...r.shifts.map((s) => [s.cashier, s.expected_cash, s.counted_cash, s.difference])]); };
  return (
    <>
      <PageHeader title="End of day" subtitle={`${location?.name} · closing report`} actions={<><Button variant="secondary" onClick={csv} disabled={!r} data-testid="csv-z">Download CSV</Button><Button variant="secondary" onClick={print} disabled={!r} data-testid="print-z"><Printer className="h-4 w-4" />Print report</Button></>} />
      <div className="mb-4 flex items-center gap-2">
        <button aria-label="Previous day" onClick={() => shift(-1)} className="grid h-10 w-10 place-items-center rounded-xl border border-line bg-surface hover:bg-sunken"><ChevronLeft className="h-5 w-5" /></button>
        <div className="min-w-[180px] rounded-xl border border-line bg-surface px-4 py-2 text-center text-sm font-semibold">{isToday ? "Today · " : ""}{day.toLocaleDateString("en-PK", { weekday: "short", day: "numeric", month: "short" })}</div>
        <button aria-label="Next day" disabled={isToday} onClick={() => shift(1)} className="grid h-10 w-10 place-items-center rounded-xl border border-line bg-surface hover:bg-sunken disabled:opacity-40"><ChevronRight className="h-5 w-5" /></button>
      </div>
      {err ? <Card className="p-6 text-sm text-bad">{err}</Card> : !r ? <Spinner /> : (
        <div className="space-y-4">
          {r.open_shifts > 0 && <div className="flex items-start gap-3 rounded-2xl border border-warn bg-warn-soft p-4 text-sm text-warn" data-testid="open-shift-warning"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" /><p><b>{r.open_shifts} shift{r.open_shifts > 1 ? "s are" : " is"} still open.</b> Close {r.open_shifts > 1 ? "them" : "it"} from the Cash desk so the cash count is final.</p></div>}
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Stat label="Net sales" value={<span data-testid="z-net">{money(r.sales.net_sales, currency)}</span>} hint={`${r.sales.orders} order${r.sales.orders === 1 ? "" : "s"}`} icon={<TrendingUp className="h-5 w-5" />} />
            <Stat label="Expenses" value={<span data-testid="z-exp">{money(r.expenses.total, currency)}</span>} icon={<Receipt className="h-5 w-5" />} tone="bad" />
            <Stat label="Stock bought" value={money(r.purchases.total, currency)} hint={Number(r.purchases.unpaid) > 0 ? `${money(r.purchases.unpaid, currency)} still owed` : "fully paid"} icon={<ShoppingBasket className="h-5 w-5" />} tone="warn" />
            <Stat label="Left after costs" value={<span data-testid="z-left">{money(r.net_after_costs, currency)}</span>} hint="sales − expenses − paid purchases" icon={<Banknote className="h-5 w-5" />} tone="good" />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="p-4"><h3 className="mb-3 text-sm font-bold">Sales by payment method</h3>
              {Object.entries(r.by_method).map(([k, v]) => <div key={k} className="flex justify-between border-b border-line py-2 text-sm last:border-0"><span>{METHODS[k] ?? k}</span><span className="num font-semibold">{money(v, currency)}</span></div>)}
              <div className="mt-2 grid grid-cols-3 gap-2 text-center text-xs text-muted"><div><p className="num text-sm font-bold text-ink">{money(r.sales.discounts, currency)}</p>Discounts</div><div><p className="num text-sm font-bold text-ink">{money(r.sales.tax, currency)}</p>Tax</div><div><p className="num text-sm font-bold text-ink">{r.exceptions.cancelled.count}</p>Cancelled</div></div></Card>
            <Card className="p-4"><h3 className="mb-3 text-sm font-bold">Expenses</h3>
              {r.expenses.by_category.length === 0 ? <p className="text-sm text-muted">No expenses recorded.</p> : r.expenses.by_category.map((c) => <div key={c.category} className="flex justify-between border-b border-line py-2 text-sm last:border-0"><span>{c.category}</span><span className="num font-semibold">{money(c.amount, currency)}</span></div>)}</Card>
          </div>
          <Card className="p-4"><h3 className="mb-3 text-sm font-bold">Cash drawers</h3>
            {r.shifts.length === 0 ? <p className="text-sm text-muted">No shifts today.</p> : (
              <div className="overflow-x-auto"><table className="w-full min-w-[520px] text-sm"><thead><tr className="text-left text-xs text-muted"><th className="py-1">Cashier</th><th>Hours</th><th className="text-right">Expected</th><th className="text-right">Counted</th><th className="text-right">Difference</th></tr></thead>
                <tbody>{r.shifts.map((s) => (
                  <tr key={s.id} className="border-t border-line" data-testid={`z-shift-${s.id}`}><td className="py-2 font-medium">{s.cashier}</td><td>{t(s.opened_at)} – {s.still_open ? <Badge tone="warn">open</Badge> : t(s.closed_at)}</td>
                    <td className="num text-right">{money(s.expected_cash, currency)}</td><td className="num text-right">{s.counted_cash !== null ? money(s.counted_cash, currency) : "—"}</td>
                    <td className={`num text-right font-semibold ${Number(s.difference) < 0 ? "text-bad" : Number(s.difference) > 0 ? "text-warn" : ""}`}>{s.difference !== null ? money(s.difference, currency) : "—"}</td></tr>))}</tbody></table></div>)}</Card>
          {r.top_items.length > 0 && <Card className="p-4"><h3 className="mb-3 text-sm font-bold">Best sellers today</h3><div className="grid gap-x-8 sm:grid-cols-2">{r.top_items.slice(0, 6).map((i) => <div key={i.name + i.variant} className="flex justify-between border-b border-line py-2 text-sm"><span>{i.quantity}× {i.name}</span><span className="num text-muted">{money(i.revenue, currency)}</span></div>)}</div></Card>}
          <p className="text-center text-xs text-muted">Reservations today: {r.reservations.total} · seated {r.reservations.seated} · no-show {r.reservations.no_show}</p>
        </div>
      )}
    </>
  );
}
