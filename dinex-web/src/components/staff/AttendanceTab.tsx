"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CalendarClock, Download, Monitor, Pencil } from "lucide-react";
import { BulkScheduleModal } from "@/components/staff/ScheduleModals";
import { Badge, Button, Card, EmptyState, Input, Modal, Select, Spinner, Textarea, cn, useAction } from "@/components/ui";
import { fmtDate } from "@/components/Platform";
import { api } from "@/lib/api";
import { DAYS, addDays, csv, download, fmtMin, hhmm, nowHHMM, todayIso } from "@/lib/time";
import type { AttReport, AttReportRow, AttRecord, Board, BoardRow, DayState } from "@/lib/types";

const STATE: Record<DayState, { label: string; tone: "brand" | "good" | "warn" | "bad" | "neutral" }> = {
  ON_DUTY: { label: "On duty", tone: "brand" }, DONE: { label: "Done", tone: "good" }, ABSENT: { label: "Absent", tone: "bad" }, ABSENT_DERIVED: { label: "Absent (not marked)", tone: "bad" },
  LEAVE: { label: "On leave", tone: "neutral" }, OFF: { label: "Weekly off", tone: "neutral" }, NO_SCHEDULE: { label: "No duty set", tone: "neutral" },
  UPCOMING: { label: "Later today", tone: "neutral" }, NOT_JOINED: { label: "Not joined", tone: "neutral" }, NOT_IN: { label: "Not in yet", tone: "warn" },
};
const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const PRESETS = [
  { label: "This month", from: () => todayIso().slice(0, 8) + "01", to: () => todayIso() },
  { label: "Last 7 days", from: () => addDays(todayIso(), -6), to: () => todayIso() },
  { label: "Last month", from: () => { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - 1); return iso(d); }, to: () => { const d = new Date(); d.setDate(0); return iso(d); } },
];
const localDT = (s: string | null) => (s ? iso(new Date(s)) + "T" + new Date(s).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) : "");

export function AttendanceTab({ locationId, canManage }: { locationId: number; canManage: boolean }) {
  const { run, busy } = useAction();
  const [view, setView] = useState<"day" | "report">("day");
  const [date, setDate] = useState(todayIso());
  const [board, setBoard] = useState<Board | null>(null);
  const [report, setReport] = useState<AttReport | null>(null);
  const [from, setFrom] = useState(PRESETS[0].from()); const [to, setTo] = useState(PRESETS[0].to());
  const [loading, setLoading] = useState(true);
  const [dlg, setDlg] = useState<null | { kind: "in" | "out" | "mark" | "edit" | "bulk" | "detail"; row?: BoardRow; rep?: AttReportRow }>(null);
  const [f, setF] = useState({ time: "", status: "ABSENT", paid: true, note: "", reason: "", cin: "", cout: "" });
  const [detail, setDetail] = useState<AttRecord[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (view === "day") setBoard(await api.get<Board>("/staff/attendance/", { location: locationId, date }));
      else setReport(await api.get<AttReport>("/staff/attendance/report/", { location: locationId, from, to }));
    } finally { setLoading(false); }
  }, [view, locationId, date, from, to]);
  useEffect(() => { load().catch(() => setLoading(false)); }, [load]);

  const openPunch = (kind: "in" | "out", row: BoardRow) => { setF((s) => ({ ...s, time: date === todayIso() ? nowHHMM() : (kind === "in" ? row.schedule?.start_time : row.schedule?.end_time)?.slice(0, 5) ?? "12:00", note: "" })); setDlg({ kind, row }); };
  const openMark = (row: BoardRow) => { setF((s) => ({ ...s, status: "ABSENT", paid: true, note: "" })); setDlg({ kind: "mark", row }); };
  const openEdit = (row: BoardRow) => { const r = row.record!; setF((s) => ({ ...s, status: r.status, paid: r.paid_leave, cin: localDT(r.check_in), cout: localDT(r.check_out), reason: "" })); setDlg({ kind: "edit", row }); };

  async function savePunch() {
    const row = dlg!.row!; let when = `${date}T${f.time}`;
    if (dlg!.kind === "out" && row.record?.check_in) {          // a check-out earlier on the clock than the check-in means "after midnight"
      const inDay = localDT(row.record.check_in).slice(0, 10); when = `${inDay}T${f.time}`;
      if (when <= localDT(row.record.check_in)) when = `${addDays(inDay, 1)}T${f.time}`;
    }
    const r = await run(() => api.post("/staff/attendance/punch/", { employee: row.employee.id, action: dlg!.kind === "in" ? "IN" : "OUT", time: when, note: f.note }), dlg!.kind === "in" ? "Checked in" : "Checked out");
    if (r) { setDlg(null); load(); }
  }
  async function saveMark() {
    const r = await run(() => api.post("/staff/attendance/mark/", { employee: dlg!.row!.employee.id, date, status: f.status, paid: f.status === "LEAVE" ? f.paid : false, note: f.note }), "Saved");
    if (r) { setDlg(null); load(); }
  }
  async function saveEdit() {
    const body: Record<string, unknown> = { status: f.status, reason: f.reason };
    if (f.status === "PRESENT") { body.check_in = f.cin; body.check_out = f.cout || null; }
    if (f.status === "LEAVE") body.paid_leave = f.paid;
    const r = await run(() => api.patch(`/staff/attendance/${dlg!.row!.record!.id}/`, body), "Corrected. The change is in the audit log.");
    if (r) { setDlg(null); load(); }
  }
  async function openDetail(rep: AttReportRow) {
    const r = await run(() => api.get<AttReport>("/staff/attendance/report/", { location: locationId, from, to, employee: rep.employee.id }));
    setDetail(r?.rows[0]?.records ?? []); setDlg({ kind: "detail", rep });
  }
  function exportCsv() {
    if (!report) return;
    download(`attendance_${report.from}_${report.to}.csv`, csv([["Code", "Name", "Role", "Scheduled days", "Present", "Late days", "Late min", "Absent", "Paid leave", "Unpaid leave", "Hours worked", "Overtime hours", "Off-days worked", "Missing check-outs"],
      ...report.rows.map((r) => [r.employee.code, r.employee.name, r.employee.role_display, r.scheduled_days, r.present_days, r.late_days, r.late_minutes, r.absent_days, r.leave_paid, r.leave_unpaid, (r.worked_minutes / 60).toFixed(1), (r.overtime_minutes / 60).toFixed(1), r.off_days_worked, r.missing_checkouts])]));
  }
  const counts = board?.counts ?? {};
  const chips = useMemo(() => [["ON_DUTY", "On duty"], ["DONE", "Done"], ["NOT_IN", "Not in yet"], ["ABSENT", "Absent"], ["LEAVE", "On leave"], ["OFF", "Off"]] as const, []);

  return (
    <>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-xl bg-sunken p-1">{([["day", "Day board"], ["report", "Report"]] as const).map(([id, l]) => <button key={id} onClick={() => setView(id)} className={cn("rounded-lg px-4 py-2 text-sm font-semibold transition", view === id ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink")}>{l}</button>)}</div>
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/kiosk"><Button variant="secondary"><Monitor className="h-4 w-4" />Open PIN kiosk</Button></Link>
          {canManage && <Button variant="secondary" onClick={() => setDlg({ kind: "bulk" })}><CalendarClock className="h-4 w-4" />Duty hours for a group</Button>}
        </div>
      </div>

      {view === "day" ? (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <Input aria-label="Date" type="date" className="w-44" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value || todayIso())} />
            <Button variant="ghost" size="sm" onClick={() => setDate(addDays(date, -1))}>← Previous day</Button>
            {date !== todayIso() && <Button variant="ghost" size="sm" onClick={() => setDate(todayIso())}>Today</Button>}
            <div className="ml-auto flex flex-wrap gap-2 text-xs">{chips.map(([k, l]) => <span key={k} className="rounded-full bg-sunken px-3 py-1.5 font-semibold">{l} <b className="ml-1 text-base">{(counts[k] ?? 0) + (k === "ABSENT" ? counts["ABSENT_DERIVED"] ?? 0 : 0)}</b></span>)}</div>
          </div>
          {loading && !board ? <Spinner /> : !board || board.rows.length === 0 ? <EmptyState title="No employees at this branch yet" /> : (
            <Card className="overflow-hidden"><div className="overflow-x-auto"><table className="w-full text-sm">
              <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Employee</th><th className="px-5 py-3">Duty</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">In → Out</th><th className="px-5 py-3 text-right">Worked</th><th className="px-5 py-3 text-right">Overtime</th>{canManage && <th className="px-5 py-3" />}</tr></thead>
              <tbody className="divide-y divide-line">
                {board.rows.map((r) => {
                  const st = STATE[r.state], rec = r.record; const off = r.schedule?.weekly_off.map((d) => DAYS[d]).join(", ");
                  return (
                    <tr key={r.employee.id} className="hover:bg-sunken/40">
                      <td className="px-5 py-3"><p className="font-semibold">{r.employee.name}</p><p className="text-xs text-muted">{r.employee.role_display}{!r.employee.has_pin && " · no PIN"}</p></td>
                      <td className="px-5 py-3 text-muted">{r.schedule ? <>{r.schedule.start_time}–{r.schedule.end_time}{off && <span className="block text-xs">off: {off}</span>}</> : "-"}</td>
                      <td className="px-5 py-3"><div className="flex flex-wrap items-center gap-1"><Badge tone={st.tone}>{rec?.status === "LEAVE" ? (rec.paid_leave ? "Paid leave" : "Unpaid leave") : st.label}</Badge>{!!rec?.late_minutes && <Badge tone="warn">Late {fmtMin(rec.late_minutes)}</Badge>}{!!rec?.early_leave_minutes && <Badge tone="warn">Left early {fmtMin(rec.early_leave_minutes)}</Badge>}{rec?.on_off_day && <Badge tone="brand">Off-day work</Badge>}{rec?.auto_closed && <Badge tone="bad">No check-out</Badge>}</div></td>
                      <td className="px-5 py-3 text-muted">{rec?.check_in ? `${hhmm(rec.check_in)} → ${rec.check_out ? hhmm(rec.check_out) : "…"}` : "-"}</td>
                      <td className="px-5 py-3 text-right">{fmtMin(rec?.worked_minutes)}</td>
                      <td className={cn("px-5 py-3 text-right font-semibold", rec?.overtime_minutes ? "text-good" : "text-muted")}>{fmtMin(rec?.overtime_minutes)}</td>
                      {canManage && <td className="px-5 py-3"><div className="flex justify-end gap-1.5">
                        {r.state === "ON_DUTY" ? <Button size="sm" onClick={() => openPunch("out", r)}>Check out</Button>
                          : !rec ? <><Button size="sm" onClick={() => openPunch("in", r)}>Check in</Button><Button size="sm" variant="ghost" onClick={() => openMark(r)}>Absent / leave</Button></> : null}
                        {rec && <Button size="sm" variant="ghost" aria-label={`Edit ${r.employee.name}`} onClick={() => openEdit(r)}><Pencil className="h-4 w-4" /></Button>}
                      </div></td>}
                    </tr>
                  );
                })}
              </tbody></table></div></Card>
          )}
        </>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            {PRESETS.map((p) => <button key={p.label} onClick={() => { setFrom(p.from()); setTo(p.to()); }} className={cn("rounded-full border px-3.5 py-1.5 text-sm font-semibold", from === p.from() && to === p.to() ? "border-brand bg-brand text-white" : "border-line bg-surface text-muted hover:text-ink")}>{p.label}</button>)}
            <Input aria-label="From" type="date" className="w-40" value={from} max={to} onChange={(e) => setFrom(e.target.value)} /><Input aria-label="To" type="date" className="w-40" value={to} min={from} max={todayIso()} onChange={(e) => setTo(e.target.value)} />
            <Button variant="secondary" className="ml-auto" onClick={exportCsv} disabled={!report?.rows.length}><Download className="h-4 w-4" />Export CSV</Button>
          </div>
          {loading && !report ? <Spinner /> : !report || report.rows.length === 0 ? <EmptyState title="No data" /> : (
            <Card className="overflow-hidden"><div className="overflow-x-auto"><table className="w-full text-sm">
              <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Employee</th><th className="px-5 py-3 text-right">Scheduled</th><th className="px-5 py-3 text-right">Present</th><th className="px-5 py-3 text-right">Late</th><th className="px-5 py-3 text-right">Absent</th><th className="px-5 py-3 text-right">Leave</th><th className="px-5 py-3 text-right">Hours</th><th className="px-5 py-3 text-right">Overtime</th><th className="px-5 py-3 text-right">Issues</th></tr></thead>
              <tbody className="divide-y divide-line">
                {report.rows.map((r) => (
                  <tr key={r.employee.id} className="cursor-pointer hover:bg-sunken/50" onClick={() => openDetail(r)}>
                    <td className="px-5 py-3"><p className="font-semibold">{r.employee.name}</p><p className="text-xs text-muted">{r.employee.role_display}</p></td>
                    <td className="px-5 py-3 text-right text-muted">{r.scheduled_days}</td><td className="px-5 py-3 text-right">{r.present_days}</td>
                    <td className="px-5 py-3 text-right">{r.late_days > 0 ? <span className="text-warn">{r.late_days}× · {fmtMin(r.late_minutes)}</span> : "-"}</td>
                    <td className={cn("px-5 py-3 text-right", r.absent_days > 0 && "font-semibold text-bad")}>{r.absent_days || "-"}</td>
                    <td className="px-5 py-3 text-right text-muted">{r.leave_paid + r.leave_unpaid || "-"}</td>
                    <td className="px-5 py-3 text-right">{(r.worked_minutes / 60).toFixed(1)}</td>
                    <td className="px-5 py-3 text-right font-semibold text-good">{r.overtime_minutes ? fmtMin(r.overtime_minutes) : "-"}</td>
                    <td className="px-5 py-3 text-right">{r.missing_checkouts > 0 ? <Badge tone="bad">{r.missing_checkouts} no check-out</Badge> : "-"}</td>
                  </tr>
                ))}
              </tbody></table></div></Card>
          )}
        </>
      )}

      <Modal open={dlg?.kind === "in" || dlg?.kind === "out"} onClose={() => setDlg(null)} title={`${dlg?.kind === "in" ? "Check in" : "Check out"} · ${dlg?.row?.employee.name ?? ""}`} width="max-w-sm"><div className="space-y-4">
        <Input label={`Time on ${fmtDate(date)}`} type="time" value={f.time} onChange={(e) => setF({ ...f, time: e.target.value })} />
        <Textarea label="Note (needed if this was earlier)" rows={2} value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} />
        <Button className="w-full" size="lg" loading={busy} disabled={!f.time} onClick={savePunch}>{dlg?.kind === "in" ? "Check in" : "Check out"}</Button></div></Modal>
      <Modal open={dlg?.kind === "mark"} onClose={() => setDlg(null)} title={`Absent or leave · ${dlg?.row?.employee.name ?? ""}`} width="max-w-sm"><div className="space-y-4">
        <Select label="What happened?" value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}><option value="ABSENT">Absent (did not come)</option><option value="LEAVE">On leave</option></Select>
        {f.status === "LEAVE" && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.paid} onChange={(e) => setF({ ...f, paid: e.target.checked })} className="h-4 w-4 accent-[rgb(var(--brand))]" />Paid leave</label>}
        <Input label="Note (optional)" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} />
        <Button className="w-full" size="lg" loading={busy} onClick={saveMark}>Save</Button></div></Modal>
      <Modal open={dlg?.kind === "edit"} onClose={() => setDlg(null)} title={`Correct ${dlg?.row?.employee.name ?? ""} · ${fmtDate(date)}`} width="max-w-sm"><div className="space-y-4">
        <Select label="Status" value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}><option value="PRESENT">Present</option><option value="ABSENT">Absent</option><option value="LEAVE">On leave</option></Select>
        {f.status === "PRESENT" && <><Input label="Check in" type="datetime-local" value={f.cin} onChange={(e) => setF({ ...f, cin: e.target.value })} /><Input label="Check out" type="datetime-local" value={f.cout} onChange={(e) => setF({ ...f, cout: e.target.value })} hint="Leave empty if still working" /></>}
        {f.status === "LEAVE" && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.paid} onChange={(e) => setF({ ...f, paid: e.target.checked })} className="h-4 w-4 accent-[rgb(var(--brand))]" />Paid leave</label>}
        <Input label="Reason for the change (required)" value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} />
        <Button className="w-full" size="lg" loading={busy} disabled={f.reason.trim().length < 3} onClick={saveEdit}>Save correction</Button></div></Modal>
      <Modal open={dlg?.kind === "detail"} onClose={() => setDlg(null)} title={`${dlg?.rep?.employee.name ?? ""} · ${fmtDate(from)} to ${fmtDate(to)}`} width="max-w-xl">
        <ul className="divide-y divide-line text-sm">{detail.map((r) => (
          <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5"><span className="font-medium">{fmtDate(r.date)}</span>
            <span className="flex flex-wrap items-center gap-1.5">{r.status === "PRESENT" ? <><span className="text-muted">{hhmm(r.check_in)} → {r.check_out ? hhmm(r.check_out) : "…"}</span>{r.late_minutes > 0 && <Badge tone="warn">late {fmtMin(r.late_minutes)}</Badge>}{r.overtime_minutes > 0 && <Badge tone="good">OT {fmtMin(r.overtime_minutes)}</Badge>}{r.auto_closed && <Badge tone="bad">no check-out</Badge>}</> : <Badge tone={r.status === "ABSENT" ? "bad" : "neutral"}>{r.status === "LEAVE" ? (r.paid_leave ? "Paid leave" : "Unpaid leave") : "Absent"}</Badge>}</span></li>
        ))}{detail.length === 0 && <li className="py-6 text-center text-muted">No records in this period.</li>}</ul></Modal>
      <BulkScheduleModal open={dlg?.kind === "bulk"} onClose={() => setDlg(null)} locationId={locationId} onSaved={load} />
    </>
  );
}
