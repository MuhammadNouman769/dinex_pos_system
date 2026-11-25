"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { FileText, Search } from "lucide-react";
import { fmtDate } from "@/components/Platform";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Select, Spinner, cn, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { InvoiceRow, Paginated } from "@/lib/types";

const FILTERS = [["", "All"], ["DUE", "Due"], ["OVERDUE", "Overdue"], ["PAID", "Paid"], ["VOID", "Void"]] as const;

export default function InvoicesPage() {
  const { me } = useAuth();
  const { run, busy } = useAction();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [rows, setRows] = useState<InvoiceRow[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [pay, setPay] = useState<InvoiceRow | null>(null);
  const [method, setMethod] = useState("Bank transfer");
  const [ref, setRef] = useState("");

  const load = useCallback(async () => {
    const r = await api.get<Paginated<InvoiceRow>>("/platform/invoices/", { status, search, page_size: 50 });
    setRows(r.results); setCount(r.count); setLoading(false);
  }, [status, search]);
  useEffect(() => { if (me?.role !== "PLATFORM") return; const t = setTimeout(() => load().catch(() => setLoading(false)), 250); return () => clearTimeout(t); }, [load, me]);

  if (me && me.role !== "PLATFORM") return <EmptyState title="DineX Admin is for XverLabs staff" />;
  const total = rows.reduce((s, r) => s + Number(r.amount), 0);

  return (
    <>
      <PageHeader title="Invoices" subtitle={`${count} invoice${count === 1 ? "" : "s"} · ${money(total)} shown`} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] flex-1 sm:max-w-sm"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input aria-label="Search" placeholder="Invoice no. or restaurant…" className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} /></div>
        <div className="flex flex-wrap gap-2">{FILTERS.map(([id, label]) => <button key={id} onClick={() => setStatus(id)} className={cn("rounded-full border px-3.5 py-1.5 text-sm font-semibold transition", status === id ? "border-brand bg-brand text-white" : "border-line bg-surface text-muted hover:text-ink")}>{label}</button>)}</div>
      </div>

      {loading ? <Spinner /> : rows.length === 0 ? <EmptyState icon={<FileText className="h-8 w-8" />} title="No invoices" hint="Invoices appear when a restaurant starts billing." /> : (
        <Card className="overflow-hidden"><div className="overflow-x-auto"><table className="w-full text-sm">
          <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Invoice</th><th className="px-5 py-3">Restaurant</th><th className="px-5 py-3">Period</th><th className="px-5 py-3 text-right">Amount</th><th className="px-5 py-3">Due</th><th className="px-5 py-3">Status</th><th className="px-5 py-3" /></tr></thead>
          <tbody className="divide-y divide-line">
            {rows.map((i) => (
              <tr key={i.id}>
                <td className="px-5 py-3 font-semibold">{i.number}</td>
                <td className="px-5 py-3"><Link href={`/admin/restaurants/${i.organization}`} className="hover:text-brand">{i.organization_name}</Link></td>
                <td className="px-5 py-3 text-muted">{fmtDate(i.period_start)} → {fmtDate(i.period_end)}</td>
                <td className="px-5 py-3 text-right font-semibold">{money(i.amount)}</td>
                <td className="px-5 py-3 text-muted">{fmtDate(i.due_date)}</td>
                <td className="px-5 py-3"><Badge tone={i.status === "PAID" ? "good" : i.status === "VOID" ? "neutral" : i.overdue ? "bad" : "warn"}>{i.status === "DUE" ? (i.overdue ? "Overdue" : "Due") : i.status === "PAID" ? `Paid ${fmtDate(i.paid_at)}` : "Void"}</Badge></td>
                <td className="px-5 py-3 text-right">{i.status === "DUE" && <Button size="sm" onClick={() => { setPay(i); setRef(""); }}>Mark paid</Button>}</td>
              </tr>
            ))}
          </tbody></table></div></Card>
      )}

      <Modal open={!!pay} onClose={() => setPay(null)} title={`Mark ${pay?.number} paid`} width="max-w-sm"><div className="space-y-4">
        <p className="text-sm text-muted">{pay?.organization_name} · {money(pay?.amount ?? 0)}</p>
        <Select label="How was it paid?" value={method} onChange={(e) => setMethod(e.target.value)}>{["Bank transfer", "JazzCash", "Easypaisa", "Cash", "Cheque", "Card"].map((m) => <option key={m}>{m}</option>)}</Select>
        <Input label="Reference (optional)" value={ref} onChange={(e) => setRef(e.target.value)} />
        <Button className="w-full" loading={busy} onClick={async () => { const r = await run(() => api.post(`/platform/invoices/${pay!.id}/pay/`, { method, reference: ref }), "Payment recorded"); if (r) { setPay(null); load(); } }}>Record payment</Button></div></Modal>
    </>
  );
}
