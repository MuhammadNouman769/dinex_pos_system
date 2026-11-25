"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Tag, Trash2 } from "lucide-react";
import { ImagePicker } from "@/components/ImagePicker";
import { Badge, Button, Card, EmptyState, Input, Select, Spinner, Switch, Textarea, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import { dealMath } from "@/lib/pricing";
import { slugify } from "@/lib/slug";
import type { Deal, Product } from "@/lib/types";

const toLocal = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

export function DealsManager({ products }: { products: Product[] }) {
  const { currency } = useAuth();
  const { run, busy } = useAction();
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const blank = () => ({ name: "", description: "", type: "FIXED" as "FIXED" | "PERCENTAGE", value: "", start: toLocal(new Date(Date.now() - 60000)), end: toLocal(new Date(Date.now() + 90 * 86400000)), lines: [{ variant: "", qty: "1" }] });
  const [f, setF] = useState(blank);

  const load = useCallback(async () => { setDeals(await api.list<Deal>("/catalog/deals/", { active: "false" })); setLoading(false); }, []);
  useEffect(() => { load().catch(() => setLoading(false)); }, [load]);

  const variants = useMemo(() => products.filter((p) => p.is_active).flatMap((p) => p.variants.filter((v) => v.is_active).map((v) => ({ id: v.id, label: p.variants.length > 1 ? `${p.name} · ${v.name}` : p.name, price: Number(v.base_price) }))), [products]);
  const base = f.lines.reduce((s, l) => s + (variants.find((v) => String(v.id) === l.variant)?.price ?? 0) * (Number(l.qty) || 0), 0);
  const off = f.type === "PERCENTAGE" ? base * (Number(f.value) || 0) / 100 : Number(f.value) || 0;
  const valid = f.name.trim() && Number(f.value) > 0 && f.lines.every((l) => l.variant && Number(l.qty) >= 1) && off < base && (f.type === "FIXED" || Number(f.value) <= 100) && f.start < f.end;

  async function create() {
    const r = await run(async () => {
      const deal = await api.post<Deal>("/catalog/deals/", {
        name: f.name.trim(), slug: `${slugify(f.name)}-${Math.random().toString(36).slice(2, 5)}`, description: f.description.trim(),
        discount_type: f.type, discount_value: Number(f.value).toFixed(2), start_at: new Date(f.start).toISOString(), end_at: new Date(f.end).toISOString(), is_active: true,
      });
      for (const l of f.lines) await api.post("/catalog/deal-items/", { deal: deal.id, product_variant: Number(l.variant), quantity: Number(l.qty) });
      return deal;
    }, "Deal created");
    if (r) { setF(blank()); setOpen(false); load(); }
  }
  const toggle = async (d: Deal) => { if ((await run(() => api.post(`/catalog/deals/${d.id}/toggle/`))) !== undefined) load(); };
  const del = async (d: Deal) => { if (confirm(`Delete deal "${d.name}"?`) && (await run(() => api.del(`/catalog/deals/${d.id}/`))) !== undefined) load(); };

  if (loading) return <Spinner />;
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-sunken px-6 py-3">
        <div><h2 className="font-bold">Deals &amp; combos</h2><p className="text-xs text-muted">Bundle dishes at a special price. They show at the top of the POS.</p></div>
        <Button size="sm" variant={open ? "secondary" : "primary"} onClick={() => setOpen(!open)} data-testid="new-deal"><Plus className="h-4 w-4" />{open ? "Close" : "New deal"}</Button>
      </div>

      {open && (
        <div className="space-y-4 border-b border-line p-6" data-testid="deal-form">
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label="Deal name" placeholder="e.g. Zinger Combo" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
            <Input label="Short description (optional)" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} />
          </div>
          <div>
            <p className="mb-2 text-sm font-semibold">What is in the deal?</p>
            <div className="space-y-2">
              {f.lines.map((l, i) => (
                <div key={i} className="flex gap-2">
                  <Select aria-label="Dish" className="flex-1" value={l.variant} onChange={(e) => setF({ ...f, lines: f.lines.map((x, j) => (j === i ? { ...x, variant: e.target.value } : x)) })}>
                    <option value="">Choose dish…</option>{variants.map((v) => <option key={v.id} value={v.id}>{v.label} · {money(v.price, currency)}</option>)}
                  </Select>
                  <div className="w-20"><Input aria-label="Quantity" type="number" min="1" value={l.qty} onChange={(e) => setF({ ...f, lines: f.lines.map((x, j) => (j === i ? { ...x, qty: e.target.value } : x)) })} /></div>
                  {f.lines.length > 1 && <Button variant="ghost" aria-label="Remove line" onClick={() => setF({ ...f, lines: f.lines.filter((_, j) => j !== i) })}><Trash2 className="h-4 w-4" /></Button>}
                </div>
              ))}
            </div>
            <button type="button" onClick={() => setF({ ...f, lines: [...f.lines, { variant: "", qty: "1" }] })} className="mt-2 text-sm font-semibold text-brand">+ Add another dish</button>
          </div>
          <div className="grid gap-3 sm:grid-cols-4">
            <Select label="Discount type" value={f.type} onChange={(e) => setF({ ...f, type: e.target.value as "FIXED" | "PERCENTAGE" })}><option value="FIXED">Amount off ({currency})</option><option value="PERCENTAGE">Percent off (%)</option></Select>
            <Input label={f.type === "FIXED" ? `Amount (${currency})` : "Percent"} type="number" min="0" step="any" inputMode="decimal" value={f.value} onChange={(e) => setF({ ...f, value: e.target.value })} />
            <Input label="Starts" type="datetime-local" value={f.start} onChange={(e) => setF({ ...f, start: e.target.value })} />
            <Input label="Ends" type="datetime-local" value={f.end} onChange={(e) => setF({ ...f, end: e.target.value })} />
          </div>
          {base > 0 && <p className="rounded-xl bg-brand-soft px-4 py-2.5 text-sm text-brand">Regular price <b className="num">{money(base, currency)}</b> → customer pays <b className="num">{money(Math.max(0, base - off), currency)}</b>{off >= base && " (discount is too big)"}</p>}
          <p className="text-xs text-muted">After creating, tap the deal picture to add a photo.</p>
          <Button loading={busy} disabled={!valid} onClick={create} data-testid="save-deal">Create deal</Button>
        </div>
      )}

      {deals.length === 0 ? <div className="p-6"><EmptyState icon={<Tag className="h-8 w-8" />} title="No deals yet" hint="Create a combo like “Zinger Burger + Fries + Drink”." /></div> : (
        <ul className="divide-y divide-line">
          {deals.map((d) => {
            const m = dealMath(d, products);
            return (
              <li key={d.id} className="flex flex-wrap items-center gap-4 px-6 py-4" data-testid={`deal-row-${d.id}`}>
                <ImagePicker kind="deal" id={d.id} src={d.image} name={d.name} size="h-16 w-16" onChanged={(url) => setDeals((s) => s.map((x) => (x.id === d.id ? { ...x, image: url } : x)))} />
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">{d.name} {!d.is_active && <Badge tone="neutral">Paused</Badge>}</p>
                  <p className="truncate text-xs text-muted">{d.items.map((i) => `${i.quantity}× ${i.product_name}`).join(" + ")}</p>
                  {m && <p className="num text-sm font-bold text-brand">{money(m.price, currency)} <span className="text-xs font-medium text-muted line-through">{money(m.base, currency)}</span></p>}
                </div>
                <Switch label={`Deal ${d.name} active`} checked={d.is_active} onChange={() => toggle(d)} />
                <Button size="sm" variant="ghost" aria-label={`Delete ${d.name}`} onClick={() => del(d)}><Trash2 className="h-4 w-4" /></Button>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
