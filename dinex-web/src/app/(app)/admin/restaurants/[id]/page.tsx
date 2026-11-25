"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Ban, CalendarPlus, CheckCircle2, KeyRound, Pause, Play, Rocket, Tag } from "lucide-react";
import { StatusBadge, fmtDate, fmtDateTime, genPassword } from "@/components/Platform";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Select, Spinner, cn, useAction, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { InvoiceRow, PlanRow, RestaurantDetail } from "@/lib/types";

type Dialog = null | "plan" | "trial" | "suspend" | "price" | "password" | "invoice" | "cancel" | "pay";
const ACTION_LABEL: Record<string, string> = {
  platform_restaurant_created: "Restaurant created", platform_activated: "Billing started", platform_plan_changed: "Plan changed", platform_trial_extended: "Trial extended",
  platform_suspended: "Suspended", platform_auto_suspended: "Auto-suspended (unpaid)", platform_reactivated: "Reactivated", platform_cancelled: "Cancelled",
  platform_price_set: "Custom price set", platform_invoice_created: "Invoice created", platform_invoice_paid: "Invoice paid", platform_invoice_voided: "Invoice voided",
  platform_owner_password_reset: "Owner password reset", platform_account_disabled: "Account disabled", platform_account_enabled: "Account enabled",
};

export default function RestaurantDetailPage() {
  const { me } = useAuth();
  const { id } = useParams<{ id: string }>();
  const toast = useToast();
  const { run, busy } = useAction();
  const [d, setD] = useState<RestaurantDetail | null>(null);
  const [plans, setPlans] = useState<PlanRow[]>([]);
  const [error, setError] = useState("");
  const [dialog, setDialog] = useState<Dialog>(null);
  const [form, setForm] = useState({ plan: "", days: "14", reason: "", price: "", password: genPassword(), amount: "", note: "", method: "Bank transfer", reference: "" });
  const [payInv, setPayInv] = useState<InvoiceRow | null>(null);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((s) => ({ ...s, [k]: e.target.value }));

  const load = useCallback(async () => {
    try { setD(await api.get<RestaurantDetail>(`/platform/restaurants/${id}/`)); } catch (e) { setError(e instanceof Error ? e.message : "Not found"); }
  }, [id]);
  useEffect(() => { if (me?.role === "PLATFORM") { load(); api.get<PlanRow[]>("/platform/plans/").then(setPlans); } }, [me, load]);

  const act = async (action: string, extra: Record<string, unknown> = {}, ok = "Done") => {
    const r = await run(() => api.post(`/platform/restaurants/${id}/subscription/`, { action, ...extra }), ok);
    if (r) { setDialog(null); load(); }
  };

  if (me && me.role !== "PLATFORM") return <EmptyState title="DineX Admin is for XverLabs staff" />;
  if (error) return <EmptyState title="Restaurant not found" hint={error} action={<Link href="/admin/restaurants"><Button>Back to restaurants</Button></Link>} />;
  if (!d) return <Spinner />;

  const sub = d.subscription, st = sub?.status;
  const plan = plans.find((p) => p.code === sub?.plan);
  const info = d.status_info;
  const limitBar = (used: number, max: number | undefined) => {
    const pct = max ? Math.min(100, (used / max) * 100) : 0;
    return <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-sunken"><div className={cn("h-full rounded-full", pct >= 100 ? "bg-bad" : pct >= 80 ? "bg-warn" : "bg-good")} style={{ width: `${pct}%` }} /></div>;
  };

  return (
    <>
      <Link href="/admin/restaurants" className="mb-3 inline-flex items-center gap-1 text-sm font-semibold text-muted hover:text-ink"><ArrowLeft className="h-4 w-4" />Restaurants</Link>
      <PageHeader title={d.name} subtitle={`${d.owner?.name} · ${d.owner?.email} · joined ${fmtDate(d.created_at)}`}
        actions={<div className="flex items-center gap-2">{!d.is_active && <Badge tone="bad">Account disabled</Badge>}<StatusBadge status={st} /></div>} />

      {info?.message && <div className={cn("mb-5 rounded-2xl px-4 py-3 text-sm font-medium", info.blocked ? "bg-bad-soft text-bad" : "bg-warn-soft text-warn")}>{info.message}{sub?.suspended_reason ? ` (${sub.suspended_reason})` : ""}</div>}

      <Card className="mb-6 p-4">
        <div className="flex flex-wrap gap-2">
          {st === "TRIAL" && <Button onClick={() => act("activate", {}, "Billing started. First invoice issued.")} loading={busy}><Rocket className="h-4 w-4" />Start billing</Button>}
          {(st === "TRIAL" || st === "SUSPENDED" || st === "CANCELLED") && <Button variant="secondary" onClick={() => setDialog("trial")}><CalendarPlus className="h-4 w-4" />Extend trial</Button>}
          {(st === "SUSPENDED" || st === "CANCELLED" || st === "PAST_DUE") && <Button variant="secondary" onClick={() => act("reactivate", {}, "Reactivated")}><Play className="h-4 w-4" />Reactivate</Button>}
          {st !== "SUSPENDED" && st !== "CANCELLED" && <Button variant="secondary" onClick={() => { setForm((s) => ({ ...s, reason: "" })); setDialog("suspend"); }}><Pause className="h-4 w-4" />Suspend</Button>}
          <Button variant="secondary" onClick={() => { setForm((s) => ({ ...s, plan: sub?.plan ?? "" })); setDialog("plan"); }}>Change plan</Button>
          <Button variant="secondary" onClick={() => { setForm((s) => ({ ...s, price: d.subscription_detail?.price_override ?? "" })); setDialog("price"); }}><Tag className="h-4 w-4" />Custom price</Button>
          <Button variant="secondary" onClick={() => { setForm((s) => ({ ...s, password: genPassword() })); setDialog("password"); }}><KeyRound className="h-4 w-4" />Reset owner password</Button>
          <Button variant="secondary" onClick={() => { setForm((s) => ({ ...s, amount: "", note: "" })); setDialog("invoice"); }}>New invoice</Button>
          {st !== "CANCELLED" && <Button variant="danger" onClick={() => setDialog("cancel")}><Ban className="h-4 w-4" />Cancel</Button>}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="p-5">
          <h2 className="mb-3 font-bold">Subscription</h2>
          <dl className="space-y-2.5 text-sm">
            <Row k="Plan" v={sub?.plan_name ?? "-"} />
            <Row k="Price / month" v={<>{money(sub?.price ?? 0)}{d.subscription_detail?.price_override != null && <Badge tone="brand" className="ml-2">custom</Badge>}</>} />
            {st === "TRIAL" && <Row k="Trial ends" v={fmtDateTime(sub?.trial_ends_at)} />}
            {sub?.current_period_end && <Row k="Paid until" v={fmtDate(sub.current_period_end)} />}
            <Row k="Invoices due" v={String(d.invoices_due)} />
          </dl>
        </Card>
        <Card className="p-5">
          <h2 className="mb-3 font-bold">Usage vs plan</h2>
          <div className="space-y-4 text-sm">
            <div><div className="flex justify-between"><span className="text-muted">Branches</span><b>{d.usage.locations} / {plan?.max_locations ?? "-"}</b></div>{limitBar(d.usage.locations, plan?.max_locations)}</div>
            <div><div className="flex justify-between"><span className="text-muted">Staff accounts</span><b>{d.usage.users} / {plan?.max_users ?? "-"}</b></div>{limitBar(d.usage.users, plan?.max_users)}</div>
            <div className="flex justify-between border-t border-line pt-3"><span className="text-muted">Orders, last 30 days</span><b>{d.usage.orders_30d.toLocaleString()}</b></div>
            <div className="flex justify-between"><span className="text-muted">Sales, last 30 days</span><b>{money(d.usage.sales_30d)}</b></div>
          </div>
        </Card>
        <Card className="p-5">
          <h2 className="mb-3 font-bold">Branches</h2>
          <ul className="space-y-2.5 text-sm">{d.locations.map((l) => <li key={l.id}><p className="font-semibold">{l.name}</p><p className="text-xs text-muted">{l.address}</p></li>)}</ul>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4"><h2 className="font-bold">Invoices</h2></div>
          <ul className="divide-y divide-line text-sm">
            {d.invoices.map((i) => (
              <li key={i.id} className="flex items-center justify-between gap-3 px-5 py-3">
                <div><p className="font-semibold">{i.number} · {money(i.amount)}</p><p className="text-xs text-muted">{fmtDate(i.period_start)} → {fmtDate(i.period_end)} · {i.status === "PAID" ? `paid ${fmtDate(i.paid_at)}${i.method ? ` (${i.method})` : ""}` : `due ${fmtDate(i.due_date)}`}</p></div>
                <div className="flex items-center gap-2">
                  <Badge tone={i.status === "PAID" ? "good" : i.status === "VOID" ? "neutral" : i.overdue ? "bad" : "warn"}>{i.status === "DUE" && i.overdue ? "Overdue" : i.status === "DUE" ? "Due" : i.status === "PAID" ? "Paid" : "Void"}</Badge>
                  {i.status === "DUE" && <Button size="sm" onClick={() => { setPayInv(i); setForm((s) => ({ ...s, method: "Bank transfer", reference: "" })); setDialog("pay"); }}>Mark paid</Button>}
                </div>
              </li>
            ))}
            {d.invoices.length === 0 && <li className="px-5 py-8 text-center text-muted">No invoices yet.</li>}
          </ul>
        </Card>
        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4"><h2 className="font-bold">People</h2></div>
          <table className="w-full text-sm"><tbody className="divide-y divide-line">
            {d.users.map((u) => <tr key={u.id}><td className="px-5 py-3"><p className="font-semibold">{u.name || u.username}</p><p className="text-xs text-muted">{u.username} · {u.email}</p></td><td className="px-5 py-3"><Badge tone={u.role === "OWNER" ? "brand" : "neutral"}>{u.role === "OWNER" ? "Owner" : "Staff"}</Badge>{!u.is_active && <Badge tone="bad" className="ml-1">off</Badge>}</td><td className="px-5 py-3 text-right text-xs text-muted">{u.last_login ? `seen ${fmtDate(u.last_login)}` : "never signed in"}</td></tr>)}
          </tbody></table>
        </Card>
      </div>

      <Card className="mt-6 overflow-hidden">
        <div className="border-b border-line px-5 py-4"><h2 className="font-bold">Admin activity</h2></div>
        <ul className="divide-y divide-line text-sm">
          {d.activity.map((a, i) => <li key={i} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3"><span><b>{ACTION_LABEL[a.action] ?? a.action}</b><span className="text-muted"> · {a.user ?? "system"}{a.details.reason ? ` · “${String(a.details.reason)}”` : ""}{a.details.new ? ` · ${String(a.details.old)} → ${String(a.details.new)}` : ""}{a.details.invoice ? ` · ${String(a.details.invoice)}` : ""}</span></span><span className="text-xs text-muted">{fmtDateTime(a.created_at)}</span></li>)}
          {d.activity.length === 0 && <li className="px-5 py-8 text-center text-muted">Nothing yet.</li>}
        </ul>
      </Card>

      {/* dialogs */}
      <Modal open={dialog === "plan"} onClose={() => setDialog(null)} title="Change plan" width="max-w-sm"><div className="space-y-4">
        <Select label="Plan" value={form.plan} onChange={set("plan")}>{plans.filter((p) => p.is_active).map((p) => <option key={p.code} value={p.code}>{p.name} · Rs {Number(p.price_monthly).toLocaleString()} · {p.max_locations} branch / {p.max_users} users</option>)}</Select>
        <p className="text-xs text-muted">A plan cannot be lowered below what the restaurant already uses ({d.usage.locations} branches, {d.usage.users} users).</p>
        <Button className="w-full" loading={busy} onClick={() => act("change_plan", { plan: form.plan }, "Plan changed")}>Save</Button></div></Modal>
      <Modal open={dialog === "trial"} onClose={() => setDialog(null)} title="Extend trial" width="max-w-sm"><div className="space-y-4">
        <Input label="Days to add" type="number" min="1" max="90" value={form.days} onChange={set("days")} />
        <Button className="w-full" loading={busy} onClick={() => act("extend_trial", { days: Number(form.days) }, "Trial extended")}>Extend</Button></div></Modal>
      <Modal open={dialog === "suspend"} onClose={() => setDialog(null)} title="Suspend restaurant" width="max-w-sm"><div className="space-y-4">
        <p className="text-sm text-muted">They can still sign in and see their data, but cannot take orders or change anything until you reactivate.</p>
        <Input label="Reason (shown to the restaurant)" value={form.reason} onChange={set("reason")} placeholder="e.g. Invoice unpaid" />
        <Button variant="danger" className="w-full" loading={busy} disabled={form.reason.trim().length < 3} onClick={() => act("suspend", { reason: form.reason }, "Suspended")}>Suspend</Button></div></Modal>
      <Modal open={dialog === "cancel"} onClose={() => setDialog(null)} title="Cancel subscription" width="max-w-sm"><div className="space-y-4">
        <p className="text-sm text-muted">The restaurant becomes read-only. Their data is kept. You can reactivate any time.</p>
        <Input label="Reason (optional)" value={form.reason} onChange={set("reason")} />
        <Button variant="danger" className="w-full" loading={busy} onClick={() => act("cancel", { reason: form.reason }, "Cancelled")}>Cancel subscription</Button></div></Modal>
      <Modal open={dialog === "price"} onClose={() => setDialog(null)} title="Custom price" width="max-w-sm"><div className="space-y-4">
        <Input label="Price per month (PKR)" type="number" min="0" value={form.price} onChange={set("price")} hint={`Plan price is ${money(d.subscription_detail?.plan_price ?? 0)}. Leave empty to use it.`} />
        <Button className="w-full" loading={busy} onClick={() => act("set_price", { price: form.price }, "Price saved")}>Save</Button></div></Modal>
      <Modal open={dialog === "password"} onClose={() => setDialog(null)} title="Reset owner password" width="max-w-sm"><div className="space-y-4">
        <Input label={`New password for ${d.owner?.username}`} value={form.password} onChange={set("password")} className="font-mono" />
        <Button className="w-full" loading={busy} onClick={async () => { const r = await run(() => api.post(`/platform/restaurants/${id}/reset-password/`, { password: form.password })); if (r) { setDialog(null); toast.ok(`Password changed. Tell the owner: ${form.password}`); } }}>Set password</Button></div></Modal>
      <Modal open={dialog === "invoice"} onClose={() => setDialog(null)} title="New invoice" width="max-w-sm"><div className="space-y-4">
        <Input label="Amount (PKR)" type="number" min="1" value={form.amount} onChange={set("amount")} hint={`Leave empty for the monthly price (${money(sub?.price ?? 0)}).`} />
        <Input label="Note" value={form.note} onChange={set("note")} placeholder="e.g. Setup fee" />
        <Button className="w-full" loading={busy} onClick={async () => { const r = await run(() => api.post(`/platform/restaurants/${id}/invoices/`, { amount: form.amount || null, note: form.note }), "Invoice created"); if (r) { setDialog(null); load(); } }}>Create invoice</Button></div></Modal>
      <Modal open={dialog === "pay"} onClose={() => setDialog(null)} title={`Mark ${payInv?.number} paid`} width="max-w-sm"><div className="space-y-4">
        <p className="flex items-center gap-2 text-sm text-muted"><CheckCircle2 className="h-4 w-4 text-good" />{money(payInv?.amount ?? 0)} received. A suspended or overdue restaurant is reactivated automatically once nothing overdue remains.</p>
        <Select label="How was it paid?" value={form.method} onChange={set("method")}>{["Bank transfer", "JazzCash", "Easypaisa", "Cash", "Cheque", "Card"].map((m) => <option key={m}>{m}</option>)}</Select>
        <Input label="Reference (optional)" value={form.reference} onChange={set("reference")} placeholder="Transaction id / slip no." />
        <Button className="w-full" loading={busy} onClick={async () => { const r = await run(() => api.post(`/platform/invoices/${payInv!.id}/pay/`, { method: form.method, reference: form.reference }), "Payment recorded"); if (r) { setDialog(null); load(); } }}>Record payment</Button></div></Modal>
    </>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return <div className="flex items-center justify-between"><dt className="text-muted">{k}</dt><dd className="font-semibold">{v}</dd></div>;
}
