"use client";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Printer, Trash2 } from "lucide-react";
import { Badge, Button, Input, Modal, Select, Spinner, cn, useAction, useToast } from "@/components/ui";
import { fmtDate } from "@/components/Platform";
import { api, money } from "@/lib/api";
import { printPayslip } from "@/lib/payslip";
import { fmtMin } from "@/lib/time";
import type { PaySlipFull } from "@/lib/types";

const METHODS = [["BANK", "Bank transfer"], ["CASH", "Cash"], ["JAZZCASH", "JazzCash"], ["EASYPAISA", "Easypaisa"], ["CHEQUE", "Cheque"], ["OTHER", "Other"]];

export function SlipModal({ slipId, onClose, onChanged, business, currency }: { slipId: number | null; onClose: () => void; onChanged: () => void; business: string; currency: string }) {
  const { run, busy } = useAction();
  const toast = useToast();
  const [s, setS] = useState<PaySlipFull | null>(null);
  const [adj, setAdj] = useState({ kind: "BONUS", label: "", amount: "" });
  const [pay, setPay] = useState({ method: "BANK", reference: "", drawer: false });
  const load = useCallback(async () => { if (slipId) setS(await api.get<PaySlipFull>(`/payroll/slips/${slipId}/`)); }, [slipId]);
  useEffect(() => { setS(null); if (slipId) load().catch((e) => toast.err(e.message)); }, [slipId, load, toast]);

  const draft = s?.run_status === "DRAFT";
  async function addAdj() {
    const r = await run(() => api.post<PaySlipFull>(`/payroll/slips/${slipId}/adjustments/`, adj), "Added");
    if (r) { setS(r); setAdj({ ...adj, label: "", amount: "" }); onChanged(); }
  }
  async function delAdj(id: number) { if ((await run(() => api.del(`/payroll/adjustments/${id}/`))) !== undefined) { await load(); onChanged(); } }
  async function doPay() {
    const r = await run(() => api.post<PaySlipFull>(`/payroll/slips/${slipId}/pay/`, { method: pay.method, reference: pay.reference, from_drawer: pay.drawer && pay.method === "CASH" }), "Salary paid");
    if (r) { setS(r); onChanged(); }
  }
  const month = s ? new Date(s.month).toLocaleDateString("en-PK", { month: "long", year: "numeric" }) : "";

  return (
    <Modal open={!!slipId} onClose={onClose} title={s ? `${s.employee.name} · ${month}` : "Payslip"} width="max-w-2xl">
      {!s ? <Spinner /> : (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2"><Badge tone="brand">{s.employee.role_display}</Badge><Badge>{s.location_name}</Badge><Badge tone={s.pay_type === "MONTHLY" ? "neutral" : "warn"}>{s.pay_type === "MONTHLY" ? `Salary ${money(s.base_amount, currency)}` : s.pay_type === "DAILY" ? `${money(s.base_amount, currency)} / day` : `${money(s.base_amount, currency)} / hour`}</Badge>
            {s.status === "PAID" ? <Badge tone="good">Paid {fmtDate(s.paid_at)} · {s.paid_method}</Badge> : s.status === "UNPAID" ? <Badge tone="warn">To pay</Badge> : <Badge>Draft</Badge>}</div>

          {s.warnings.length > 0 && <div className="space-y-1 rounded-xl bg-warn-soft p-3 text-sm text-warn">{s.warnings.map((w) => <p key={w} className="flex gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{w}</p>)}</div>}

          <div className="grid grid-cols-3 gap-2 text-center text-xs sm:grid-cols-6">
            {[["Worked days", s.present_days], ["Absent", s.absent_days], ["Leave", s.leave_paid + s.leave_unpaid], ["Late", s.late_days], ["Hours", (s.worked_minutes / 60).toFixed(1)], ["Overtime", fmtMin(s.overtime_minutes)]].map(([k, v]) => <div key={k as string} className="rounded-xl bg-sunken p-2"><p className="text-base font-bold">{v}</p><p className="text-muted">{k}</p></div>)}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div><p className="mb-2 text-[13px] font-semibold text-muted">Earnings</p>
              <ul className="space-y-2 text-sm">{s.lines.filter((l) => l.kind === "earning").map((l, i) => <li key={i}><div className="flex justify-between"><span>{l.label}</span><b>{money(l.amount, currency)}</b></div>{l.note && <p className="text-xs text-muted">{l.note}</p>}</li>)}
                <li className="flex justify-between border-t border-line pt-2 font-bold"><span>Gross</span><span>{money(s.gross, currency)}</span></li></ul></div>
            <div><p className="mb-2 text-[13px] font-semibold text-muted">Deductions</p>
              <ul className="space-y-2 text-sm">{s.lines.filter((l) => l.kind === "deduction").map((l, i) => <li key={i}><div className="flex justify-between"><span>{l.label}</span><b className="text-bad">−{money(l.amount, currency)}</b></div>{l.note && <p className="text-xs text-muted">{l.note}</p>}</li>)}
                {s.lines.every((l) => l.kind !== "deduction") && <li className="text-muted">None</li>}
                <li className="flex justify-between border-t border-line pt-2 font-bold"><span>Total</span><span>−{money(s.deductions, currency)}</span></li></ul></div>
          </div>

          <div className="flex items-center justify-between rounded-2xl bg-brand-soft px-5 py-4"><span className="font-semibold text-brand">Net pay</span><span className="text-3xl font-bold text-brand">{money(s.net, currency)}</span></div>

          {draft && (
            <div className="space-y-3 rounded-xl border border-line p-4">
              <p className="text-sm font-semibold">Add a bonus or a one-off deduction</p>
              {s.adjustments.length > 0 && <ul className="space-y-1.5 text-sm">{s.adjustments.map((a) => <li key={a.id} className="flex items-center justify-between rounded-lg bg-sunken px-3 py-1.5"><span>{a.kind === "BONUS" ? "＋" : "−"} {a.label}</span><span className="flex items-center gap-2"><b className={a.kind === "BONUS" ? "text-good" : "text-bad"}>{money(a.amount, currency)}</b><button aria-label="Remove" onClick={() => delAdj(a.id)} className="text-muted hover:text-bad"><Trash2 className="h-4 w-4" /></button></span></li>)}</ul>}
              <div className="grid grid-cols-[110px_1fr_110px_auto] items-end gap-2">
                <Select aria-label="Type" value={adj.kind} onChange={(e) => setAdj({ ...adj, kind: e.target.value })}><option value="BONUS">Bonus</option><option value="DEDUCTION">Deduction</option></Select>
                <Input aria-label="What for" placeholder="e.g. Eid bonus" value={adj.label} onChange={(e) => setAdj({ ...adj, label: e.target.value })} />
                <Input aria-label="Amount" type="number" min="0" placeholder="Amount" value={adj.amount} onChange={(e) => setAdj({ ...adj, amount: e.target.value })} />
                <Button variant="secondary" loading={busy} disabled={adj.label.trim().length < 2 || !(Number(adj.amount) > 0)} onClick={addAdj}>Add</Button>
              </div>
            </div>
          )}

          {s.status === "UNPAID" && (
            <div className="space-y-3 rounded-xl border border-line p-4">
              <p className="text-sm font-semibold">Pay {money(s.net, currency)} to {s.employee.name.split(" ")[0]}</p>
              <div className="grid grid-cols-2 gap-3"><Select label="How" value={pay.method} onChange={(e) => setPay({ ...pay, method: e.target.value })}>{METHODS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select><Input label="Reference (optional)" value={pay.reference} onChange={(e) => setPay({ ...pay, reference: e.target.value })} /></div>
              {pay.method === "CASH" && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={pay.drawer} onChange={(e) => setPay({ ...pay, drawer: e.target.checked })} className="h-4 w-4 accent-[rgb(var(--brand))]" />Take it from my cash drawer (recorded as an expense on my shift)</label>}
              <Button className="w-full" size="lg" loading={busy} onClick={doPay}>Mark as paid</Button>
            </div>
          )}

          <Button variant="secondary" className="w-full" onClick={() => { if (!printPayslip(s, business, currency)) toast.err("Allow pop-ups to print."); }}><Printer className="h-4 w-4" />Print payslip</Button>
        </div>
      )}
    </Modal>
  );
}
