"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, HandCoins, Lock, LockOpen, Pencil, Plus, RefreshCw, Wallet } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { PayProfileModal } from "@/components/payroll/PayProfileModal";
import { SlipModal } from "@/components/payroll/SlipModal";
import { fmtDate } from "@/components/Platform";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Select, Spinner, cn, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import { todayIso } from "@/lib/time";
import type { AdvanceRow, PayEmp, PayProfile, PayProfileRow, PayrollRunDetail, PayrollRunRow } from "@/lib/types";

const monthLabel = (m: string) => new Date(m).toLocaleDateString("en-PK", { month: "long", year: "numeric" });
const prevMonth = () => { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; };
const TYPE_LABEL = { MONTHLY: "Monthly", DAILY: "Daily wage", HOURLY: "Hourly" } as const;
const METHODS = [["BANK", "Bank transfer"], ["CASH", "Cash"], ["JAZZCASH", "JazzCash"], ["EASYPAISA", "Easypaisa"], ["CHEQUE", "Cheque"], ["OTHER", "Other"]];

export default function PayrollPage() {
  const { me, location, currency } = useAuth();
  const { run, busy } = useAction();
  const [tab, setTab] = useState<"runs" | "people" | "advances">("runs");
  const [month, setMonth] = useState(prevMonth());
  const [runs, setRuns] = useState<PayrollRunRow[]>([]);
  const [detail, setDetail] = useState<PayrollRunDetail | null>(null);
  const [people, setPeople] = useState<PayProfileRow[]>([]);
  const [advances, setAdvances] = useState<AdvanceRow[]>([]);
  const [advFilter, setAdvFilter] = useState<"ACTIVE" | "CLEARED" | "">("ACTIVE");
  const [loading, setLoading] = useState(true);
  const [slipId, setSlipId] = useState<number | null>(null);
  const [profileFor, setProfileFor] = useState<PayProfileRow | null>(null);
  const [dlg, setDlg] = useState<null | "reopen" | "payall" | "advance" | "repay">(null);
  const [f, setF] = useState({ reason: "", method: "BANK", reference: "", emp: "", amount: "", installment: "", note: "", given: todayIso() });
  const [repayFor, setRepayFor] = useState<AdvanceRow | null>(null);

  const loadRuns = useCallback(async () => { if (location) setRuns(await api.get<PayrollRunRow[]>("/payroll/runs/", { location: location.id })); }, [location]);
  const loadPeople = useCallback(async () => { if (location) setPeople(await api.get<PayProfileRow[]>("/payroll/profiles/", { location: location.id })); }, [location]);
  const loadAdvances = useCallback(async () => { if (location) setAdvances(await api.get<AdvanceRow[]>("/payroll/advances/", { location: location.id, status: advFilter })); }, [location, advFilter]);
  const reloadDetail = useCallback(async (id: number) => setDetail(await api.get<PayrollRunDetail>(`/payroll/runs/${id}/`)), []);
  useEffect(() => { Promise.all([loadRuns(), loadPeople()]).finally(() => setLoading(false)); }, [loadRuns, loadPeople]);
  useEffect(() => { loadAdvances().catch(() => undefined); }, [loadAdvances]);

  const existing = useMemo(() => runs.find((r) => r.month.slice(0, 7) === month), [runs, month]);
  const refresh = async () => { await loadRuns(); if (detail) await reloadDetail(detail.id); await loadPeople(); await loadAdvances(); };

  if (me && !me.organization) return <PlatformNotice />;
  if (!me?.is_owner) return <EmptyState title="Payroll is for the owner" hint="Salaries are private. Only the restaurant owner can see them." />;
  if (loading) return <Spinner label="Loading payroll…" />;

  const prepare = async () => { const r = await run(() => api.post<PayrollRunDetail>("/payroll/runs/", { location: location!.id, month })); if (r) { setDetail(r); loadRuns(); } };
  const open = async (r: PayrollRunRow) => { setMonth(r.month.slice(0, 7)); await reloadDetail(r.id); };
  const act = async (action: string, body: Record<string, unknown> = {}, ok = "Done") => {
    const r = await run(() => api.post<PayrollRunDetail>(`/payroll/runs/${detail!.id}/${action}/`, body), ok);
    if (r) { setDetail(r); setDlg(null); loadRuns(); loadAdvances(); }
  };
  const giveAdvance = async () => {
    const r = await run(() => api.post("/payroll/advances/", { employee: Number(f.emp), amount: f.amount, installment: f.installment || null, given_on: f.given, reason: f.note }), "Advance recorded");
    if (r) { setDlg(null); setF((s) => ({ ...s, amount: "", installment: "", note: "" })); loadAdvances(); loadPeople(); }
  };
  const repay = async () => { const r = await run(() => api.post(`/payroll/advances/${repayFor!.id}/repay/`, { amount: f.amount, note: f.note }), "Repayment recorded"); if (r) { setDlg(null); loadAdvances(); loadPeople(); } };
  const voidAdvance = async (a: AdvanceRow) => { if (confirm(`Cancel the advance of ${money(a.amount, currency)} to ${a.employee.name}?`) && (await run(() => api.post(`/payroll/advances/${a.id}/void/`), "Cancelled"))) { loadAdvances(); loadPeople(); } };
  const noProfile = people.filter((p) => !p.profile);
  const totalOwed = people.reduce((s, p) => s + Number(p.advance_balance), 0);

  return (
    <>
      <PageHeader title="Payroll" subtitle={`${location?.name} · salaries, overtime, advances and payslips. Private to you.`} />
      <div className="mb-5 inline-flex rounded-xl bg-sunken p-1">
        {([["runs", "Monthly payroll"], ["people", "People & pay"], ["advances", "Advances"]] as const).map(([id, l]) => (
          <button key={id} onClick={() => setTab(id)} className={cn("rounded-lg px-4 py-2 text-sm font-semibold transition", tab === id ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink")}>
            {l}{id === "people" && noProfile.length > 0 && <span className="ml-2 rounded-full bg-warn px-2 py-0.5 text-[11px] font-bold text-white">{noProfile.length}</span>}
          </button>))}
      </div>

      {tab === "runs" && (
        <div className="space-y-6">
          <Card className="p-5">
            <div className="flex flex-wrap items-end gap-3">
              <Input label="Month" type="month" className="w-48" value={month} max={todayIso().slice(0, 7)} onChange={(e) => { setMonth(e.target.value); setDetail(null); }} />
              {existing ? <Button variant="secondary" onClick={() => open(existing)}>Open {monthLabel(existing.month)} ({existing.status === "FINALIZED" ? "finalized" : "draft"})</Button>
                : <Button loading={busy} onClick={prepare}>Prepare payroll</Button>}
              <p className="max-w-md text-xs text-muted">Pulls attendance, overtime, deliveries and advances for the month and works out everyone&apos;s pay. Nothing is paid or locked until you finalize.</p>
            </div>
            {noProfile.length > 0 && <p className="mt-3 flex items-center gap-2 text-sm text-warn"><AlertTriangle className="h-4 w-4" />{noProfile.length} employee{noProfile.length > 1 ? "s have" : " has"} no pay set up and will not be in payroll. See “People &amp; pay”.</p>}
          </Card>

          {detail && (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3"><h2 className="text-xl font-bold">{monthLabel(detail.month)}</h2><Badge tone={detail.status === "FINALIZED" ? "good" : "warn"}>{detail.status === "FINALIZED" ? "Finalized" : "Draft"}</Badge></div>
                <div className="flex flex-wrap gap-2">
                  {detail.status === "DRAFT" ? <>
                    <Button variant="secondary" loading={busy} onClick={() => act("regenerate", {}, "Recalculated")}><RefreshCw className="h-4 w-4" />Recalculate</Button>
                    <Button disabled={!detail.can_finalize} loading={busy} onClick={() => confirm("Finalize this month? Advance installments are taken and the payslips are locked.") && act("finalize", {}, "Payroll finalized")}><Lock className="h-4 w-4" />Finalize</Button></>
                    : <>
                      {detail.unpaid > 0 && <Button onClick={() => { setF((s) => ({ ...s, method: "BANK", reference: "" })); setDlg("payall"); }}><HandCoins className="h-4 w-4" />Pay all ({detail.unpaid})</Button>}
                      {detail.paid === 0 && <Button variant="ghost" onClick={() => { setF((s) => ({ ...s, reason: "" })); setDlg("reopen"); }}><LockOpen className="h-4 w-4" />Reopen</Button>}</>}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                {[["Employees", String(detail.employees), ""], ["Gross", money(detail.gross, currency), ""], ["Deductions", money(detail.deductions, currency), "text-bad"], ["Net to pay", money(detail.net, currency), "text-brand"]].map(([l, v, c]) => <Card key={l} className="p-5"><p className="text-sm text-muted">{l}</p><p className={cn("text-2xl font-bold tracking-tight", c)}>{v}</p></Card>)}
              </div>

              {detail.blockers.length > 0 && (
                <div className="rounded-2xl bg-warn-soft p-4 text-sm text-warn"><p className="mb-1 flex items-center gap-2 font-bold"><AlertTriangle className="h-4 w-4" />Fix these before you can finalize</p><ul className="list-disc space-y-0.5 pl-6">{detail.blockers.map((b) => <li key={b}>{b}</li>)}</ul>
                  <p className="mt-2 text-xs">Mark attendance in Staff → Attendance, then press Recalculate.</p></div>
              )}

              <Card className="overflow-hidden"><div className="overflow-x-auto"><table className="w-full text-sm">
                <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Employee</th><th className="px-5 py-3">Pay type</th><th className="px-5 py-3 text-right">Gross</th><th className="px-5 py-3 text-right">Deductions</th><th className="px-5 py-3 text-right">Net</th><th className="px-5 py-3">Status</th></tr></thead>
                <tbody className="divide-y divide-line">
                  {detail.slips.map((s) => (
                    <tr key={s.id} className="cursor-pointer hover:bg-sunken/50" onClick={() => setSlipId(s.id)}>
                      <td className="px-5 py-3"><p className="font-semibold">{s.employee.name}</p><p className="text-xs text-muted">{s.employee.role_display}{s.warnings.length > 0 && <span className="ml-2 inline-flex items-center gap-1 text-warn"><AlertTriangle className="h-3 w-3" />{s.warnings.length}</span>}</p></td>
                      <td className="px-5 py-3 text-muted">{TYPE_LABEL[s.pay_type]}</td>
                      <td className="px-5 py-3 text-right">{money(s.gross, currency)}</td><td className="px-5 py-3 text-right text-bad">{Number(s.deductions) ? `−${money(s.deductions, currency)}` : "-"}</td>
                      <td className="px-5 py-3 text-right font-bold">{money(s.net, currency)}</td>
                      <td className="px-5 py-3">{s.status === "PAID" ? <Badge tone="good"><CheckCircle2 className="h-3 w-3" />Paid</Badge> : s.status === "UNPAID" ? <Badge tone="warn">To pay</Badge> : <Badge>Draft</Badge>}</td>
                    </tr>))}
                  {detail.slips.length === 0 && <tr><td colSpan={6} className="px-5 py-10 text-center text-muted">Nobody has pay set up yet.</td></tr>}
                </tbody></table></div></Card>
            </>
          )}

          {!detail && runs.length > 0 && (
            <Card className="overflow-hidden"><div className="border-b border-line px-5 py-4"><h2 className="font-bold">Past payrolls</h2></div>
              <ul className="divide-y divide-line text-sm">{runs.map((r) => (
                <li key={r.id}><button onClick={() => open(r)} className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left hover:bg-sunken/50">
                  <span><b>{monthLabel(r.month)}</b><span className="block text-xs text-muted">{r.employees} people · net {money(r.net, currency)}</span></span>
                  <span className="flex items-center gap-2">{r.unpaid > 0 && <Badge tone="warn">{r.unpaid} to pay</Badge>}<Badge tone={r.status === "FINALIZED" ? "good" : "neutral"}>{r.status === "FINALIZED" ? (r.unpaid === 0 ? "Paid" : "Finalized") : "Draft"}</Badge></span></button></li>))}</ul></Card>
          )}
        </div>
      )}

      {tab === "people" && (
        <Card className="overflow-hidden"><div className="overflow-x-auto"><table className="w-full text-sm">
          <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Employee</th><th className="px-5 py-3">Pay</th><th className="px-5 py-3 text-right">Allowance</th><th className="px-5 py-3 text-right">Advance owed</th><th className="px-5 py-3" /></tr></thead>
          <tbody className="divide-y divide-line">
            {people.map((p) => (
              <tr key={p.employee.id}>
                <td className="px-5 py-3"><p className="font-semibold">{p.employee.name}</p><p className="text-xs text-muted">{p.employee.role_display}</p></td>
                <td className="px-5 py-3">{p.profile ? <><b>{money(p.profile.base_amount, currency)}</b><span className="ml-2 text-xs text-muted">{p.profile.pay_type === "MONTHLY" ? "a month" : p.profile.pay_type === "DAILY" ? "a day" : "an hour"}</span></> : <Badge tone="warn">Not set up</Badge>}</td>
                <td className="px-5 py-3 text-right text-muted">{p.profile && Number(p.profile.fixed_allowance) ? money(p.profile.fixed_allowance, currency) : "-"}</td>
                <td className="px-5 py-3 text-right">{Number(p.advance_balance) ? <span className="font-semibold text-warn">{money(p.advance_balance, currency)}</span> : "-"}</td>
                <td className="px-5 py-3 text-right"><Button size="sm" variant={p.profile ? "ghost" : "primary"} onClick={() => setProfileFor(p)}>{p.profile ? <Pencil className="h-4 w-4" /> : "Set up pay"}</Button></td>
              </tr>))}
            {people.length === 0 && <tr><td colSpan={5} className="px-5 py-10 text-center text-muted">Add employees in Staff first.</td></tr>}
          </tbody></table></div></Card>
      )}

      {tab === "advances" && (
        <>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex gap-2">{([["ACTIVE", "Being repaid"], ["CLEARED", "Repaid"], ["", "All"]] as const).map(([id, l]) => <button key={id} onClick={() => setAdvFilter(id)} className={cn("rounded-full border px-3.5 py-1.5 text-sm font-semibold", advFilter === id ? "border-brand bg-brand text-white" : "border-line bg-surface text-muted hover:text-ink")}>{l}</button>)}</div>
            <div className="flex items-center gap-3">{totalOwed > 0 && <span className="text-sm text-muted">Total owed to you: <b className="text-warn">{money(totalOwed, currency)}</b></span>}<Button onClick={() => { setF((s) => ({ ...s, emp: "", amount: "", installment: "", note: "", given: todayIso() })); setDlg("advance"); }}><Plus className="h-4 w-4" />Give advance</Button></div>
          </div>
          {advances.length === 0 ? <EmptyState icon={<Wallet className="h-8 w-8" />} title="No advances" hint="When you give an employee money in advance, record it here. The installments come out of their salary automatically." /> : (
            <Card className="overflow-hidden"><div className="overflow-x-auto"><table className="w-full text-sm">
              <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Employee</th><th className="px-5 py-3">Given</th><th className="px-5 py-3 text-right">Amount</th><th className="px-5 py-3 text-right">Per month</th><th className="px-5 py-3 text-right">Repaid</th><th className="px-5 py-3 text-right">Owes</th><th className="px-5 py-3" /></tr></thead>
              <tbody className="divide-y divide-line">
                {advances.map((a) => (
                  <tr key={a.id}>
                    <td className="px-5 py-3"><p className="font-semibold">{a.employee.name}</p><p className="text-xs text-muted">{a.reason || "-"}</p></td>
                    <td className="px-5 py-3 text-muted">{fmtDate(a.given_on)}</td><td className="px-5 py-3 text-right">{money(a.amount, currency)}</td>
                    <td className="px-5 py-3 text-right text-muted">{money(a.installment, currency)}</td><td className="px-5 py-3 text-right">{money(a.repaid, currency)}</td>
                    <td className="px-5 py-3 text-right font-bold">{a.status === "ACTIVE" ? money(a.balance, currency) : a.status === "VOID" ? <Badge>Cancelled</Badge> : <Badge tone="good">Cleared</Badge>}</td>
                    <td className="px-5 py-3 text-right">{a.status === "ACTIVE" && <div className="flex justify-end gap-1.5"><Button size="sm" variant="secondary" onClick={() => { setRepayFor(a); setF((s) => ({ ...s, amount: "", note: "" })); setDlg("repay"); }}>Repay</Button>{Number(a.repaid) === 0 && <Button size="sm" variant="ghost" onClick={() => voidAdvance(a)}>Cancel</Button>}</div>}</td>
                  </tr>))}
              </tbody></table></div></Card>
          )}
        </>
      )}

      <SlipModal slipId={slipId} onClose={() => setSlipId(null)} onChanged={refresh} business={me.organization!.name} currency={currency} />
      <PayProfileModal open={!!profileFor} onClose={() => setProfileFor(null)} employee={profileFor?.employee as PayEmp | null} profile={(profileFor?.profile as PayProfile | null) ?? null} currency={currency} onSaved={() => { loadPeople(); loadRuns(); }} />

      <Modal open={dlg === "reopen"} onClose={() => setDlg(null)} title="Reopen this month" width="max-w-sm"><div className="space-y-4">
        <p className="text-sm text-muted">Payslips go back to draft and advance installments are returned. You can only do this while nobody has been paid.</p>
        <Input label="Why? (required)" value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} />
        <Button className="w-full" loading={busy} disabled={f.reason.trim().length < 3} onClick={() => act("reopen", { reason: f.reason }, "Reopened")}>Reopen</Button></div></Modal>
      <Modal open={dlg === "payall"} onClose={() => setDlg(null)} title="Pay everyone" width="max-w-sm"><div className="space-y-4">
        <p className="text-sm text-muted">Marks all {detail?.unpaid} unpaid salaries ({money(detail?.net ?? 0, currency)}) as paid. To pay from your cash drawer, pay people one by one.</p>
        <Select label="How" value={f.method} onChange={(e) => setF({ ...f, method: e.target.value })}>{METHODS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select>
        <Input label="Reference (optional)" value={f.reference} onChange={(e) => setF({ ...f, reference: e.target.value })} />
        <Button className="w-full" size="lg" loading={busy} onClick={() => act("pay-all", { method: f.method, reference: f.reference }, "All salaries marked paid")}>Mark all paid</Button></div></Modal>
      <Modal open={dlg === "advance"} onClose={() => setDlg(null)} title="Give an advance" width="max-w-sm"><div className="space-y-4">
        <Select label="Employee" value={f.emp} onChange={(e) => setF({ ...f, emp: e.target.value })}><option value="">Choose…</option>{people.map((p) => <option key={p.employee.id} value={p.employee.id}>{p.employee.name} · {p.employee.role_display}</option>)}</Select>
        <div className="grid grid-cols-2 gap-3"><Input label={`Amount (${currency})`} type="number" min="0" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /><Input label="Taken per month" type="number" min="0" value={f.installment} onChange={(e) => setF({ ...f, installment: e.target.value })} hint="Empty = all at once" /></div>
        <Input label="Date" type="date" max={todayIso()} value={f.given} onChange={(e) => setF({ ...f, given: e.target.value })} />
        <Input label="Reason" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} placeholder="e.g. Medical, rent" />
        <Button className="w-full" size="lg" loading={busy} disabled={!f.emp || !(Number(f.amount) > 0)} onClick={giveAdvance}>Record advance</Button></div></Modal>
      <Modal open={dlg === "repay"} onClose={() => setDlg(null)} title={`Repayment · ${repayFor?.employee.name ?? ""}`} width="max-w-sm"><div className="space-y-4">
        <p className="text-sm text-muted">Still owed: <b>{money(repayFor?.balance ?? 0, currency)}</b>. Use this when they pay back directly (cash). Salary installments are taken automatically.</p>
        <Input label={`Amount (${currency})`} type="number" min="0" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /><Input label="Note" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} />
        <Button className="w-full" loading={busy} disabled={!(Number(f.amount) > 0)} onClick={repay}>Record repayment</Button></div></Modal>
    </>
  );
}
