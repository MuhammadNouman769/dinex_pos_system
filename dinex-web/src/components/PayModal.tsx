"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Banknote, CheckCircle2, CreditCard, Gift, Landmark, Printer, Smartphone } from "lucide-react";
import { Badge, Button, Input, Modal, Spinner, cn, useAction, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import { printReceipt } from "@/lib/receipt";
import type { Order, OrderMoney, PayMethod, PaymentRow, ShiftSummary } from "@/lib/types";

const METHODS: { id: PayMethod; label: string; icon: typeof Banknote }[] = [
  { id: "CASH", label: "Cash", icon: Banknote }, { id: "CARD", label: "Card", icon: CreditCard },
  { id: "WALLET", label: "JazzCash / Easypaisa", icon: Smartphone }, { id: "BANK", label: "Bank transfer", icon: Landmark },
];

/** Take payment for an order: cash with change, card, wallet, bank, or any split of them. */
export function PayModal({ order, open, onClose, onChanged }: { order: Order | null; open: boolean; onClose: () => void; onChanged?: () => void }) {
  const { me, location, currency } = useAuth();
  const toast = useToast();
  const { run, busy } = useAction();
  const [info, setInfo] = useState<{ order: OrderMoney; payments: PaymentRow[] } | null>(null);
  const [shift, setShift] = useState<ShiftSummary | null | undefined>(undefined);
  const [method, setMethod] = useState<PayMethod>("CASH");
  const [amount, setAmount] = useState("");
  const [tendered, setTendered] = useState("");
  const [ref, setRef] = useState("");
  const [guests, setGuests] = useState(0);
  const [lastChange, setLastChange] = useState<number | null>(null);
  const [fresh, setFresh] = useState<Order | null>(null);
  const [usePts, setUsePts] = useState("");

  const load = useCallback(async (keepAmount = false) => {
    if (!order) return;
    const [i, s, f] = await Promise.all([
      api.get<{ order: OrderMoney; payments: PaymentRow[] }>(`/cash/orders/${order.id}/payments/`),
      api.get<{ shift: ShiftSummary | null }>("/cash/shifts/current/", { location: order.location }).then((r) => r.shift),
      api.get<Order>(`/orders/${order.id}/`),
    ]);
    setFresh(f);
    if (f.loyalty) { const per = Number(f.loyalty.point_value) || 1; setUsePts(String(Math.max(0, Math.min(f.loyalty.balance, Math.floor(Number(i.order.due) / per))))); }
    setInfo(i); setShift(s); if (!keepAmount) setAmount(String(Number(i.order.due))); setTendered("");
  }, [order]);

  useEffect(() => { if (open) { setInfo(null); setFresh(null); setShift(undefined); setLastChange(null); setGuests(0); setMethod("CASH"); setRef(""); load().catch((e) => toast.err(e.message)); } }, [open, load, toast]);

  if (!order) return null;
  const due = Number(info?.order.due ?? 0);
  const amt = Number(amount) || 0;
  const change = method === "CASH" && Number(tendered) > amt ? Number(tendered) - amt : 0;
  const quick = Array.from(new Set([due, Math.ceil(due / 100) * 100, Math.ceil(due / 500) * 500, Math.ceil(due / 1000) * 1000, Math.ceil(due / 5000) * 5000])).filter((v) => v >= due && v > 0).slice(0, 4);
  const paidInFull = info && due <= 0;

  const share = (n: number, remaining: number) => String(Math.round((remaining / n) * 100) / 100);
  function pickGuests(n: number) { setGuests(n); setAmount(n > 1 ? share(n, due) : String(due)); setTendered(""); }

  async function pay() {
    const r = await run(() => api.post<{ payment: PaymentRow; order: OrderMoney }>(`/cash/orders/${order!.id}/payments/`, {
      method, amount: String(amt), ...(method === "CASH" && tendered ? { tendered } : {}), ...(method !== "CASH" && ref ? { reference: ref } : {}),
    }));
    if (r) { setLastChange(r.payment.change ? Number(r.payment.change) : null); if (guests > 1) { const left = guests - 1; setGuests(left); const dueNow = Number(r.order.due); setAmount(left > 1 ? share(left, dueNow) : String(dueNow)); } await load(guests > 1); onChanged?.(); }
  }

  return (
    <Modal open={open} onClose={onClose} title={`Payment · ${order.order_number}`} width="max-w-md">
      {!info || shift === undefined ? <Spinner /> : paidInFull ? (
        <div className="text-center">
          <CheckCircle2 className="mx-auto h-14 w-14 text-good" />
          <p className="mt-3 text-xl font-bold">Paid in full</p>
          <p className="text-2xl font-bold text-brand">{money(info.order.total, currency)}</p>
          {lastChange ? <div className="mx-auto mt-4 w-fit rounded-2xl bg-warn-soft px-6 py-3"><p className="text-xs font-semibold uppercase text-warn">Give change</p><p className="text-3xl font-bold text-warn">{money(lastChange, currency)}</p></div> : null}
          <div className="mt-5 grid grid-cols-2 gap-2">
            <Button variant="secondary" onClick={() => { if (!printReceipt(fresh ?? order, { business: me!.organization!.name, branding: me!.organization!.branding, loyalty: me!.organization!.loyalty, location: order.location_name, address: location?.address, currency })) toast.err("Allow pop-ups to print the bill."); }}><Printer className="h-4 w-4" />Print bill</Button>
            <Button onClick={onClose}>Done</Button>
          </div>
        </div>
      ) : shift === null ? (
        <div className="space-y-3 text-center">
          <p className="font-semibold">Open your shift first</p>
          <p className="text-sm text-muted">Every payment is recorded against a cashier&apos;s shift so the cash can be counted at the end of the day.</p>
          <Link href="/cash" onClick={onClose}><Button className="w-full">Go to Cash desk</Button></Link>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="rounded-2xl bg-sunken p-4 text-center">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Amount due</p>
            <p className="text-4xl font-bold tracking-tight">{money(due, currency)}</p>
            {Number(info.order.paid) > 0 && <p className="mt-1 text-xs text-muted">{money(info.order.paid, currency)} already paid of {money(info.order.total, currency)}</p>}
          </div>

          <div className="grid grid-cols-2 gap-2">
            {METHODS.map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setMethod(id)} className={cn("flex items-center gap-2 rounded-xl border px-3 py-3 text-left text-sm font-semibold transition", method === id ? "border-brand bg-brand-soft text-brand" : "border-line hover:bg-sunken")}>
                <Icon className="h-5 w-5 shrink-0" /><span className="leading-tight">{label}</span>
              </button>
            ))}
          </div>

          {fresh?.loyalty && (
            <div className="rounded-2xl border border-line bg-sunken p-3.5" data-testid="loyalty-panel">
              <p className="flex items-center gap-2 text-sm font-semibold"><Gift className="h-4 w-4 text-brand" />{fresh.loyalty.customer} · <span data-testid="loy-balance">{fresh.loyalty.balance}</span> points</p>
              {fresh.loyalty.redeemed > 0 && <p className="mt-1 text-sm text-good" data-testid="loy-used">Used {fresh.loyalty.redeemed} points · {money(fresh.loyalty.redeemed_value, currency)} off</p>}
              {fresh.loyalty.earned > 0 && <p className="mt-1 text-sm text-good" data-testid="loy-earned">Earned {fresh.loyalty.earned} points on this bill</p>}
              {fresh.loyalty.can_redeem ? (
                <div className="mt-2.5 flex items-end gap-2">
                  <div className="flex-1"><Input label="Use points" type="number" min={1} max={fresh.loyalty.balance} value={usePts} data-testid="use-points" onChange={(e) => setUsePts(e.target.value)} hint={`1 point = ${money(fresh.loyalty.point_value, currency)} off`} /></div>
                  <Button variant="secondary" loading={busy} disabled={!Number(usePts)} data-testid="use-points-btn" onClick={async () => { const r = await run(() => api.post(`/orders/${order!.id}/redeem-points/`, { points: Number(usePts) }), "Points used"); if (r) { await load(); onChanged?.(); } }}>Use</Button>
                </div>
              ) : fresh.loyalty.redeemed === 0 && !fresh.loyalty.earned && fresh.loyalty.balance < fresh.loyalty.min_redeem && (
                <p className="mt-1 text-xs text-muted">Points can be used from {fresh.loyalty.min_redeem} points.</p>
              )}
            </div>
          )}
          {due > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-semibold text-muted">Split equally between</p>
              <div className="flex flex-wrap gap-2">
                {[1, 2, 3, 4, 5, 6].map((n) => <button key={n} type="button" data-testid={`guests-${n}`} onClick={() => pickGuests(n)} className={cn("h-10 min-w-[40px] rounded-full border px-3 text-sm font-semibold", (guests || 1) === n ? "border-brand bg-brand-soft text-brand" : "border-line text-muted hover:text-ink")}>{n === 1 ? "Whole bill" : n}</button>)}
              </div>
              {guests > 1 && <p className="mt-1.5 text-xs text-muted">{guests} guests left to pay · each pays about {money(Number(share(guests, due)), currency)}</p>}
            </div>
          )}
          <Input label="Amount to pay now" type="number" min="0" step="any" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} hint={amt < due && amt > 0 ? "Part payment. You can add another method for the rest." : undefined} />

          {method === "CASH" ? (
            <div className="space-y-3">
              <Input label="Cash received" type="number" min="0" step="any" inputMode="decimal" value={tendered} onChange={(e) => setTendered(e.target.value)} placeholder="Optional: to work out the change" />
              <div className="flex flex-wrap gap-2">
                {quick.map((v) => <button key={v} onClick={() => setTendered(String(v))} className="rounded-full border border-line px-3 py-1.5 text-sm font-semibold hover:border-brand hover:text-brand">{v === due ? "Exact" : v.toLocaleString()}</button>)}
              </div>
              {change > 0 && <div className="flex items-center justify-between rounded-xl bg-warn-soft px-4 py-3 text-warn"><span className="text-sm font-semibold">Change to give</span><span className="text-xl font-bold">{money(change, currency)}</span></div>}
            </div>
          ) : <Input label="Reference (optional)" placeholder={method === "CARD" ? "Slip / approval no." : "Transaction id"} value={ref} onChange={(e) => setRef(e.target.value)} />}

          <Button size="lg" className="w-full" loading={busy} disabled={amt <= 0 || amt > due || (method === "CASH" && !!tendered && Number(tendered) < amt)} onClick={pay}>Receive {money(amt, currency)}</Button>

          {info.payments.length > 0 && (
            <ul className="space-y-1 border-t border-line pt-3 text-sm">
              {info.payments.map((p) => <li key={p.id} className="flex justify-between"><span className="text-muted">{p.kind === "REFUND" ? "Refund · " : ""}{METHODS.find((m) => m.id === p.method)?.label} · {p.by}</span><span className={cn("font-semibold", p.kind === "REFUND" && "text-bad")}>{p.kind === "REFUND" ? "−" : ""}{money(p.amount, currency)}</span></li>)}
            </ul>
          )}
        </div>
      )}
      {info && !paidInFull && <div className="mt-4 text-center"><Badge tone={info.order.payment_status === "PARTIAL" ? "warn" : "neutral"}>{info.order.payment_status === "PARTIAL" ? "Partly paid" : "Unpaid"}</Badge></div>}
    </Modal>
  );
}
