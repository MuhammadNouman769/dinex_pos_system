"use client";
import { useCallback, useEffect, useState } from "react";
import { Ban, Bike, ChefHat, ArrowRightLeft, Scissors, Minus, Plus, ClipboardList, HandCoins, Printer, RefreshCw, Undo2, UserRound } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { useOutboxFor } from "@/components/SyncPill";
import { CloudOff } from "lucide-react";
import { TablePicker } from "@/components/TablePicker";
import { PayModal } from "@/components/PayModal";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Select, Spinner, cn, useAction, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import { onSynced } from "@/lib/offline/outbox";
import { canCancel, nextStep, statusTone } from "@/lib/orderStatus";
import { printReceipt } from "@/lib/receipt";
import { downloadCsv } from "@/lib/csv";
import { printKot } from "@/lib/kot";
import type { Order, OrderMoney, PayMethod, RiderRow, TableT } from "@/lib/types";

const TABS = [
  { id: "active", label: "Active", statuses: ["PENDING", "CONFIRMED", "PREPARING", "READY", "OUT_FOR_DELIVERY"] },
  { id: "done", label: "Completed", statuses: ["COMPLETED"] },
  { id: "cancelled", label: "Cancelled", statuses: ["CANCELLED"] },
] as const;
const REASONS = ["Customer left / changed mind", "Wrong order entered", "Item not available", "Duplicate order", "Kitchen problem", "Other"];
const PAY_BADGE: Record<Order["payment_status"], { label: string; tone: "neutral" | "warn" | "good" | "bad" }> = {
  PENDING: { label: "Unpaid", tone: "neutral" }, PARTIAL: { label: "Part paid", tone: "warn" }, PAID: { label: "Paid", tone: "good" },
  REFUNDED: { label: "Refunded", tone: "bad" }, FAILED: { label: "Failed", tone: "bad" },
};

export default function OrdersPage() {
  const { me, location, currency } = useAuth();
  const toast = useToast();
  const { run, busy } = useAction();
  const box = useOutboxFor();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("active");
  const [working, setWorking] = useState<number | null>(null);
  const [payFor, setPayFor] = useState<Order | null>(null);
  const [cancelFor, setCancelFor] = useState<Order | null>(null);
  const [reasonPick, setReasonPick] = useState(REASONS[0]);
  const [reasonText, setReasonText] = useState("");
  const [riders, setRiders] = useState<RiderRow[]>([]);
  const [assignFor, setAssignFor] = useState<Order | null>(null);
  const [refundFor, setRefundFor] = useState<Order | null>(null);
  const [refund, setRefund] = useState<{ method: PayMethod; amount: string; reason: string; paid: number }>({ method: "CASH", amount: "", reason: "", paid: 0 });

  const [tables, setTables] = useState<TableT[]>([]);
  const [moveFor, setMoveFor] = useState<Order | null>(null);
  const [splitFor, setSplitFor] = useState<Order | null>(null);
  const [picks, setPicks] = useState<Record<number, number>>({});
  const tableName = (id: number | null | undefined) => tables.find((t) => t.id === id)?.table_number;

  const load = useCallback(async () => {
    if (!location) return;
    try {
      setOrders(await api.list<Order>("/orders/", { location: location.id }));
      setTables(await api.list<TableT>("/orders/tables/", { location: location.id }).catch(() => []));
      setRiders(await api.get<RiderRow[]>("/staff/riders/", { location: location.id }).catch(() => []));
    }
    catch (e) { toast.err(e instanceof Error ? e.message : "Could not load orders."); }
    finally { setLoading(false); }
  }, [location, toast]);

  useEffect(() => onSynced(() => { load(); }), [load]);
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, [load]);

  async function move(o: Order, to: string, reason = "") {
    setWorking(o.id);
    const r = await run(() => api.post<{ stock_warnings?: string[] }>(`/orders/${o.id}/status/`, { status: to, reason }));
    if (r?.stock_warnings?.length) toast.err("Low stock: " + r.stock_warnings.join("; "));
    setWorking(null);
    load();
    return r;
  }
  async function assign(rider: number | null) {
    if (!assignFor) return;
    const r = await run(() => api.post(`/staff/orders/${assignFor.id}/assign-rider/`, { rider }), rider ? "Rider assigned" : "Rider removed");
    if (r) { setAssignFor(null); load(); }
  }
  async function confirmCancel() {
    if (!cancelFor) return;
    const reason = reasonPick === "Other" ? reasonText.trim() : reasonText.trim() ? `${reasonPick}: ${reasonText.trim()}` : reasonPick;
    const r = await move(cancelFor, "CANCELLED", reason);
    if (r) { setCancelFor(null); setReasonText(""); setReasonPick(REASONS[0]); }
  }
  async function doMove(t: TableT) {
    if (!moveFor) return;
    const r = await run(() => api.post(`/orders/${moveFor.id}/transfer-table/`, { table: t.id }), `Moved to table ${t.table_number}`);
    if (r) { setMoveFor(null); load(); }
  }
  async function doSplit() {
    if (!splitFor) return;
    const items = Object.entries(picks).filter(([, q]) => q > 0).map(([item, quantity]) => ({ item: Number(item), quantity }));
    const r = await run(() => api.post<{ order: Order; new_order: Order }>(`/orders/${splitFor.id}/split/`, { items }));
    if (r) { toast.ok(`New bill ${r.new_order.order_number} created`); setSplitFor(null); setPicks({}); load(); }
  }
  async function openRefund(o: Order) {
    const info = await run(() => api.get<{ order: OrderMoney }>(`/cash/orders/${o.id}/payments/`));
    if (!info) return;
    const net = Number(info.order.paid) - Number(info.order.refunded);
    setRefund({ method: "CASH", amount: String(net), reason: "", paid: net });
    setRefundFor(o);
  }
  async function confirmRefund() {
    const r = await run(() => api.post(`/cash/orders/${refundFor!.id}/refund/`, { method: refund.method, amount: refund.amount, reason: refund.reason }), "Refund recorded");
    if (r) { setRefundFor(null); load(); }
  }

  if (me && !me.organization) return <PlatformNotice />;
  if (loading) return <Spinner label="Loading orders…" />;

  const statuses = TABS.find((t) => t.id === tab)!.statuses as readonly string[];
  const shown = orders.filter((o) => statuses.includes(o.status));
  const countOf = (id: string) => orders.filter((o) => (TABS.find((t) => t.id === id)!.statuses as readonly string[]).includes(o.status)).length;
  const isManager = !!me?.can_view_reports;

  return (
    <>
      <PageHeader title="Orders" subtitle={`${location?.name} · refreshes automatically`} actions={<><Button variant="secondary" data-testid="csv-orders" onClick={() => downloadCsv("orders.csv", [["Order", "Date", "Type", "Status", "Payment", "Total"], ...orders.map((o) => [o.order_number, o.created_at, o.order_type_display, o.status, o.payment_status, o.total_amount])])}>Download CSV</Button><Button variant="secondary" onClick={load}><RefreshCw className="h-4 w-4" />Refresh</Button></>} />

      {box.rows.length > 0 && (
        <div className="mb-5 rounded-2xl bg-warn-soft p-4 text-warn" data-testid="outbox-strip">
          <p className="flex items-center gap-2 text-sm font-bold"><CloudOff className="h-4 w-4" />{box.rows.length} order{box.rows.length > 1 ? "s" : ""} waiting to sync</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {box.rows.map((r) => <li key={r.client_uuid} className="rounded-full bg-surface/70 px-3 py-1 text-xs font-semibold">{r.display.number} · {money(r.display.total, currency)}{r.status === "failed" ? " · needs attention" : ""}</li>)}
          </ul>
          <p className="mt-2 text-xs">They appear in the list below as soon as they reach the server. Use the sync button in the top bar to retry or review.</p>
        </div>
      )}

      <div className="mb-5 inline-flex rounded-xl bg-sunken p-1">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={cn("rounded-lg px-4 py-2 text-sm font-semibold transition", tab === t.id ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink")}>
            {t.label} <span className="ml-1 text-xs opacity-60">{countOf(t.id)}</span>
          </button>
        ))}
      </div>

      {shown.length === 0 ? <EmptyState icon={<ClipboardList className="h-8 w-8" />} title="Nothing here" hint={tab === "active" ? "New orders from the POS appear here for the kitchen." : undefined} /> : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {shown.map((o) => {
            const step = nextStep(o);
            const unpaid = o.status !== "CANCELLED" && Number(o.total_amount) > 0 && o.payment_status !== "PAID";
            const isDelivery = o.order_type === "DELIVERY";
            const codWithRider = isDelivery && o.status === "OUT_FOR_DELIVERY";           // the rider collects the cash
            const needsPaymentFirst = step?.to === "COMPLETED" && unpaid && !codWithRider;
            const needsRider = isDelivery && step?.to === "OUT_FOR_DELIVERY" && !o.rider;
            const cashWithRider = isDelivery && o.status === "COMPLETED" && unpaid;
            const canRefund = isManager && (o.payment_status === "PAID" || o.payment_status === "PARTIAL");
            const pay = PAY_BADGE[o.payment_status];
            return (
              <Card key={o.id} className="flex flex-col p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-lg font-bold">{o.order_number}</p>
                    <p className="text-xs text-muted">{o.order_type_display}{tableName(o.table) ? ` · Table ${tableName(o.table)}` : ""}{o.customer_name ? ` · ${o.customer_name}` : ""} · {new Date(o.created_at).toLocaleTimeString("en-PK", { hour: "2-digit", minute: "2-digit" })}</p>
                    {o.waiter_name && <p className="mt-0.5 flex items-center gap-1 text-xs font-medium text-muted"><UserRound className="h-3 w-3" />Waiter: {o.waiter_name}</p>}
                    {o.order_type === "DELIVERY" && <p className="mt-0.5 flex items-center gap-1 text-xs font-medium"><Bike className="h-3 w-3 text-brand" />{o.rider_name ? <span>Rider: <b>{o.rider_name}</b></span> : <span className="text-warn">No rider yet</span>}</p>}
                  </div>
                  <div className="flex flex-col items-end gap-1"><Badge tone={statusTone(o.status)}>{o.status_display}</Badge>{o.status !== "CANCELLED" && <Badge tone={pay.tone}>{pay.label}</Badge>}</div>
                </div>
                <ul className="my-4 flex-1 space-y-1.5 text-sm">
                  {o.items.map((i) => (
                    <li key={i.id} className="flex justify-between gap-3"><div className="min-w-0"><span><b>{i.quantity}×</b> {i.product_name}{i.variant_name && i.variant_name !== "Regular" ? ` · ${i.variant_name}` : ""}</span>
                      {(i.modifiers ?? []).length > 0 && <span className="block text-xs text-muted">+ {(i.modifiers ?? []).map((m) => m.name).join(", ")}</span>}
                      {i.notes && <span className="block text-xs font-medium text-warn">“{i.notes}”</span>}</div><span className="text-muted">{money(i.total_price, currency)}</span></li>
                  ))}
                  {o.items.length === 0 && <li className="text-muted">No items</li>}
                  {o.notes && <li className="rounded-lg bg-warn-soft px-2 py-1 text-xs text-warn">Note: {o.notes}</li>}
                </ul>
                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3">
                  <span className="font-bold">{money(o.total_amount, currency)}</span>
                  <div className="flex flex-wrap items-center justify-end gap-2">
                    <Button size="sm" variant="ghost" aria-label="Print kitchen ticket" data-testid="kot" onClick={() => { if (!printKot(o, { location: o.location_name, tableLabel: tableName(o.table) })) toast.err("Allow pop-ups to print."); }}><ChefHat className="h-4 w-4" /><span className="hidden xl:inline">Kitchen</span></Button>
                    {o.order_type === "DINE_IN" && o.status !== "COMPLETED" && o.status !== "CANCELLED" && <Button size="sm" variant="ghost" aria-label="Move table" data-testid="move-table" onClick={() => setMoveFor(o)}><ArrowRightLeft className="h-4 w-4" /><span className="hidden xl:inline">Move</span></Button>}
                    {o.order_type === "DINE_IN" && o.status !== "COMPLETED" && o.status !== "CANCELLED" && o.payment_status === "PENDING" && o.items.length > 1 || o.order_type === "DINE_IN" && o.status !== "COMPLETED" && o.status !== "CANCELLED" && o.payment_status === "PENDING" && o.items.some((i) => i.quantity > 1) ? <Button size="sm" variant="ghost" aria-label="Split bill" data-testid="split-bill" onClick={() => { setPicks({}); setSplitFor(o); }}><Scissors className="h-4 w-4" /><span className="hidden xl:inline">Split</span></Button> : null}
                    <Button size="sm" variant="ghost" aria-label="Print bill" onClick={() => { if (!printReceipt(o, { business: me!.organization!.name, branding: me!.organization!.branding, loyalty: me!.organization!.loyalty, location: o.location_name, address: location?.address, currency })) toast.err("Allow pop-ups to print the bill."); }}><Printer className="h-4 w-4" /></Button>
                    {canRefund && <Button size="sm" variant="ghost" aria-label="Refund" onClick={() => openRefund(o)}><Undo2 className="h-4 w-4" /></Button>}
                    {canCancel(o) && o.payment_status !== "PAID" && <Button size="sm" variant="danger" disabled={busy} aria-label="Cancel order" onClick={() => setCancelFor(o)}><Ban className="h-4 w-4" /></Button>}
                    {isDelivery && o.status !== "COMPLETED" && o.status !== "CANCELLED" && <Button size="sm" variant="ghost" onClick={() => setAssignFor(o)}><Bike className="h-4 w-4" />{o.rider ? "Change" : "Rider"}</Button>}
                    {cashWithRider && <Badge tone="warn">Cash with rider</Badge>}
                    {unpaid && !needsPaymentFirst && !codWithRider && !cashWithRider && <Button size="sm" variant="secondary" onClick={() => setPayFor(o)}><HandCoins className="h-4 w-4" />Pay</Button>}
                    {needsRider
                      ? <Button size="sm" onClick={() => setAssignFor(o)}><Bike className="h-4 w-4" />Assign rider</Button>
                      : needsPaymentFirst
                      ? <Button size="sm" onClick={() => setPayFor(o)}><HandCoins className="h-4 w-4" />Take payment</Button>
                      : step && <Button size="sm" loading={working === o.id} onClick={() => move(o, step.to)}>{step.label}</Button>}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <Modal open={!!assignFor} onClose={() => setAssignFor(null)} title={`Rider for ${assignFor?.order_number ?? ""}`} width="max-w-sm">
        <div className="space-y-3">
          {riders.length === 0 ? <p className="text-sm text-muted">No riders yet. Add them in Staff → Add employee (role: Delivery rider).</p> : riders.map((r) => (
            <button key={r.id} onClick={() => assign(r.id)} disabled={busy} className={cn("flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left transition hover:border-brand", assignFor?.rider === r.id ? "border-brand bg-brand-soft" : "border-line")}>
              <span><b>{r.name}</b><span className="block text-xs text-muted">{r.vehicle || "-"}</span></span>
              <span className="text-right text-xs">{r.summary.on_road > 0 ? <Badge tone="brand">{r.summary.on_road} on the road</Badge> : <Badge tone="good">Free</Badge>}<span className="mt-1 block text-muted">{r.summary.delivered_today} today</span></span>
            </button>
          ))}
          {assignFor?.rider && assignFor.status !== "OUT_FOR_DELIVERY" && <Button variant="ghost" className="w-full" onClick={() => assign(null)}>Remove rider</Button>}
        </div>
      </Modal>
      <TablePicker open={!!moveFor} onClose={() => setMoveFor(null)} tables={tables} value={String(moveFor?.table ?? "")} taken={new Set()} onPick={doMove} />
      <Modal open={!!splitFor} onClose={() => setSplitFor(null)} title={`Split ${splitFor?.order_number ?? ""}`} width="max-w-md">
        <div className="space-y-3">
          <p className="text-sm text-muted">Choose what goes on the new bill. The rest stays on this one. Split before any payment is taken.</p>
          {splitFor?.items.map((i) => {
            const q = picks[i.id] ?? 0; const locked = !!i.deal_name;
            return (
              <div key={i.id} className={cn("flex items-center justify-between gap-3 rounded-xl border border-line p-2.5", locked && "opacity-50")}>
                <span className="min-w-0 text-sm"><b>{i.quantity}×</b> {i.product_name || i.deal_name}{locked && <span className="block text-xs text-muted">Deal items cannot be split</span>}</span>
                <div className="flex items-center gap-1">
                  <button aria-label="Less" disabled={locked || q <= 0} onClick={() => setPicks({ ...picks, [i.id]: q - 1 })} className="grid h-9 w-9 place-items-center rounded-lg bg-sunken disabled:opacity-40"><Minus className="h-4 w-4" /></button>
                  <span className="num w-7 text-center font-bold" data-testid={`split-q-${i.id}`}>{q}</span>
                  <button aria-label="More" disabled={locked || q >= i.quantity} onClick={() => setPicks({ ...picks, [i.id]: q + 1 })} className="grid h-9 w-9 place-items-center rounded-lg bg-sunken disabled:opacity-40"><Plus className="h-4 w-4" /></button>
                </div>
              </div>
            );
          })}
          <Button className="w-full" size="lg" loading={busy} disabled={Object.values(picks).every((q) => !q) || (splitFor ? splitFor.items.every((i) => (picks[i.id] ?? 0) === i.quantity) : true)} onClick={doSplit} data-testid="split-confirm">Create separate bill</Button>
        </div>
      </Modal>
      <PayModal order={payFor} open={!!payFor} onClose={() => setPayFor(null)} onChanged={load} />

      <Modal open={!!cancelFor} onClose={() => setCancelFor(null)} title={`Cancel ${cancelFor?.order_number ?? ""}`} width="max-w-sm">
        <div className="space-y-4">
          <p className="text-sm text-muted">Cancelled orders are recorded with the reason, so the owner can review them.{cancelFor && cancelFor.status !== "PENDING" ? " Ingredients are returned to stock only if cooking has not started." : ""}</p>
          <Select label="Reason" value={reasonPick} onChange={(e) => setReasonPick(e.target.value)}>{REASONS.map((r) => <option key={r}>{r}</option>)}</Select>
          <Input label={reasonPick === "Other" ? "Reason (required)" : "More detail (optional)"} value={reasonText} onChange={(e) => setReasonText(e.target.value)} />
          <div className="grid grid-cols-2 gap-2"><Button variant="secondary" onClick={() => setCancelFor(null)}>Keep order</Button><Button variant="danger" loading={busy} disabled={reasonPick === "Other" && reasonText.trim().length < 3} onClick={confirmCancel}>Cancel order</Button></div>
        </div>
      </Modal>

      <Modal open={!!refundFor} onClose={() => setRefundFor(null)} title={`Refund ${refundFor?.order_number ?? ""}`} width="max-w-sm">
        <div className="space-y-4">
          <p className="text-sm text-muted">Up to {money(refund.paid, currency)} can be refunded. Refunds are recorded on your open shift and cannot be undone.</p>
          <Select label="Refund by" value={refund.method} onChange={(e) => setRefund({ ...refund, method: e.target.value as PayMethod })}>
            <option value="CASH">Cash</option><option value="CARD">Card</option><option value="WALLET">JazzCash / Easypaisa</option><option value="BANK">Bank transfer</option>
          </Select>
          <Input label={`Amount (${currency})`} type="number" min="0" step="any" value={refund.amount} onChange={(e) => setRefund({ ...refund, amount: e.target.value })} />
          <Input label="Reason (required)" value={refund.reason} onChange={(e) => setRefund({ ...refund, reason: e.target.value })} placeholder="e.g. Cold food, wrong item" />
          <Button className="w-full" variant="danger" loading={busy} disabled={!(Number(refund.amount) > 0) || refund.reason.trim().length < 3} onClick={confirmRefund}>Give refund</Button>
        </div>
      </Modal>
    </>
  );
}
