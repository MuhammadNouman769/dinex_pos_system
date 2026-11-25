"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Banknote, CheckCircle2, ImageIcon, Pencil, Plus, Trash2 } from "lucide-react";
import { fmtDateTime } from "@/components/Platform";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Select, Spinner, Switch, Tabs, Textarea, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { PaymentAccountT, PaymentSubmissionT, Paginated } from "@/lib/types";

type Tab = "PENDING" | "APPROVED" | "REJECTED";
const BLANK = { method: "JAZZCASH", account_title: "", account_number: "", bank_name: "", instructions: "", is_active: true };

export default function PaymentsPage() {
  const { me } = useAuth();
  const { run, busy } = useAction();
  const [tab, setTab] = useState<Tab>("PENDING");
  const [rows, setRows] = useState<PaymentSubmissionT[] | null>(null);
  const [accounts, setAccounts] = useState<PaymentAccountT[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [reject, setReject] = useState<PaymentSubmissionT | null>(null);
  const [reason, setReason] = useState("");
  const [edit, setEdit] = useState<(typeof BLANK & { id?: number }) | null>(null);

  const load = useCallback(async () => {
    const [r, a, p] = await Promise.all([
      api.get<Paginated<PaymentSubmissionT>>("/platform/payments/", { status: tab, page_size: 50 }),
      api.get<PaymentAccountT[]>("/platform/payment-accounts/"),
      api.get<Paginated<PaymentSubmissionT>>("/platform/payments/", { status: "PENDING", page_size: 1 }),
    ]);
    setRows(r.results); setAccounts(a); setPendingCount(p.count);
  }, [tab]);
  useEffect(() => { if (me?.role === "PLATFORM") load().catch(() => setRows([])); }, [me, load]);

  if (me && me.role !== "PLATFORM") return <EmptyState title="DineX Admin is for XverLabs staff" />;

  return (
    <>
      <PageHeader title="Payments" subtitle="Check the money arrived, then approve to switch the restaurant on" />
      <Tabs value={tab} onChange={setTab} tabs={[{ value: "PENDING", label: "To check", count: pendingCount }, { value: "APPROVED", label: "Approved" }, { value: "REJECTED", label: "Rejected" }]} className="mb-4" />

      {!rows ? <Spinner /> : rows.length === 0 ? <EmptyState icon={<Banknote className="h-8 w-8" />} title={tab === "PENDING" ? "Nothing to check" : "Nothing here"} hint={tab === "PENDING" ? "New payments from restaurants appear here." : undefined} /> : (
        <div className="space-y-3">
          {rows.map((x) => (
            <Card key={x.id} className="p-4 sm:p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <Link href={`/admin/restaurants/${x.organization}`} className="font-display text-lg font-extrabold hover:text-brand">{x.organization_name}</Link>
                  <p className="text-xs text-muted">{fmtDateTime(x.created_at)} · by {x.submitted_by ?? "-"}</p>
                </div>
                <div className="text-right"><p className="num text-xl font-extrabold">{money(x.amount)}</p>
                  {x.invoice_amount && !x.amount_matches ? <Badge tone="warn">Invoice is {money(x.invoice_amount)}</Badge> : x.invoice_amount ? <Badge tone="good">Matches invoice</Badge> : null}</div>
              </div>
              <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div><dt className="text-xs text-muted">Method</dt><dd className="font-semibold">{x.method}</dd></div>
                <div><dt className="text-xs text-muted">Transaction ID</dt><dd className="num font-semibold">{x.reference}</dd></div>
                <div><dt className="text-xs text-muted">Sender</dt><dd className="font-semibold">{x.sender_name || "-"} {x.sender_number}</dd></div>
                <div><dt className="text-xs text-muted">Invoice</dt><dd className="font-semibold">{x.invoice_number ?? "-"}</dd></div>
              </dl>
              {x.note && <p className="mt-2 text-sm text-muted">Note: {x.note}</p>}
              {x.reject_reason && <p className="mt-2 text-sm text-bad">Rejected: {x.reject_reason}</p>}
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {x.proof && <a href={x.proof} target="_blank" rel="noreferrer" className="inline-flex min-h-[44px] items-center gap-2 rounded-xl border border-line px-3 text-sm font-semibold hover:bg-sunken"><ImageIcon className="h-4 w-4" />Screenshot</a>}
                <div className="flex-1" />
                {x.status === "PENDING" && <>
                  <Button variant="secondary" onClick={() => { setReject(x); setReason(""); }}>Reject</Button>
                  <Button loading={busy} onClick={async () => { if (await run(() => api.post(`/platform/payments/${x.id}/approve/`), `${x.organization_name} is now active`)) load(); }}><CheckCircle2 className="h-4 w-4" />Approve &amp; activate</Button>
                </>}
              </div>
            </Card>
          ))}
        </div>
      )}

      <section className="mt-10" aria-labelledby="acc-h">
        <div className="mb-3 flex items-center justify-between"><div><h2 id="acc-h" className="font-display text-lg font-extrabold">Where restaurants pay you</h2><p className="text-sm text-muted">These accounts are shown to every restaurant on its Billing page.</p></div>
          <Button variant="secondary" onClick={() => setEdit({ ...BLANK })}><Plus className="h-4 w-4" />Add account</Button></div>
        {accounts.length === 0 ? <Card className="p-6 text-center text-sm text-muted">No payment accounts yet. Add your JazzCash, Easypaisa or bank details so restaurants know where to pay.</Card> : (
          <div className="grid gap-3 md:grid-cols-2">
            {accounts.map((a) => (
              <Card key={a.id} className="flex items-center justify-between gap-3 p-4">
                <div className="min-w-0"><p className="font-bold">{a.method_label}{a.bank_name ? ` · ${a.bank_name}` : ""} {!a.is_active && <Badge>Hidden</Badge>}</p><p className="num truncate text-sm">{a.account_number} · {a.account_title}</p></div>
                <div className="flex gap-1">
                  <button aria-label="Edit" onClick={() => setEdit({ ...a })} className="grid h-11 w-11 place-items-center rounded-xl hover:bg-sunken"><Pencil className="h-4 w-4" /></button>
                  <button aria-label="Delete" onClick={async () => { if (confirm("Delete this account?") && await run(() => api.del(`/platform/payment-accounts/${a.id}/`), "Deleted")) load(); }} className="grid h-11 w-11 place-items-center rounded-xl text-bad hover:bg-bad-soft"><Trash2 className="h-4 w-4" /></button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <Modal open={!!reject} onClose={() => setReject(null)} title="Reject payment" width="max-w-sm"><div className="space-y-4">
        <p className="text-sm text-muted">{reject?.organization_name} · {money(reject?.amount ?? 0)} · TID {reject?.reference}</p>
        <Textarea label="Reason (the restaurant will see this)" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        <Button className="w-full" loading={busy} disabled={reason.trim().length < 3} onClick={async () => { if (await run(() => api.post(`/platform/payments/${reject!.id}/reject/`, { reason }), "Rejected")) { setReject(null); load(); } }}>Reject payment</Button></div></Modal>

      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? "Edit account" : "Add payment account"} width="max-w-md"><div className="space-y-4">
        <Select label="Type" value={edit?.method} onChange={(e) => setEdit((x) => x && { ...x, method: e.target.value })}><option value="JAZZCASH">JazzCash</option><option value="EASYPAISA">Easypaisa</option><option value="BANK">Bank transfer</option><option value="OTHER">Other</option></Select>
        <Input label="Account title (name)" value={edit?.account_title ?? ""} onChange={(e) => setEdit((x) => x && { ...x, account_title: e.target.value })} />
        <Input label="Number / IBAN" value={edit?.account_number ?? ""} onChange={(e) => setEdit((x) => x && { ...x, account_number: e.target.value })} />
        {edit?.method === "BANK" && <Input label="Bank name" value={edit.bank_name} onChange={(e) => setEdit((x) => x && { ...x, bank_name: e.target.value })} />}
        <Input label="Instructions (optional)" value={edit?.instructions ?? ""} onChange={(e) => setEdit((x) => x && { ...x, instructions: e.target.value })} />
        <Switch checked={!!edit?.is_active} onChange={(v) => setEdit((x) => x && { ...x, is_active: v })} label="Show to restaurants" />
        <Button className="w-full" loading={busy} onClick={async () => { const e = edit!; const r = await run(() => e.id ? api.patch(`/platform/payment-accounts/${e.id}/`, e) : api.post("/platform/payment-accounts/", e), "Saved"); if (r) { setEdit(null); load(); } }}>Save</Button></div></Modal>
    </>
  );
}
