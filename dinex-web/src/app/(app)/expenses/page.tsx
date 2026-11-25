"use client";
import { useCallback, useEffect, useState } from "react";
import { Plus, Receipt, Trash2 } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Segmented, Spinner, Stat, cn, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { downloadCsv } from "@/lib/csv";
import { api, money } from "@/lib/api";
import type { ExpenseT, Paginated } from "@/lib/types";

const CATS = ["Gas", "Electricity", "Rent", "Vegetables", "Meat & dairy", "Repairs", "Cleaning", "Transport", "Other"];
const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
type Range = "today" | "week" | "month";
interface Resp extends Paginated<ExpenseT> { total: string; by_category: { category: string; total: string }[] }

export default function ExpensesPage() {
  const { me, location, currency } = useAuth();
  const { run, busy } = useAction();
  const [range, setRange] = useState<Range>("month");
  const [data, setData] = useState<Resp | null>(null);
  const [open, setOpen] = useState(false);
  const blank = { category: "Gas", custom: "", amount: "", description: "", source: "OTHER" as "OTHER" | "DRAWER" };
  const [f, setF] = useState(blank);

  const load = useCallback(async () => {
    if (!location) return;
    const to = new Date(), from = new Date();
    if (range === "week") from.setDate(from.getDate() - 6); else if (range === "month") from.setDate(from.getDate() - 29);
    setData(await api.get<Resp>("/operations/expenses/", { location: location.id, from: ymd(from), to: ymd(to), page_size: 100 }));
  }, [location, range]);
  useEffect(() => { load().catch(() => {}); }, [load]);

  async function save() {
    const category = f.category === "Other" && f.custom.trim() ? f.custom.trim() : f.category;
    const r = await run(() => api.post("/operations/expenses/", { location: location!.id, category, amount: f.amount, description: f.description, source: f.source }), "Expense saved");
    if (r) { setOpen(false); setF(blank); load(); }
  }
  async function del(e: ExpenseT) { if ((await run(() => api.del(`/operations/expenses/${e.id}/`), "Deleted")) !== undefined) load(); }

  if (me && !me.organization) return <PlatformNotice />;
  const top = data?.by_category ?? [];
  const max = Math.max(1, ...top.map((c) => Number(c.total)));

  return (
    <>
      <PageHeader title="Expenses" subtitle={`${location?.name} · gas, bills, rent and other running costs`} actions={<><Button variant="secondary" disabled={!data?.results.length} data-testid="csv-exp" onClick={() => downloadCsv("expenses.csv", [["Date", "Category", "Note", "Paid from", "Amount"], ...data!.results.map((e) => [e.date, e.category, e.description, e.source === "DRAWER" ? "Cash drawer" : "Outside till", e.amount])])}>Download CSV</Button><Button onClick={() => { setF(blank); setOpen(true); }} data-testid="new-expense"><Plus className="h-4 w-4" />Add expense</Button></>} />
      <div className="mb-4"><Segmented value={range} onChange={setRange} options={[{ value: "today", label: "Today" }, { value: "week", label: "7 days" }, { value: "month", label: "30 days" }]} /></div>
      {!data ? <Spinner /> : (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-4">
            <Stat label="Total spent" value={<span data-testid="exp-total">{money(data.total, currency)}</span>} icon={<Receipt className="h-5 w-5" />} tone="bad" />
            {top.length > 0 && (
              <Card className="p-4"><h3 className="mb-3 text-sm font-bold">By category</h3>
                <div className="space-y-2.5">{top.map((c) => (
                  <div key={c.category}><div className="mb-1 flex justify-between text-sm"><span>{c.category}</span><span className="num font-semibold">{money(c.total, currency)}</span></div>
                    <div className="h-2 rounded-full bg-sunken"><div className="h-2 rounded-full bg-brand" style={{ width: `${(Number(c.total) / max) * 100}%` }} /></div></div>
                ))}</div></Card>
            )}
          </div>
          <div className="lg:col-span-2">
            {data.results.length === 0 ? <EmptyState icon={<Receipt className="h-8 w-8" />} title="No expenses in this period" hint="Record gas, bills and purchases of small items so your day report shows true profit." /> : (
              <Card className="divide-y divide-line">
                {data.results.map((e) => (
                  <div key={e.id} className="flex items-center gap-3 p-3.5" data-testid={`exp-${e.id}`}>
                    <div className="min-w-0 flex-1"><p className="font-semibold">{e.category} {e.source === "DRAWER" && <Badge tone="warn">From till</Badge>}</p>
                      <p className="truncate text-xs text-muted">{new Date(e.date).toLocaleDateString("en-PK", { day: "numeric", month: "short" })}{e.description ? ` · ${e.description}` : ""}</p></div>
                    <p className="num font-bold">{money(e.amount, currency)}</p>
                    {e.source === "OTHER" && <button aria-label="Delete expense" onClick={() => del(e)} className="text-muted hover:text-bad"><Trash2 className="h-4 w-4" /></button>}
                  </div>
                ))}
              </Card>
            )}
          </div>
        </div>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title="Add expense">
        <div className="space-y-4">
          <div><p className="mb-2 text-sm font-medium">Category</p><div className="flex flex-wrap gap-2">{CATS.map((c) => (
            <button key={c} type="button" onClick={() => setF({ ...f, category: c })} data-testid={`cat-${c}`} className={cn("h-9 rounded-full border px-3.5 text-sm font-semibold", f.category === c ? "border-brand bg-brand-soft text-brand" : "border-line text-muted")}>{c}</button>))}</div></div>
          {f.category === "Other" && <Input label="What for?" value={f.custom} onChange={(e) => setF({ ...f, custom: e.target.value })} />}
          <Input label={`Amount (${currency})`} type="number" min={0} inputMode="decimal" data-testid="exp-amount" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} />
          <Input label="Note (optional)" value={f.description} maxLength={200} onChange={(e) => setF({ ...f, description: e.target.value })} />
          <Segmented value={f.source} onChange={(v) => setF({ ...f, source: v })} options={[{ value: "OTHER", label: "Paid outside the till" }, { value: "DRAWER", label: "Taken from cash drawer" }]} />
          {f.source === "DRAWER" && <p className="text-xs text-muted">This is deducted from your open shift&apos;s cash, so the drawer count stays right. You need an open shift.</p>}
          <Button className="w-full" size="lg" loading={busy} disabled={!Number(f.amount)} onClick={save} data-testid="exp-save">Save expense</Button>
        </div>
      </Modal>
    </>
  );
}
