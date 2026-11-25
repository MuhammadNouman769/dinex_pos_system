"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Bike, CheckCircle2, Clock, HandCoins, KeyRound, Pencil, Plus, Search, Timer, Trash2, UserRound } from "lucide-react";
import { AttendanceTab } from "@/components/staff/AttendanceTab";
import { PinModal, ScheduleModal } from "@/components/staff/ScheduleModals";
import { DAYS, fmtMin, hhmm } from "@/lib/time";
import { PlatformNotice } from "@/components/AppShell";
import { fmtDate, fmtDateTime } from "@/components/Platform";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Select, Spinner, cn, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { EmpRole, Employee, EmployeeDetail, Paginated, RiderLedger, RiderRow } from "@/lib/types";

const ROLES: { id: EmpRole; label: string }[] = [
  { id: "MANAGER", label: "Manager" }, { id: "CASHIER", label: "Cashier" }, { id: "WAITER", label: "Waiter" }, { id: "RIDER", label: "Delivery rider" },
  { id: "CHEF", label: "Chef" }, { id: "HELPER", label: "Kitchen helper" }, { id: "OTHER", label: "Other" },
];
const TONE: Record<EmpRole, "brand" | "good" | "warn" | "neutral"> = { MANAGER: "brand", CASHIER: "good", WAITER: "warn", RIDER: "brand", CHEF: "neutral", HELPER: "neutral", OTHER: "neutral" };
const blank = { name: "", role: "WAITER" as EmpRole, location: "", phone: "", cnic: "", address: "", emergency_contact: "", joining_date: "", vehicle: "", delivery_commission: "0" };

export default function StaffPage() {
  const { me, location, currency } = useAuth();
  const { run, busy } = useAction();
  const [tab, setTab] = useState<"team" | "riders" | "attendance">("team");
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [pinOpen, setPinOpen] = useState(false);
  const [team, setTeam] = useState<Employee[]>([]);
  const [riders, setRiders] = useState<RiderRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [role, setRole] = useState<EmpRole | "">("");
  const [search, setSearch] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [edit, setEdit] = useState<Employee | "new" | null>(null);
  const [f, setF] = useState(blank);
  const [detail, setDetail] = useState<EmployeeDetail | null>(null);
  const [settle, setSettle] = useState<RiderLedger | null>(null);
  const [picked, setPicked] = useState<number[]>([]);
  const [handed, setHanded] = useState("");

  const load = useCallback(async () => {
    if (!location) return;
    const [t, r] = await Promise.all([
      api.get<Paginated<Employee>>("/staff/employees/", { location: location.id, active: showInactive ? "false" : "true", page_size: 100 }),
      api.get<RiderRow[]>("/staff/riders/", { location: location.id }),
    ]);
    setTeam(t.results); setRiders(r); setLoading(false);
  }, [location, showInactive]);
  useEffect(() => { load().catch(() => setLoading(false)); }, [load]);

  const shown = useMemo(() => team.filter((e) => (!role || e.role === role) && `${e.name} ${e.phone} ${e.code}`.toLowerCase().includes(search.trim().toLowerCase())), [team, role, search]);
  const counts = useMemo(() => Object.fromEntries(ROLES.map((r) => [r.id, team.filter((e) => e.role === r.id).length])) as Record<EmpRole, number>, [team]);

  if (me && !me.organization) return <PlatformNotice />;
  if (!me?.can_view_reports) return <EmptyState title="Staff is for owners and managers" />;
  if (loading) return <Spinner label="Loading team…" />;

  const set = (k: keyof typeof blank) => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }));
  const open = (e: Employee | "new") => {
    setF(e === "new" ? { ...blank, location: String(location!.id) } : { name: e.name, role: e.role, location: String(e.location), phone: e.phone, cnic: e.cnic, address: e.address, emergency_contact: e.emergency_contact, joining_date: e.joining_date ?? "", vehicle: e.vehicle, delivery_commission: String(Number(e.delivery_commission)) });
    setEdit(e);
  };
  async function save() {
    const body = { ...f, location: Number(f.location), joining_date: f.joining_date || null, delivery_commission: f.role === "RIDER" ? f.delivery_commission || "0" : "0", vehicle: f.role === "RIDER" ? f.vehicle : "" };
    const r = await run(() => edit === "new" ? api.post("/staff/employees/", body) : api.patch(`/staff/employees/${(edit as Employee).id}/`, body), edit === "new" ? "Employee added" : "Saved");
    if (r) { setEdit(null); load(); }
  }
  async function remove(e: Employee) {
    if (!confirm(`Remove ${e.name}? Their past orders keep their name.`)) return;
    if ((await run(() => api.del(`/staff/employees/${e.id}/`), "Removed")) !== undefined) { setDetail(null); load(); }
  }
  async function reactivate(e: Employee) {
    if (await run(() => api.patch(`/staff/employees/${e.id}/`, { is_active: true }), "Reactivated")) load();
  }
  const openDetail = async (e: Employee) => setDetail(await run(() => api.get<EmployeeDetail>(`/staff/employees/${e.id}/`)) ?? null);
  async function openSettle(r: Employee) {
    const led = await run(() => api.get<RiderLedger>(`/staff/riders/${r.id}/ledger/`));
    if (led) { setSettle(led); setPicked(led.orders.map((o) => o.id)); setHanded(String(led.orders.reduce((s, o) => s + Number(o.due), 0))); }
  }
  const expected = settle ? settle.orders.filter((o) => picked.includes(o.id)).reduce((s, o) => s + Number(o.due), 0) : 0;
  const short = Math.max(0, expected - (Number(handed) || 0));
  async function doSettle() {
    const r = await run(() => api.post<{ shortage: number }>(`/staff/riders/${settle!.rider.id}/settle/`, { handed, order_ids: picked }), "Cash received");
    if (r) { setSettle(null); load(); }
  }
  const totalOwed = riders.reduce((s, r) => s + Number(r.summary.to_settle), 0);

  return (
    <>
      <PageHeader title="Staff" subtitle={`${location?.name} · ${team.length} ${showInactive ? "inactive" : "active"} people`} actions={<Button onClick={() => open("new")}><Plus className="h-4 w-4" />Add employee</Button>} />
      <div className="mb-5 inline-flex rounded-xl bg-sunken p-1">
        {([["team", "Team"], ["attendance", "Attendance"], ["riders", "Riders & delivery cash"]] as const).map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)} className={cn("rounded-lg px-4 py-2 text-sm font-semibold transition", tab === id ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink")}>
            {label}{id === "riders" && totalOwed > 0 && <span className="ml-2 rounded-full bg-warn px-2 py-0.5 text-[11px] font-bold text-white">{money(totalOwed, currency)}</span>}
          </button>
        ))}
      </div>

      {tab === "attendance" ? <AttendanceTab locationId={location!.id} canManage /> : tab === "team" ? (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="relative min-w-[220px] flex-1 sm:max-w-sm"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input aria-label="Search" placeholder="Search name, phone, code…" className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} /></div>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setRole("")} className={cn("rounded-full border px-3.5 py-1.5 text-sm font-semibold", role === "" ? "border-brand bg-brand text-white" : "border-line bg-surface text-muted hover:text-ink")}>All</button>
              {ROLES.filter((r) => counts[r.id] > 0 || role === r.id).map((r) => <button key={r.id} onClick={() => setRole(r.id)} className={cn("rounded-full border px-3.5 py-1.5 text-sm font-semibold", role === r.id ? "border-brand bg-brand text-white" : "border-line bg-surface text-muted hover:text-ink")}>{r.label} {counts[r.id]}</button>)}
            </div>
            <label className="flex items-center gap-2 text-sm text-muted"><input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} className="accent-[rgb(var(--brand))]" />Show inactive</label>
          </div>
          {shown.length === 0 ? <EmptyState icon={<UserRound className="h-8 w-8" />} title="No one here yet" hint="Add your waiters, riders, chefs and cashiers. Waiters can then be chosen on every order, and riders on deliveries." action={<Button onClick={() => open("new")}>Add employee</Button>} /> : (
            <Card className="overflow-hidden"><div className="overflow-x-auto"><table className="w-full text-sm">
              <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Name</th><th className="px-5 py-3">Role</th><th className="px-5 py-3">Phone</th><th className="px-5 py-3">Joined</th><th className="px-5 py-3">Login</th><th className="px-5 py-3" /></tr></thead>
              <tbody className="divide-y divide-line">
                {shown.map((e) => (
                  <tr key={e.id} className="cursor-pointer hover:bg-sunken/50" onClick={() => openDetail(e)}>
                    <td className="px-5 py-3"><p className="font-semibold">{e.name}</p><p className="text-xs text-muted">{e.code}</p></td>
                    <td className="px-5 py-3"><Badge tone={TONE[e.role]}>{e.role_display}</Badge></td>
                    <td className="px-5 py-3 text-muted">{e.phone || "-"}</td>
                    <td className="px-5 py-3 text-muted">{fmtDate(e.joining_date)}</td>
                    <td className="px-5 py-3">{e.username ? <Badge tone="good">{e.username}</Badge> : <span className="text-muted">-</span>}</td>
                    <td className="px-5 py-3 text-right" onClick={(ev) => ev.stopPropagation()}>
                      {e.is_active ? <Button size="sm" variant="ghost" aria-label={`Edit ${e.name}`} onClick={() => open(e)}><Pencil className="h-4 w-4" /></Button> : <Button size="sm" variant="secondary" onClick={() => reactivate(e)}>Reactivate</Button>}
                    </td>
                  </tr>
                ))}
              </tbody></table></div></Card>
          )}
        </>
      ) : riders.length === 0 ? (
        <EmptyState icon={<Bike className="h-8 w-8" />} title="No riders yet" hint="Add an employee with the role “Delivery rider”. Then assign riders to delivery orders and settle their cash here." action={<Button onClick={() => { open("new"); setF((s) => ({ ...s, role: "RIDER" })); }}>Add a rider</Button>} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {riders.map((r) => (
            <Card key={r.id} className="flex flex-col p-5">
              <div className="flex items-start justify-between"><div><p className="text-lg font-bold">{r.name}</p><p className="text-xs text-muted">{r.vehicle || "No vehicle noted"} · {r.phone || "no phone"}</p></div>{r.summary.on_road > 0 ? <Badge tone="brand"><Bike className="h-3 w-3" />On the road · {r.summary.on_road}</Badge> : <Badge tone="good">Free</Badge>}</div>
              <dl className="my-4 grid grid-cols-3 gap-3 text-center text-sm">
                <div className="rounded-xl bg-sunken p-2.5"><dd className="text-xl font-bold">{r.summary.delivered_today}</dd><dt className="text-[11px] text-muted">delivered today</dt></div>
                <div className="rounded-xl bg-sunken p-2.5"><dd className="text-xl font-bold">{r.summary.delivered_30d}</dd><dt className="text-[11px] text-muted">last 30 days</dt></div>
                <div className="rounded-xl bg-sunken p-2.5"><dd className="text-xl font-bold">{r.summary.avg_delivery_minutes ?? "-"}</dd><dt className="text-[11px] text-muted">avg minutes</dt></div>
              </dl>
              <div className={cn("mt-auto flex items-center justify-between rounded-xl p-3", Number(r.summary.to_settle) > 0 ? "bg-warn-soft" : "bg-good-soft")}>
                <div><p className={cn("text-xs font-semibold", Number(r.summary.to_settle) > 0 ? "text-warn" : "text-good")}>Cash with rider</p><p className="text-lg font-bold">{money(r.summary.to_settle, currency)}</p><p className="text-xs text-muted">{r.summary.to_settle_orders} order{r.summary.to_settle_orders === 1 ? "" : "s"}</p></div>
                <Button size="sm" disabled={Number(r.summary.to_settle) <= 0} onClick={() => openSettle(r)}><HandCoins className="h-4 w-4" />Take cash</Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit === "new" ? "Add employee" : `Edit ${f.name}`}><div className="space-y-4">
        <Input label="Full name" value={f.name} onChange={set("name")} autoFocus />
        <div className="grid grid-cols-2 gap-3">
          <Select label="Role" value={f.role} onChange={set("role")}>{ROLES.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}</Select>
          <Select label="Branch" value={f.location} onChange={set("location")}>{me.locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</Select>
        </div>
        <div className="grid grid-cols-2 gap-3"><Input label="Phone" value={f.phone} onChange={set("phone")} placeholder="0300-1234567" /><Input label="CNIC (optional)" value={f.cnic} onChange={set("cnic")} placeholder="42101-1234567-1" /></div>
        {f.role === "RIDER" && <div className="grid grid-cols-2 gap-3"><Input label="Vehicle" value={f.vehicle} onChange={set("vehicle")} placeholder="Honda 70 · LEB-1234" /><Input label={`Commission per delivery (${currency})`} type="number" min="0" value={f.delivery_commission} onChange={set("delivery_commission")} /></div>}
        <div className="grid grid-cols-2 gap-3"><Input label="Joining date" type="date" value={f.joining_date} onChange={set("joining_date")} /><Input label="Emergency contact" value={f.emergency_contact} onChange={set("emergency_contact")} /></div>
        <Input label="Address" value={f.address} onChange={set("address")} />
        <Button className="w-full" size="lg" loading={busy} disabled={f.name.trim().length < 2} onClick={save}>{edit === "new" ? "Add employee" : "Save"}</Button>
      </div></Modal>

      <Modal open={!!detail} onClose={() => setDetail(null)} title={detail?.name ?? ""} width="max-w-md">
        {detail && <div className="space-y-4">
          <div className="flex items-center gap-2"><Badge tone={TONE[detail.role]}>{detail.role_display}</Badge><Badge>{detail.code}</Badge>{detail.username && <Badge tone="good">login: {detail.username}</Badge>}</div>
          {detail.stats.kind === "waiter" ? (
            <div className="grid grid-cols-3 gap-3 text-center"><div className="rounded-xl bg-sunken p-3"><p className="text-xl font-bold">{detail.stats.orders_30d}</p><p className="text-[11px] text-muted">orders, 30 days</p></div><div className="rounded-xl bg-sunken p-3"><p className="text-lg font-bold">{money(detail.stats.sales_30d, currency)}</p><p className="text-[11px] text-muted">sales</p></div><div className="rounded-xl bg-sunken p-3"><p className="text-lg font-bold">{money(detail.stats.average_bill, currency)}</p><p className="text-[11px] text-muted">average bill</p></div></div>
          ) : (
            <div className="grid grid-cols-3 gap-3 text-center"><div className="rounded-xl bg-sunken p-3"><p className="text-xl font-bold">{detail.stats.delivered_30d}</p><p className="text-[11px] text-muted">deliveries, 30 days</p></div><div className="rounded-xl bg-sunken p-3"><p className="text-xl font-bold">{detail.stats.avg_delivery_minutes ?? "-"}</p><p className="text-[11px] text-muted">avg minutes</p></div><div className="rounded-xl bg-sunken p-3"><p className="text-lg font-bold">{money(detail.stats.to_settle, currency)}</p><p className="text-[11px] text-muted">cash with rider</p></div></div>
          )}
          <dl className="space-y-2 text-sm">
            {([["Phone", detail.phone], ["CNIC", detail.cnic], ["Address", detail.address], ["Emergency contact", detail.emergency_contact], ["Joined", fmtDate(detail.joining_date)], ["Branch", detail.location_name], ...(detail.role === "RIDER" ? [["Vehicle", detail.vehicle], ["Commission / delivery", money(detail.delivery_commission, currency)]] : [])] as [string, string][]).map(([k, v]) => <div key={k} className="flex justify-between gap-4"><dt className="text-muted">{k}</dt><dd className="text-right font-medium">{v || "-"}</dd></div>)}
          </dl>
          <div className="rounded-xl border border-line p-3 text-sm">
            <div className="flex items-center justify-between"><p className="flex items-center gap-2 font-semibold"><Timer className="h-4 w-4 text-brand" />Duty hours</p><Button size="sm" variant="ghost" onClick={() => setScheduleOpen(true)}>{detail.schedule ? "Change" : "Set"}</Button></div>
            <p className="mt-1 text-muted">{detail.schedule ? `${detail.schedule.start_time} – ${detail.schedule.end_time}${detail.schedule.weekly_off.length ? ` · off ${detail.schedule.weekly_off.map((d) => DAYS[d]).join(", ")}` : ""} · late after ${detail.schedule.grace_minutes} min · overtime ×${detail.schedule.overtime_multiplier}` : "Not set: late and overtime are not worked out."}</p>
            <p className="mt-1.5 text-xs text-muted">Today: <b>{detail.today.state.replace("_", " ").toLowerCase()}</b>{detail.today.record?.check_in ? ` · in ${hhmm(detail.today.record.check_in)}${detail.today.record.check_out ? `, out ${hhmm(detail.today.record.check_out)} (${fmtMin(detail.today.record.worked_minutes)})` : ""}` : ""}</p>
            <div className="mt-2 flex items-center justify-between border-t border-line pt-2"><p className="flex items-center gap-2 font-semibold"><KeyRound className="h-4 w-4 text-brand" />Attendance PIN</p><Button size="sm" variant="ghost" onClick={() => setPinOpen(true)}>{detail.has_pin ? "Change" : "Set PIN"}</Button></div>
          </div>
          <div className="flex gap-2 border-t border-line pt-4"><Button variant="secondary" className="flex-1" onClick={() => { const e = detail; setDetail(null); open(e); }}><Pencil className="h-4 w-4" />Edit</Button>{detail.is_active && <Button variant="danger" onClick={() => remove(detail)}><Trash2 className="h-4 w-4" />Remove</Button>}</div>
        </div>}
      </Modal>

      {detail && <ScheduleModal open={scheduleOpen} onClose={() => setScheduleOpen(false)} employeeId={detail.id} name={detail.name} current={detail.schedule} onSaved={() => openDetail(detail)} />}
      {detail && <PinModal open={pinOpen} onClose={() => setPinOpen(false)} employeeId={detail.id} name={detail.name} hasPin={detail.has_pin} onSaved={() => { openDetail(detail); load(); }} />}

      <Modal open={!!settle} onClose={() => setSettle(null)} title={`Take cash from ${settle?.rider.name ?? ""}`} width="max-w-lg">
        {settle && <div className="space-y-4">
          <p className="text-sm text-muted">Tick the deliveries the rider is paying for. The cash is added to <b>your</b> open shift.</p>
          <ul className="max-h-64 space-y-1.5 overflow-y-auto">
            {settle.orders.map((o) => (
              <li key={o.id}><label className="flex cursor-pointer items-center gap-3 rounded-xl border border-line px-3 py-2.5 text-sm hover:bg-sunken">
                <input type="checkbox" checked={picked.includes(o.id)} onChange={(e) => { const next = e.target.checked ? [...picked, o.id] : picked.filter((x) => x !== o.id); setPicked(next); setHanded(String(settle.orders.filter((x) => next.includes(x.id)).reduce((s, x) => s + Number(x.due), 0))); }} className="h-4 w-4 accent-[rgb(var(--brand))]" />
                <span className="flex-1"><b>{o.order_number}</b><span className="block text-xs text-muted">{o.customer_name || "Customer"} · {fmtDateTime(o.delivered_at)}</span></span><b>{money(o.due, currency)}</b></label></li>
            ))}
          </ul>
          <div className="flex items-center justify-between rounded-xl bg-sunken px-4 py-3"><span className="text-sm text-muted">Should receive</span><span className="text-xl font-bold">{money(expected, currency)}</span></div>
          <Input label="Cash actually received" type="number" min="0" step="any" value={handed} onChange={(e) => setHanded(e.target.value)} />
          {short > 0 && <p className="flex items-center gap-2 rounded-xl bg-warn-soft px-3 py-2 text-sm font-semibold text-warn"><Clock className="h-4 w-4" />Short by {money(short, currency)}. It stays due on the oldest orders and is recorded.</p>}
          {short === 0 && Number(handed) > 0 && <p className="flex items-center gap-2 rounded-xl bg-good-soft px-3 py-2 text-sm font-semibold text-good"><CheckCircle2 className="h-4 w-4" />Complete</p>}
          <Button size="lg" className="w-full" loading={busy} disabled={picked.length === 0 || handed === "" || Number(handed) > expected} onClick={doSettle}>Receive {money(Number(handed) || 0, currency)}</Button>
          {settle.settlements.length > 0 && <details className="text-sm"><summary className="cursor-pointer font-semibold text-muted">Recent settlements</summary><ul className="mt-2 space-y-1">{settle.settlements.slice(0, 5).map((s) => <li key={s.id} className="flex justify-between text-xs"><span>{fmtDateTime(s.created_at)} · {s.received_by}</span><span>{money(s.handed, currency)}{Number(s.shortage) > 0 ? ` (short ${money(s.shortage, currency)})` : ""}</span></li>)}</ul></details>}
        </div>}
      </Modal>
    </>
  );
}
