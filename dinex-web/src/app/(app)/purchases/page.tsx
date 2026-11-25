"use client";
import { useCallback, useEffect, useState } from "react";
import { PackagePlus, Plus, Truck, X } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Select, Spinner, Tabs, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { PurchaseT, Supplier } from "@/lib/types";

interface Ing { id: number; name: string; base_unit: "G" | "ML" | "PCS" }
const UNITS: Record<Ing["base_unit"], string[]> = { G: ["kg", "g"], ML: ["l", "ml"], PCS: ["pcs", "dozen"] };
type Tab = "purchases" | "suppliers";
const blankLine = { ingredient: "", quantity: "", unit: "", unit_cost: "" };

export default function PurchasesPage() {
  const { me, location, currency } = useAuth();
  const { run, busy } = useAction();
  const [tab, setTab] = useState<Tab>("purchases");
  const [purchases, setPurchases] = useState<PurchaseT[] | null>(null);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [ings, setIngs] = useState<Ing[]>([]);
  const [buy, setBuy] = useState(false);
  const [sup, setSup] = useState(false);
  const [payFor, setPayFor] = useState<PurchaseT | null>(null);
  const [payAmt, setPayAmt] = useState("");
  const [form, setForm] = useState({ supplier: "", invoice: "", paid: "", lines: [{ ...blankLine }] });
  const [sf, setSf] = useState({ name: "", phone: "", address: "" });

  const load = useCallback(async () => {
    if (!location) return;
    const [p, s, i] = await Promise.all([api.list<PurchaseT>("/operations/purchases/", { location: location.id }), api.list<Supplier>("/operations/suppliers/"), api.list<Ing>("/inventory/ingredients/")]);
    setPurchases(p); setSuppliers(s); setIngs(i.filter((x) => !(x as unknown as { is_prepared?: boolean }).is_prepared));
  }, [location]);
  useEffect(() => { load().catch(() => setPurchases([])); }, [load]);

  const total = form.lines.reduce((a, l) => a + (Number(l.quantity) || 0) * (Number(l.unit_cost) || 0), 0);
  const setLine = (i: number, patch: Partial<typeof blankLine>) => setForm((f) => ({ ...f, lines: f.lines.map((l, j) => (j === i ? { ...l, ...patch } : l)) }));
  const ready = form.lines.every((l) => l.ingredient && Number(l.quantity) > 0 && l.unit_cost !== "") && Number(form.paid || 0) <= total;

  async function save() {
    const r = await run(() => api.post("/operations/purchases/", {
      location: location!.id, supplier: form.supplier ? Number(form.supplier) : null, invoice_no: form.invoice, paid: form.paid || "0",
      lines: form.lines.map((l) => ({ ingredient: Number(l.ingredient), quantity: l.quantity, unit: l.unit, unit_cost: l.unit_cost })),
    }), "Stock received");
    if (r) { setBuy(false); setForm({ supplier: "", invoice: "", paid: "", lines: [{ ...blankLine }] }); load(); }
  }
  async function addSupplier() {
    const r = await run(() => api.post<Supplier>("/operations/suppliers/", sf), "Supplier added");
    if (r) { setSup(false); setSf({ name: "", phone: "", address: "" }); load(); }
  }
  async function pay() {
    if (!payFor) return;
    const r = await run(() => api.post(`/operations/purchases/${payFor.id}/pay/`, { amount: payAmt }), "Payment recorded");
    if (r) { setPayFor(null); load(); }
  }

  if (me && !me.organization) return <PlatformNotice />;
  const owed = suppliers.reduce((a, s) => a + Number(s.balance), 0);

  return (
    <>
      <PageHeader title="Purchases" subtitle={`${location?.name} · receive stock from suppliers`} actions={<Button onClick={() => setBuy(true)} data-testid="new-purchase"><PackagePlus className="h-4 w-4" />Receive stock</Button>} />
      <Tabs value={tab} onChange={setTab} tabs={[{ value: "purchases", label: "Purchases" }, { value: "suppliers", label: <>Suppliers{owed > 0 && <span className="ml-1.5 text-warn">· owe {money(owed, currency)}</span>}</> }]} className="mb-4" />
      {purchases === null ? <Spinner /> : tab === "purchases" ? (
        purchases.length === 0 ? <EmptyState icon={<Truck className="h-8 w-8" />} title="No purchases yet" hint="When a delivery arrives, record it here. Stock goes up and the ingredient cost updates." action={<Button onClick={() => setBuy(true)}>Receive stock</Button>} /> : (
          <div className="grid gap-3 md:grid-cols-2">
            {purchases.map((p) => (
              <Card key={p.id} className="p-4"><div data-testid={`pur-${p.id}`}>
                <div className="flex items-start justify-between gap-2"><div><p className="font-bold">{p.supplier_name || "No supplier"}</p>
                  <p className="text-xs text-muted">{new Date(p.date).toLocaleDateString("en-PK", { day: "numeric", month: "short" })}{p.invoice_no ? ` · ${p.invoice_no}` : ""}</p></div>
                  <p className="num text-lg font-extrabold">{money(p.total, currency)}</p></div>
                <p className="mt-2 text-sm text-muted">{p.lines.map((l) => `${Number(l.quantity)} ${l.unit} ${l.name}`).join(" · ")}</p>
                <div className="mt-3 flex items-center justify-between">
                  {Number(p.due) > 0 ? <Badge tone="warn">Due {money(p.due, currency)}</Badge> : <Badge tone="good">Paid</Badge>}
                  {Number(p.due) > 0 && <Button size="sm" variant="secondary" data-testid="pur-pay" onClick={() => { setPayFor(p); setPayAmt(String(Number(p.due))); }}>Pay</Button>}
                </div></div></Card>
            ))}
          </div>
        )
      ) : (
        <>
          <div className="mb-3"><Button variant="secondary" onClick={() => setSup(true)} data-testid="new-supplier"><Plus className="h-4 w-4" />Add supplier</Button></div>
          {suppliers.length === 0 ? <EmptyState icon={<Truck className="h-8 w-8" />} title="No suppliers yet" hint="Add the people you buy from, so you can see what you owe each one." /> : (
            <Card className="divide-y divide-line">{suppliers.map((s) => (
              <div key={s.id} className="flex items-center justify-between gap-3 p-3.5" data-testid={`sup-${s.id}`}><div><p className="font-semibold">{s.name}</p><p className="text-xs text-muted">{s.phone || "No phone"}{s.address ? ` · ${s.address}` : ""}</p></div>
                {Number(s.balance) > 0 ? <Badge tone="warn">Owe {money(s.balance, currency)}</Badge> : <Badge tone="good">Settled</Badge>}</div>
            ))}</Card>
          )}
        </>
      )}

      <Modal open={buy} onClose={() => setBuy(false)} title="Receive stock" width="max-w-xl">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Select label="Supplier" value={form.supplier} data-testid="pur-supplier" onChange={(e) => setForm({ ...form, supplier: e.target.value })}><option value="">No supplier / market</option>{suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</Select>
            <Input label="Invoice no." value={form.invoice} onChange={(e) => setForm({ ...form, invoice: e.target.value })} /></div>
          <div className="space-y-2.5">{form.lines.map((l, i) => {
            const ing = ings.find((x) => x.id === Number(l.ingredient));
            const units = ing ? UNITS[ing.base_unit] : [];
            return (
              <div key={i} className="rounded-xl border border-line p-2.5" data-testid={`line-${i}`}>
                <div className="flex items-center gap-2">
                  <div className="flex-1"><Select aria-label="Ingredient" data-testid={`line-ing-${i}`} value={l.ingredient} onChange={(e) => { const g = ings.find((x) => x.id === Number(e.target.value)); setLine(i, { ingredient: e.target.value, unit: g ? UNITS[g.base_unit][0] : "" }); }}><option value="">Choose ingredient…</option>{ings.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</Select></div>
                  {form.lines.length > 1 && <button aria-label="Remove line" onClick={() => setForm({ ...form, lines: form.lines.filter((_, j) => j !== i) })} className="text-muted hover:text-bad"><X className="h-4 w-4" /></button>}
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2">
                  <Input aria-label="Quantity" placeholder="Qty" type="number" min={0} data-testid={`line-qty-${i}`} value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} />
                  <Select aria-label="Unit" value={l.unit} onChange={(e) => setLine(i, { unit: e.target.value })}>{units.map((u) => <option key={u}>{u}</option>)}</Select>
                  <Input aria-label="Price per unit" placeholder={`Price / ${l.unit || "unit"}`} type="number" min={0} data-testid={`line-cost-${i}`} value={l.unit_cost} onChange={(e) => setLine(i, { unit_cost: e.target.value })} />
                </div>
              </div>);
          })}
            <button type="button" className="text-sm font-semibold text-brand" onClick={() => setForm({ ...form, lines: [...form.lines, { ...blankLine }] })} data-testid="add-line"><Plus className="mr-1 inline h-3.5 w-3.5" />Add another item</button></div>
          <div className="flex items-center justify-between rounded-xl bg-sunken px-4 py-3"><span className="text-sm font-medium">Bill total</span><span className="num text-lg font-extrabold" data-testid="pur-total">{money(total, currency)}</span></div>
          <Input label="Paid now" hint="Leave empty if you will pay later" type="number" min={0} data-testid="pur-paid" value={form.paid} onChange={(e) => setForm({ ...form, paid: e.target.value })} />
          <Button className="w-full" size="lg" loading={busy} disabled={!ready} onClick={save} data-testid="pur-save">Receive into stock</Button>
        </div>
      </Modal>
      <Modal open={sup} onClose={() => setSup(false)} title="Add supplier">
        <div className="space-y-3"><Input label="Name" data-testid="sup-name" value={sf.name} onChange={(e) => setSf({ ...sf, name: e.target.value })} /><Input label="Phone" inputMode="tel" value={sf.phone} onChange={(e) => setSf({ ...sf, phone: e.target.value })} />
          <Input label="Address" value={sf.address} onChange={(e) => setSf({ ...sf, address: e.target.value })} /><Button className="w-full" loading={busy} disabled={!sf.name.trim()} onClick={addSupplier} data-testid="sup-save">Save supplier</Button></div>
      </Modal>
      <Modal open={!!payFor} onClose={() => setPayFor(null)} title={`Pay ${payFor?.supplier_name || "supplier"}`}>
        <div className="space-y-3"><p className="text-sm text-muted">Still due: <b>{money(payFor?.due, currency)}</b></p>
          <Input label="Amount" type="number" min={0} data-testid="pay-amount" value={payAmt} onChange={(e) => setPayAmt(e.target.value)} />
          <Button className="w-full" loading={busy} disabled={!Number(payAmt)} onClick={pay} data-testid="pay-save">Record payment</Button></div>
      </Modal>
    </>
  );
}
