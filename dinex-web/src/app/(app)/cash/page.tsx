"use client";
import { useCallback, useEffect, useState } from "react";
import { ArrowDownCircle, ArrowUpCircle, Banknote, CheckCircle2, Lock, PiggyBank, Receipt, Unlock, Wallet } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Select, Spinner, cn, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { Paginated, PayMethod, ShiftRow, ShiftSummary } from "@/lib/types";

const KINDS = [
  { id: "EXPENSE", label: "Expense from drawer", hint: "Vegetables, gas, repairs…", icon: Receipt },
  { id: "CASH_IN", label: "Cash in", hint: "Extra float added", icon: ArrowDownCircle },
  { id: "CASH_OUT", label: "Cash out", hint: "Money taken out", icon: ArrowUpCircle },
  { id: "SAFE_DROP", label: "Moved to safe", hint: "Too much cash in drawer", icon: PiggyBank },
] as const;
const METHOD_LABEL: Record<PayMethod, string> = { CASH: "Cash", CARD: "Card", WALLET: "JazzCash / Easypaisa", BANK: "Bank transfer" };
const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString("en-PK", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "-");

export default function CashDeskPage() {
  const { me, location, currency } = useAuth();
  const { run, busy } = useAction();
  const [shift, setShift] = useState<ShiftSummary | null>(null);
  const [history, setHistory] = useState<ShiftRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [opening, setOpening] = useState("");
  const [moveOpen, setMoveOpen] = useState(false);
  const [mv, setMv] = useState({ kind: "EXPENSE", amount: "", reason: "", category: "" });
  const [closeOpen, setCloseOpen] = useState(false);
  const [counted, setCounted] = useState("");
  const [note, setNote] = useState("");
  const [closed, setClosed] = useState<ShiftSummary | null>(null);

  const load = useCallback(async () => {
    if (!location) return;
    const [cur, hist] = await Promise.all([
      api.get<{ shift: ShiftSummary | null }>("/cash/shifts/current/", { location: location.id }),
      api.get<Paginated<ShiftRow>>("/cash/shifts/", { location: location.id, page_size: 15 }),
    ]);
    setShift(cur.shift); setHistory(hist.results); setLoading(false);
  }, [location]);
  useEffect(() => { load().catch(() => setLoading(false)); }, [load]);

  if (me && !me.organization) return <PlatformNotice />;
  if (!me?.can_operate_pos) return <EmptyState title="No cash desk access" hint="Ask the owner to assign you to a location." />;
  if (loading) return <Spinner label="Loading cash desk…" />;

  const openShift = async () => {
    const r = await run(() => api.post<ShiftSummary>("/cash/shifts/open/", { location: location!.id, opening_cash: opening || "0" }), "Shift opened. Good luck!");
    if (r) { setOpening(""); load(); }
  };
  const addMove = async () => {
    const r = await run(() => api.post(`/cash/shifts/${shift!.id}/movements/`, mv), "Recorded");
    if (r !== undefined) { setMoveOpen(false); setMv({ kind: "EXPENSE", amount: "", reason: "", category: "" }); load(); }
  };
  const closeShift = async () => {
    const r = await run(() => api.post<ShiftSummary>(`/cash/shifts/${shift!.id}/close/`, { counted_cash: counted, note }));
    if (r) { setClosed(r); setCloseOpen(false); setCounted(""); setNote(""); load(); }
  };

  const expected = Number(shift?.expected_cash ?? 0);
  const diff = counted === "" ? null : Number(counted) - expected;

  return (
    <>
      <PageHeader title="Cash desk" subtitle={`${location?.name} · every payment and every rupee of cash is tracked by shift`} />

      {!shift ? (
        <Card className="mx-auto max-w-md space-y-5 p-8 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-brand-soft text-brand"><Unlock className="h-7 w-7" /></div>
          <div><h2 className="text-xl font-bold">Start your shift</h2><p className="mt-1 text-sm text-muted">Count the cash in the drawer and enter it. You need an open shift to take payments.</p></div>
          <Input label={`Cash in drawer now (${currency})`} type="number" min="0" step="any" inputMode="decimal" value={opening} onChange={(e) => setOpening(e.target.value)} placeholder="0" autoFocus />
          <Button size="lg" className="w-full" loading={busy} onClick={openShift}>Open shift</Button>
        </Card>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat label="Opened with" value={money(shift.opening_cash, currency)} sub={`since ${when(shift.opened_at)}`} icon={Wallet} />
            <Stat label="Cash sales" value={money(shift.methods.CASH.net, currency)} sub={`${shift.orders_paid} orders paid`} icon={Banknote} />
            <Stat label="Card / wallet / bank" value={money(Number(shift.methods.CARD.net) + Number(shift.methods.WALLET.net) + Number(shift.methods.BANK.net), currency)} sub="not in the drawer" icon={Receipt} />
            <Card className="border-brand/40 bg-brand-soft p-5"><p className="text-sm font-medium text-brand">Cash that should be in the drawer</p><p className="mt-1 text-3xl font-bold text-brand">{money(shift.expected_cash, currency)}</p></Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <div className="flex items-center justify-between border-b border-line px-5 py-4"><h2 className="font-bold">Cash movements</h2><Button size="sm" variant="secondary" onClick={() => setMoveOpen(true)}>Add expense / cash in / out</Button></div>
              {shift.movements.length === 0 ? <p className="px-5 py-10 text-center text-sm text-muted">No movements yet. Record anything that goes in or out of the drawer apart from sales.</p> : (
                <ul className="divide-y divide-line">
                  {shift.movements.map((m) => {
                    const k = KINDS.find((x) => x.id === m.kind)!; const incoming = m.kind === "CASH_IN";
                    return (
                      <li key={m.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                        <div className="flex items-center gap-3"><div className={cn("grid h-9 w-9 place-items-center rounded-xl", incoming ? "bg-good-soft text-good" : "bg-bad-soft text-bad")}><k.icon className="h-4 w-4" /></div>
                          <div><p className="text-sm font-semibold">{k.label}{m.category ? ` · ${m.category}` : ""}</p><p className="text-xs text-muted">{m.reason || "-"} · {when(m.created_at)}</p></div></div>
                        <span className={cn("font-bold", incoming ? "text-good" : "text-bad")}>{incoming ? "+" : "−"}{money(m.amount, currency)}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </Card>

            <div className="space-y-6">
              <Card className="p-5">
                <h2 className="mb-3 font-bold">Payments this shift</h2>
                <dl className="space-y-2 text-sm">
                  {(Object.keys(METHOD_LABEL) as PayMethod[]).map((k) => (
                    <div key={k} className="flex justify-between"><dt className="text-muted">{METHOD_LABEL[k]}</dt><dd className="font-semibold">{money(shift.methods[k].net, currency)}</dd></div>
                  ))}
                  <div className="flex justify-between border-t border-line pt-2 font-bold"><dt>Total</dt><dd>{money(shift.net_total, currency)}</dd></div>
                  {Number(shift.refunds_total) > 0 && <div className="flex justify-between text-bad"><dt>Refunds given</dt><dd>−{money(shift.refunds_total, currency)}</dd></div>}
                  {shift.cancelled.count > 0 && <div className="flex justify-between text-warn"><dt>Cancelled orders</dt><dd>{shift.cancelled.count} · {money(shift.cancelled.total, currency)}</dd></div>}
                </dl>
              </Card>
              <Button size="lg" variant="secondary" className="w-full" onClick={() => setCloseOpen(true)}><Lock className="h-4 w-4" />Close shift</Button>
            </div>
          </div>
        </>
      )}

      <Card className="mt-8 overflow-hidden">
        <div className="border-b border-line px-5 py-4"><h2 className="font-bold">Recent shifts</h2></div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Cashier</th><th className="px-5 py-3">Opened</th><th className="px-5 py-3">Closed</th><th className="px-5 py-3 text-right">Expected</th><th className="px-5 py-3 text-right">Counted</th><th className="px-5 py-3 text-right">Difference</th></tr></thead>
            <tbody className="divide-y divide-line">
              {history.map((s) => (
                <tr key={s.id}>
                  <td className="px-5 py-3 font-semibold">{s.cashier}</td><td className="px-5 py-3 text-muted">{when(s.opened_at)}</td>
                  <td className="px-5 py-3 text-muted">{s.status === "OPEN" ? <Badge tone="good">Open</Badge> : when(s.closed_at)}</td>
                  <td className="px-5 py-3 text-right">{s.expected_cash !== null ? money(s.expected_cash, currency) : "-"}</td>
                  <td className="px-5 py-3 text-right">{s.counted_cash !== null ? money(s.counted_cash, currency) : "-"}</td>
                  <td className="px-5 py-3 text-right">{s.difference === null ? "-" : Number(s.difference) === 0 ? <Badge tone="good">Balanced</Badge> : <Badge tone={Number(s.difference) < 0 ? "bad" : "warn"}>{Number(s.difference) > 0 ? "+" : "−"}{money(Math.abs(Number(s.difference)), currency)}</Badge>}</td>
                </tr>
              ))}
              {history.length === 0 && <tr><td colSpan={6} className="px-5 py-8 text-center text-muted">No shifts yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={moveOpen} onClose={() => setMoveOpen(false)} title="Cash movement">
        <div className="space-y-4">
          <Select label="What is it?" value={mv.kind} onChange={(e) => setMv({ ...mv, kind: e.target.value })}>{KINDS.map((k) => <option key={k.id} value={k.id}>{k.label}: {k.hint}</option>)}</Select>
          <Input label={`Amount (${currency})`} type="number" min="0" step="any" inputMode="decimal" value={mv.amount} onChange={(e) => setMv({ ...mv, amount: e.target.value })} />
          <Input label="What was it for?" value={mv.reason} onChange={(e) => setMv({ ...mv, reason: e.target.value })} hint={mv.kind === "EXPENSE" || mv.kind === "CASH_OUT" ? "Required" : "Optional"} />
          <Input label="Category (optional)" placeholder="vegetables, gas, electricity…" value={mv.category} onChange={(e) => setMv({ ...mv, category: e.target.value })} />
          <Button className="w-full" size="lg" loading={busy} disabled={!(Number(mv.amount) > 0)} onClick={addMove}>Save</Button>
        </div>
      </Modal>

      <Modal open={closeOpen} onClose={() => setCloseOpen(false)} title="Close shift">
        <div className="space-y-4">
          <p className="text-sm text-muted">Count all the cash in the drawer and enter the total. DineX compares it with what it expects.</p>
          <Input label={`Cash counted (${currency})`} type="number" min="0" step="any" inputMode="decimal" value={counted} onChange={(e) => setCounted(e.target.value)} autoFocus />
          {diff !== null && (
            <div className={cn("rounded-xl px-4 py-3 text-sm font-semibold", diff === 0 ? "bg-good-soft text-good" : diff < 0 ? "bg-bad-soft text-bad" : "bg-warn-soft text-warn")}>
              {diff === 0 ? "Perfect, the drawer balances." : diff < 0 ? `Short by ${money(-diff, currency)}` : `Over by ${money(diff, currency)}`}
            </div>
          )}
          <Input label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} placeholder={diff && diff !== 0 ? "Explain the difference" : ""} />
          <Button className="w-full" size="lg" loading={busy} disabled={counted === ""} onClick={closeShift}>Close shift</Button>
        </div>
      </Modal>

      <Modal open={!!closed} onClose={() => setClosed(null)} title="Shift closed" width="max-w-sm">
        {closed && (
          <div className="text-center">
            <CheckCircle2 className="mx-auto h-14 w-14 text-good" />
            <dl className="mt-4 space-y-2 text-left text-sm">
              <div className="flex justify-between"><dt className="text-muted">Total sales</dt><dd className="font-bold">{money(closed.net_total, currency)}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Expected cash</dt><dd className="font-semibold">{money(closed.expected_cash, currency)}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Counted cash</dt><dd className="font-semibold">{money(closed.counted_cash, currency)}</dd></div>
              <div className="flex justify-between border-t border-line pt-2"><dt className="font-semibold">Difference</dt><dd className={cn("font-bold", Number(closed.difference) < 0 ? "text-bad" : Number(closed.difference) > 0 ? "text-warn" : "text-good")}>{Number(closed.difference) === 0 ? "Balanced" : money(closed.difference, currency)}</dd></div>
            </dl>
            <Button className="mt-5 w-full" onClick={() => setClosed(null)}>Done</Button>
          </div>
        )}
      </Modal>
    </>
  );
}

function Stat({ label, value, sub, icon: Icon }: { label: string; value: string; sub: string; icon: typeof Wallet }) {
  return <Card className="p-5"><div className="mb-3 grid h-9 w-9 place-items-center rounded-xl bg-sunken text-muted"><Icon className="h-4 w-4" /></div><p className="text-2xl font-bold tracking-tight">{value}</p><p className="mt-0.5 text-sm text-muted">{label}</p><p className="text-xs text-muted/80">{sub}</p></Card>;
}
