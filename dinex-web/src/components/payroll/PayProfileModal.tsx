"use client";
import { useEffect, useState } from "react";
import { Button, Input, Modal, Select, cn, useAction } from "@/components/ui";
import { api } from "@/lib/api";
import type { PayEmp, PayProfile, PayType } from "@/lib/types";

const TYPES: { id: PayType; label: string; hint: string }[] = [
  { id: "MONTHLY", label: "Monthly salary", hint: "A fixed salary. Absent days and unpaid leave are deducted." },
  { id: "DAILY", label: "Daily wage", hint: "Paid for each day worked (plus paid leave if you choose)." },
  { id: "HOURLY", label: "Hourly", hint: "Paid for the hours worked." },
];
const blank = { pay_type: "MONTHLY" as PayType, base_amount: "", month_basis: "30", standard_hours: "", fixed_allowance: "0", fixed_deduction: "0", overtime_enabled: true, absent_penalty_days: "1",
  pay_paid_leave: true, pay_weekly_off: false, late_rule: "NONE", late_every: "3", late_deduct_days: "0.5", notes: "" };

export function PayProfileModal({ open, onClose, employee, profile, currency, onSaved }: { open: boolean; onClose: () => void; employee: PayEmp | null; profile: PayProfile | null; currency: string; onSaved: () => void }) {
  const { run, busy } = useAction();
  const [f, setF] = useState(blank);
  useEffect(() => {
    if (!open) return;
    setF(profile ? { ...blank, ...Object.fromEntries(Object.entries(profile).map(([k, v]) => [k, typeof v === "boolean" ? v : v === null ? "" : String(v)])), base_amount: String(Number(profile.base_amount)),
      fixed_allowance: String(Number(profile.fixed_allowance)), fixed_deduction: String(Number(profile.fixed_deduction)), standard_hours: profile.standard_hours ? String(Number(profile.standard_hours)) : "" } as typeof blank : blank);
  }, [open, profile]);
  const set = <K extends keyof typeof blank>(k: K, v: (typeof blank)[K]) => setF((s) => ({ ...s, [k]: v }));
  const type = TYPES.find((t) => t.id === f.pay_type)!;
  const amountLabel = f.pay_type === "MONTHLY" ? `Monthly salary (${currency})` : f.pay_type === "DAILY" ? `Wage per day (${currency})` : `Rate per hour (${currency})`;

  async function save() {
    const body = { ...f, base_amount: f.base_amount, standard_hours: f.standard_hours || null, late_every: Number(f.late_every) || 3 };
    if (await run(() => api.put(`/payroll/employees/${employee!.id}/profile/`, body), "Pay saved")) { onClose(); onSaved(); }
  }
  async function remove() {
    if (confirm(`Remove ${employee?.name}'s pay profile? They will no longer appear in payroll.`) && (await run(() => api.del(`/payroll/employees/${employee!.id}/profile/`), "Removed")) !== undefined) { onClose(); onSaved(); }
  }
  const Toggle = ({ k, label }: { k: "overtime_enabled" | "pay_paid_leave" | "pay_weekly_off"; label: string }) => (
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f[k]} onChange={(e) => set(k, e.target.checked)} className="h-4 w-4 accent-[rgb(var(--brand))]" />{label}</label>
  );

  return (
    <Modal open={open} onClose={onClose} title={`Pay · ${employee?.name ?? ""}`} width="max-w-xl"><div className="space-y-5">
      <div className="grid grid-cols-3 gap-2">{TYPES.map((t) => <button key={t.id} type="button" onClick={() => set("pay_type", t.id)} className={cn("rounded-xl border px-3 py-3 text-sm font-semibold transition", f.pay_type === t.id ? "border-brand bg-brand-soft text-brand" : "border-line hover:bg-sunken")}>{t.label}</button>)}</div>
      <p className="-mt-2 text-xs text-muted">{type.hint}</p>
      <div className="grid grid-cols-2 gap-3">
        <Input label={amountLabel} type="number" min="0" step="any" value={f.base_amount} onChange={(e) => set("base_amount", e.target.value)} autoFocus />
        {f.pay_type === "MONTHLY"
          ? <Select label="One day's pay is the salary ÷" value={f.month_basis} onChange={(e) => set("month_basis", e.target.value)}><option value="30">30 days</option><option value="26">26 working days</option><option value="CALENDAR">Days in that month</option></Select>
          : <Input label="Paid hours in a day" type="number" min="0" max="24" step="0.5" value={f.standard_hours} onChange={(e) => set("standard_hours", e.target.value)} hint="Empty = from duty hours" />}
      </div>
      {f.pay_type === "MONTHLY" && <Input label="Paid hours in a day" type="number" min="0" max="24" step="0.5" value={f.standard_hours} onChange={(e) => set("standard_hours", e.target.value)} hint="Used for the hourly rate (overtime). Empty = from duty hours." />}
      <div className="grid grid-cols-2 gap-3"><Input label={`Monthly allowance (${currency})`} type="number" min="0" value={f.fixed_allowance} onChange={(e) => set("fixed_allowance", e.target.value)} hint="Food, transport…" /><Input label={`Monthly deduction (${currency})`} type="number" min="0" value={f.fixed_deduction} onChange={(e) => set("fixed_deduction", e.target.value)} hint="EOBI, uniform…" /></div>
      <div className="space-y-2.5 rounded-xl bg-sunken p-4">
        <Toggle k="overtime_enabled" label="Pay overtime (using the overtime rate in their duty hours)" />
        {f.pay_type === "MONTHLY" && <Input label="Days of pay lost for each absent day" type="number" min="0" max="5" step="0.5" value={f.absent_penalty_days} onChange={(e) => set("absent_penalty_days", e.target.value)} />}
        {f.pay_type !== "MONTHLY" && <Toggle k="pay_paid_leave" label="Paid-leave days are paid" />}
        {f.pay_type === "DAILY" && <Toggle k="pay_weekly_off" label="The weekly off is paid" />}
      </div>
      <div className="space-y-3">
        <Select label="When they arrive late" value={f.late_rule} onChange={(e) => set("late_rule", e.target.value)}><option value="NONE">No deduction</option><option value="MINUTES">Deduct the late minutes</option><option value="COUNT">Every few late arrivals, deduct days</option></Select>
        {f.late_rule === "COUNT" && <div className="grid grid-cols-2 gap-3"><Input label="Every this many late days" type="number" min="1" value={f.late_every} onChange={(e) => set("late_every", e.target.value)} /><Input label="Deduct this many days of pay" type="number" min="0" step="0.25" value={f.late_deduct_days} onChange={(e) => set("late_deduct_days", e.target.value)} /></div>}
      </div>
      <div className="flex gap-2"><Button className="flex-1" size="lg" loading={busy} disabled={f.base_amount === ""} onClick={save}>Save</Button>{profile && <Button variant="danger" onClick={remove}>Remove</Button>}</div>
    </div></Modal>
  );
}
