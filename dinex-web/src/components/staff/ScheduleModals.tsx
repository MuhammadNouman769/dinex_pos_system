"use client";
import { useEffect, useState } from "react";
import { Button, Input, Modal, Select, cn, useAction } from "@/components/ui";
import { api } from "@/lib/api";
import { DAYS } from "@/lib/time";
import type { EmpRole, Schedule } from "@/lib/types";

const DEFAULT: Schedule = { start_time: "12:00", end_time: "22:00", weekly_off: [], grace_minutes: 10, min_overtime_minutes: 30, overtime_multiplier: 1.5, overnight: false };

function Form({ value, onChange }: { value: Schedule; onChange: (s: Schedule) => void }) {
  const set = <K extends keyof Schedule>(k: K, v: Schedule[K]) => onChange({ ...value, [k]: v });
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3"><Input label="Duty starts" type="time" value={value.start_time} onChange={(e) => set("start_time", e.target.value)} /><Input label="Duty ends" type="time" value={value.end_time} onChange={(e) => set("end_time", e.target.value)} hint={value.end_time <= value.start_time ? "Ends after midnight" : undefined} /></div>
      <div>
        <p className="mb-1.5 text-[13px] font-semibold text-muted">Weekly off</p>
        <div className="flex flex-wrap gap-2">{DAYS.map((d, i) => { const on = value.weekly_off.includes(i); return <button key={d} type="button" onClick={() => set("weekly_off", on ? value.weekly_off.filter((x) => x !== i) : [...value.weekly_off, i].sort())} className={cn("rounded-full border px-3.5 py-1.5 text-sm font-semibold", on ? "border-brand bg-brand text-white" : "border-line bg-surface text-muted hover:text-ink")}>{d}</button>; })}</div>
        <p className="mt-1 text-xs text-muted">Working on the weekly off counts completely as overtime.</p>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <Input label="Late after (min)" type="number" min="0" value={value.grace_minutes} onChange={(e) => set("grace_minutes", Number(e.target.value))} hint="grace period" />
        <Input label="Min overtime (min)" type="number" min="0" value={value.min_overtime_minutes} onChange={(e) => set("min_overtime_minutes", Number(e.target.value))} hint="ignore less" />
        <Input label="Overtime rate ×" type="number" min="1" max="5" step="0.25" value={value.overtime_multiplier} onChange={(e) => set("overtime_multiplier", Number(e.target.value))} />
      </div>
    </div>
  );
}

export function ScheduleModal({ open, onClose, employeeId, name, current, onSaved }: { open: boolean; onClose: () => void; employeeId: number; name: string; current: Schedule | null; onSaved: () => void }) {
  const { run, busy } = useAction();
  const [v, setV] = useState<Schedule>(DEFAULT);
  useEffect(() => { if (open) setV(current ?? DEFAULT); }, [open, current]);
  const save = async () => { if (await run(() => api.put(`/staff/employees/${employeeId}/schedule/`, v), "Duty hours saved")) { onClose(); onSaved(); } };
  const clear = async () => { if (confirm("Remove the duty hours? Late and overtime will no longer be worked out.") && (await run(() => api.del(`/staff/employees/${employeeId}/schedule/`), "Removed")) !== undefined) { onClose(); onSaved(); } };
  return <Modal open={open} onClose={onClose} title={`Duty hours · ${name}`}><div className="space-y-5"><Form value={v} onChange={setV} /><div className="flex gap-2"><Button className="flex-1" size="lg" loading={busy} onClick={save}>Save</Button>{current && <Button variant="danger" onClick={clear}>Remove</Button>}</div></div></Modal>;
}

export function BulkScheduleModal({ open, onClose, locationId, onSaved }: { open: boolean; onClose: () => void; locationId: number; onSaved: () => void }) {
  const { run, busy } = useAction();
  const [v, setV] = useState<Schedule>(DEFAULT);
  const [role, setRole] = useState<EmpRole | "">("WAITER");
  const save = async () => { if (await run(() => api.post("/staff/schedule/bulk/", { ...v, location: locationId, ...(role ? { role } : {}) }), "Duty hours saved")) { onClose(); onSaved(); } };
  return (
    <Modal open={open} onClose={onClose} title="Duty hours for a whole group"><div className="space-y-5">
      <Select label="Who" value={role} onChange={(e) => setRole(e.target.value as EmpRole | "")}>
        <option value="">Everyone at this branch</option>{(["MANAGER", "CASHIER", "WAITER", "RIDER", "CHEF", "HELPER", "OTHER"] as EmpRole[]).map((r) => <option key={r} value={r}>All {r.toLowerCase()}s</option>)}
      </Select>
      <Form value={v} onChange={setV} />
      <Button className="w-full" size="lg" loading={busy} onClick={save}>Apply</Button>
    </div></Modal>
  );
}

export function PinModal({ open, onClose, employeeId, name, hasPin, onSaved }: { open: boolean; onClose: () => void; employeeId: number; name: string; hasPin: boolean; onSaved: () => void }) {
  const { run, busy } = useAction();
  const [pin, setPin] = useState("");
  useEffect(() => { if (open) setPin(""); }, [open]);
  const save = async (value: string | null) => { if (await run(() => api.post(`/staff/employees/${employeeId}/set-pin/`, { pin: value }), value ? "PIN saved" : "PIN removed")) { onClose(); onSaved(); } };
  return (
    <Modal open={open} onClose={onClose} title={`Attendance PIN · ${name}`} width="max-w-sm"><div className="space-y-4">
      <p className="text-sm text-muted">{name} types this PIN on the attendance tablet to check in and out. 4 to 6 digits, different from everyone else at the branch.</p>
      <Input label="New PIN" inputMode="numeric" maxLength={6} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} className="text-center font-mono text-2xl tracking-[0.5em]" autoFocus />
      <Button className="w-full" size="lg" loading={busy} disabled={pin.length < 4} onClick={() => save(pin)}>{hasPin ? "Change PIN" : "Set PIN"}</Button>
      {hasPin && <Button variant="ghost" className="w-full" onClick={() => save(null)}>Remove PIN</Button>}
    </div></Modal>
  );
}
