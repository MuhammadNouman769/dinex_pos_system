"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2, Clock, Copy, CreditCard, Receipt, Upload, XCircle } from "lucide-react";
import { StatusBadge, fmtDate, fmtDateTime } from "@/components/Platform";
import { Badge, Button, Card, EmptyState, Input, PageHeader, Select, Spinner, Textarea, cn, useAction, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { InvoiceRow, PaymentAccountT, PaymentSubmissionT, PublicPlan, SubscriptionInfo } from "@/lib/types";

interface Data {
  subscription: SubscriptionInfo | null; usage: { locations: number; users: number }; invoices: InvoiceRow[];
  plans: PublicPlan[]; payment_accounts: PaymentAccountT[]; submissions: PaymentSubmissionT[];
}

function CopyBtn({ text }: { text: string }) {
  const toast = useToast();
  return <button type="button" aria-label="Copy" onClick={() => { navigator.clipboard?.writeText(text).then(() => toast.ok("Copied"), () => toast.err("Could not copy")); }} className="grid h-10 w-10 shrink-0 place-items-center rounded-lg text-muted hover:bg-sunken hover:text-ink"><Copy className="h-4 w-4" /></button>;
}

export default function BillingPage() {
  const { me, reload } = useAuth();
  const { run, busy } = useAction();
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [f, setF] = useState({ method: "", amount: "", reference: "", sender_name: "", sender_number: "", note: "" });
  const [proof, setProof] = useState<File | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => api.get<Data>("/platform/billing/me/").then(setD).catch((e) => setError(e.message)), []);
  useEffect(() => { if (me?.is_owner) load(); }, [me, load]);

  const s = d?.subscription ?? null;
  const pending = d?.submissions.find((x) => x.status === "PENDING");
  const lastRejected = d?.submissions[0]?.status === "REJECTED" ? d.submissions[0] : null;
  const dueAmount = s ? (Number(s.amount_due) > 0 ? s.amount_due : s.price) : "0";
  useEffect(() => { if (d && !f.amount) setF((x) => ({ ...x, amount: String(Number(dueAmount)), method: x.method || d.payment_accounts[0]?.method_label || "JazzCash" })); }, [d]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!me?.is_owner) return <EmptyState title="Billing is for the restaurant owner" />;
  if (error) return <EmptyState title="Could not load billing" hint={error} />;
  if (!d) return <Spinner />;
  if (!s) return <EmptyState icon={<CreditCard className="h-8 w-8" />} title="No subscription" hint="Your account is not on a paid plan yet. Contact XverLabs." />;

  const bar = (used: number, max: number) => <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-sunken"><div className={cn("h-full rounded-full", used >= max ? "bg-bad" : used / max >= 0.8 ? "bg-warn" : "bg-good")} style={{ width: `${Math.min(100, (used / max) * 100)}%` }} /></div>;
  const canPay = !pending && (s.status !== "ACTIVE" || s.invoices_due > 0);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((x) => ({ ...x, [k]: e.target.value }));

  async function pickPlan(code: string) {
    const r = await run(() => api.post("/platform/billing/me/select-plan/", { plan: code }), "Plan updated");
    if (r) { await reload(); setF((x) => ({ ...x, amount: "" })); load(); }
  }

  async function submit() {
    setFieldErrors({});
    const form = new FormData();
    Object.entries(f).forEach(([k, v]) => form.append(k, v));
    if (proof) form.append("proof", proof);
    try {
      await api.upload("/platform/billing/me/payments/", form);
      setProof(null); setF((x) => ({ ...x, reference: "", note: "" }));
      await reload(); load();
      return true;
    } catch (e) {
      const data = (e as { data?: Record<string, unknown> }).data;
      if (data && typeof data === "object") setFieldErrors(Object.fromEntries(Object.entries(data).map(([k, v]) => [k, Array.isArray(v) ? v.join(" ") : String(v)])));
      throw e;
    }
  }

  return (
    <>
      <PageHeader title="Billing" subtitle="Your DineX plan, payments and invoices" />

      {s.blocked && (
        <div className="mb-6 rounded-3xl bg-brand-gradient p-6 text-white shadow-glow dark:text-[#04201a]">
          <h2 className="font-display text-2xl font-extrabold">{s.status === "TRIAL" ? "Your free trial has ended" : "Your subscription needs a payment"}</h2>
          <p className="mt-1 max-w-xl text-sm opacity-90">Your data is safe. Send your subscription payment below and DineX switches back on as soon as we confirm it.</p>
        </div>
      )}
      {pending && (
        <div role="status" className="mb-6 flex items-start gap-3 rounded-2xl border border-warn/40 bg-warn-soft p-4 text-sm text-warn">
          <Clock className="mt-0.5 h-5 w-5 shrink-0" />
          <p><b>We received your payment details</b> (TID {pending.reference}, {money(pending.amount)}). We are checking it. This page updates when it is confirmed.</p>
        </div>
      )}
      {lastRejected && !pending && (
        <div role="alert" className="mb-6 flex items-start gap-3 rounded-2xl border border-bad/40 bg-bad-soft p-4 text-sm text-bad">
          <XCircle className="mt-0.5 h-5 w-5 shrink-0" /><p><b>Your last payment was not accepted:</b> {lastRejected.reject_reason}. Please check and send the details again.</p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="p-6 lg:col-span-2">
          <div className="flex items-start justify-between"><div><p className="text-sm text-muted">Current plan</p><h2 className="font-display text-2xl font-extrabold">{s.plan.name}</h2></div><StatusBadge status={s.status} /></div>
          <p className="num mt-4 text-3xl font-extrabold tracking-tight">{money(s.price)}<span className="text-sm font-medium text-muted"> / month</span></p>
          <dl className="mt-4 space-y-2 text-sm">
            {s.status === "TRIAL" && <div className="flex justify-between"><dt className="text-muted">Trial ends</dt><dd className="font-semibold">{fmtDate(s.trial_ends_at)}{s.days_left !== null ? ` (${s.days_left} day${s.days_left === 1 ? "" : "s"} left)` : ""}</dd></div>}
            {s.current_period_end && <div className="flex justify-between"><dt className="text-muted">Paid until</dt><dd className="font-semibold">{fmtDate(s.current_period_end)}</dd></div>}
            {s.invoices_due > 0 && <div className="flex justify-between"><dt className="text-muted">Amount due</dt><dd className="font-bold text-warn">{money(s.amount_due)}</dd></div>}
          </dl>
        </Card>
        <Card className="p-6">
          <h2 className="mb-4 font-bold">Your usage</h2>
          <div className="space-y-4 text-sm">
            <div><div className="flex justify-between"><span className="text-muted">Branches</span><b>{d.usage.locations} / {s.plan.max_locations}</b></div>{bar(d.usage.locations, s.plan.max_locations)}</div>
            <div><div className="flex justify-between"><span className="text-muted">Staff accounts</span><b>{d.usage.users} / {s.plan.max_users}</b></div>{bar(d.usage.users, s.plan.max_users)}</div>
          </div>
        </Card>
      </div>

      {s.status === "TRIAL" && !pending && (
        <section className="mt-6" aria-labelledby="plans-h">
          <h2 id="plans-h" className="mb-3 font-display text-lg font-extrabold">Choose your plan</h2>
          <div className="grid gap-4 md:grid-cols-3">
            {d.plans.map((p) => { const cur = p.code === s.plan.code; return (
              <Card key={p.code} className={cn("flex flex-col p-5", cur && "border-brand ring-2 ring-brand/30")}>
                <div className="flex items-center justify-between"><h3 className="font-bold">{p.name}</h3>{cur && <Badge tone="brand">Selected</Badge>}</div>
                <p className="num mt-1 text-2xl font-extrabold">{money(p.price_monthly)}<span className="text-xs font-medium text-muted"> / month</span></p>
                <p className="mt-1 text-sm text-muted">{p.max_locations} {p.max_locations === 1 ? "branch" : "branches"} · {p.max_users} staff</p>
                <Button className="mt-4" variant={cur ? "secondary" : "primary"} disabled={cur || busy} onClick={() => pickPlan(p.code)}>{cur ? "Current plan" : `Switch to ${p.name}`}</Button>
              </Card>); })}
          </div>
        </section>
      )}

      {canPay && (
        <section className="mt-6 grid gap-6 lg:grid-cols-2" aria-labelledby="pay-h">
          <Card className="p-6">
            <h2 id="pay-h" className="font-display text-lg font-extrabold">1. Send the payment</h2>
            <p className="mt-1 text-sm text-muted">Send <b className="text-ink">{money(dueAmount)}</b> to any account below, then fill in the details here.</p>
            {d.payment_accounts.length === 0 ? <p className="mt-4 rounded-xl bg-sunken p-4 text-sm text-muted">Payment account details will be shown here. Please contact XverLabs for them.</p> : (
              <ul className="mt-4 space-y-3">
                {d.payment_accounts.map((a) => (
                  <li key={a.id} className="rounded-2xl border border-line bg-sunken/60 p-4">
                    <div className="flex items-center justify-between gap-2"><b>{a.method_label}{a.bank_name ? ` · ${a.bank_name}` : ""}</b><Badge>{a.account_title}</Badge></div>
                    <div className="mt-1 flex items-center justify-between gap-2"><span className="num min-w-0 break-all text-base font-bold tracking-wide sm:text-lg">{a.account_number}</span><CopyBtn text={a.account_number} /></div>
                    {a.instructions && <p className="mt-1 text-xs text-muted">{a.instructions}</p>}
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card className="p-6">
            <h2 className="font-display text-lg font-extrabold">2. Tell us you paid</h2>
            <div className="mt-4 space-y-4">
              <Select label="Paid with" value={f.method} onChange={set("method")}>
                {[...new Set([...d.payment_accounts.map((a) => a.method_label), "JazzCash", "Easypaisa", "Bank transfer", "Other"])].map((m) => <option key={m}>{m}</option>)}
              </Select>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Amount sent (PKR)" type="number" inputMode="decimal" min="1" value={f.amount} onChange={set("amount")} error={fieldErrors.amount} />
                <Input label="Transaction ID (TID)" value={f.reference} onChange={set("reference")} error={fieldErrors.reference} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input label="Sender name" value={f.sender_name} onChange={set("sender_name")} />
                <Input label="Sender number" type="tel" inputMode="tel" value={f.sender_number} onChange={set("sender_number")} />
              </div>
              <Textarea label="Note (optional)" rows={2} value={f.note} onChange={set("note")} />
              <div>
                <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" aria-label="Payment screenshot" onChange={(e) => setProof(e.target.files?.[0] ?? null)} />
                <Button type="button" variant="secondary" onClick={() => fileRef.current?.click()}><Upload className="h-4 w-4" />{proof ? proof.name : "Add screenshot (optional)"}</Button>
                {fieldErrors.proof && <p className="mt-1 text-xs text-bad">{fieldErrors.proof}</p>}
              </div>
              {fieldErrors.detail && <p role="alert" className="rounded-xl bg-bad-soft px-3 py-2 text-sm text-bad">{fieldErrors.detail}</p>}
              <Button size="lg" className="w-full" loading={busy} onClick={() => run(submit, "Payment sent for confirmation")}>Send for confirmation</Button>
            </div>
          </Card>
        </section>
      )}

      {d.submissions.length > 0 && (
        <Card className="mt-6 overflow-hidden">
          <div className="flex items-center gap-2 border-b border-line px-5 py-4"><CreditCard className="h-4 w-4 text-muted" /><h2 className="font-bold">Your payments</h2></div>
          <ul className="divide-y divide-line text-sm">
            {d.submissions.map((x) => (
              <li key={x.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3.5">
                <div><p className="font-semibold">{money(x.amount)} · {x.method}</p><p className="text-xs text-muted">TID {x.reference} · {fmtDateTime(x.created_at)}{x.reject_reason ? ` · ${x.reject_reason}` : ""}</p></div>
                <Badge tone={x.status === "APPROVED" ? "good" : x.status === "REJECTED" ? "bad" : "warn"}>{x.status_label}</Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card className="mt-6 overflow-hidden">
        <div className="flex items-center gap-2 border-b border-line px-5 py-4"><Receipt className="h-4 w-4 text-muted" /><h2 className="font-bold">Invoices</h2></div>
        {d.invoices.length === 0 ? <p className="px-5 py-10 text-center text-sm text-muted">No invoices yet. You are on a free trial.</p> : (
          <ul className="divide-y divide-line text-sm">
            {d.invoices.map((i) => (
              <li key={i.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3.5">
                <div><p className="font-semibold">{i.number}</p><p className="text-xs text-muted">{fmtDate(i.period_start)} → {fmtDate(i.period_end)}</p></div>
                <div className="flex items-center gap-3"><span className="font-semibold">{money(i.amount)}</span>
                  {i.status === "PAID" ? <Badge tone="good"><CheckCircle2 className="h-3 w-3" />Paid {fmtDate(i.paid_at)}</Badge> : i.status === "VOID" ? <Badge>Void</Badge> : <Badge tone={i.overdue ? "bad" : "warn"}>{i.overdue ? "Overdue" : "Due"} {fmtDate(i.due_date)}</Badge>}</div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
