"use client";
import { useCallback, useEffect, useState } from "react";
import { Plus, Trash2, UtensilsCrossed, X } from "lucide-react";
import { Badge, Button, Card, EmptyState, Input, Select, Spinner, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import { ImagePicker } from "@/components/ImagePicker";
import { DealsManager } from "@/components/setup/DealsManager";
import { makeSku, slugify } from "@/lib/slug";
import { DishOptions } from "@/components/setup/DishOptions";
import type { Category, Product } from "@/lib/types";

export function MenuStep() {
  const { currency } = useAuth();
  const { run, busy } = useAction();
  const [cats, setCats] = useState<Category[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [optsFor, setOptsFor] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [catName, setCatName] = useState("");
  const [item, setItem] = useState({ category: "", name: "", price: "" });
  const [size, setSize] = useState<{ product: number | null; name: string; price: string }>({ product: null, name: "", price: "" });

  const load = useCallback(async () => {
    const [c, p] = await Promise.all([api.list<Category>("/catalog/categories/"), api.list<Product>("/catalog/products/")]);
    setCats(c); setProducts(p); setLoading(false);
  }, []);
  useEffect(() => { load().catch(() => setLoading(false)); }, [load]);
  if (loading) return <Spinner />;

  const addCat = async () => {
    const name = catName.trim(); if (!name) return;
    const r = await run(() => api.post<Category>("/catalog/categories/", { name, slug: slugify(name) }));
    if (r) { setCatName(""); setItem((s) => ({ ...s, category: String(r.id) })); load(); }
  };
  const delCat = async (c: Category) => { if (confirm(`Delete category "${c.name}"?`) && (await run(() => api.del(`/catalog/categories/${c.id}/`))) !== undefined) load(); };

  const addItem = async () => {
    const name = item.name.trim();
    const r = await run(() => api.post("/catalog/products/", {
      category: Number(item.category), name, slug: `${slugify(name)}-${Math.random().toString(36).slice(2, 5)}`, sku: makeSku(name),
      variants: [{ name: "Regular", base_price: item.price }],
    }), `${name} added`);
    if (r !== undefined) { setItem((s) => ({ ...s, name: "", price: "" })); load(); }
  };
  const delItem = async (p: Product) => {
    if (!confirm(`Delete "${p.name}"?`)) return;
    // a product can only be deleted once its sizes are gone
    const r = await run(async () => { for (const v of p.variants) await api.del(`/catalog/variants/${v.id}/`); await api.del(`/catalog/products/${p.id}/`); return true; }, "Dish removed");
    if (r) load();
  };
  const addSize = async () => {
    if (!size.product) return;
    const r = await run(() => api.post("/catalog/variants/", { product: size.product, name: size.name.trim(), base_price: size.price }), "Size added");
    if (r !== undefined) { setSize({ product: null, name: "", price: "" }); load(); }
  };
  const delSize = async (id: number) => { if ((await run(() => api.del(`/catalog/variants/${id}/`))) !== undefined) load(); };

  const canAddItem = item.category && item.name.trim() && Number(item.price) > 0;

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-lg font-bold">Categories</h2>
        <p className="mb-4 text-sm text-muted">Group your dishes: Burgers, Pizza, Drinks, Desserts…</p>
        <div className="mb-4 flex flex-wrap gap-2">
          {cats.map((c) => (
            <span key={c.id} className="inline-flex items-center gap-2 rounded-full bg-brand-soft px-3.5 py-1.5 text-sm font-semibold text-brand">
              {c.name}<button aria-label={`Delete ${c.name}`} onClick={() => delCat(c)} className="opacity-60 hover:opacity-100"><X className="h-3.5 w-3.5" /></button>
            </span>
          ))}
          {cats.length === 0 && <p className="text-sm text-muted">No categories yet.</p>}
        </div>
        <form className="flex max-w-md gap-2" onSubmit={(e) => { e.preventDefault(); addCat(); }}>
          <Input aria-label="New category" placeholder="New category name" value={catName} onChange={(e) => setCatName(e.target.value)} />
          <Button type="submit" variant="secondary" disabled={!catName.trim()} loading={busy}>Add</Button>
        </form>
      </Card>

      <Card className="p-6">
        <h2 className="text-lg font-bold">Add a dish</h2>
        <p className="mb-4 text-sm text-muted">Start with the regular size. You can add Small / Large sizes after.</p>
        <div className="grid items-end gap-3 sm:grid-cols-[1fr_1.4fr_140px_auto]">
          <Select label="Category" value={item.category} onChange={(e) => setItem((s) => ({ ...s, category: e.target.value }))}>
            <option value="">Choose…</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
          <Input label="Dish name" placeholder="e.g. Zinger Burger" value={item.name} onChange={(e) => setItem((s) => ({ ...s, name: e.target.value }))} />
          <Input label={`Price (${currency})`} type="number" min="0" step="any" inputMode="decimal" value={item.price} onChange={(e) => setItem((s) => ({ ...s, price: e.target.value }))} />
          <Button loading={busy} disabled={!canAddItem} onClick={addItem}><Plus className="h-4 w-4" />Add</Button>
        </div>
      </Card>

      {products.length === 0 ? <EmptyState icon={<UtensilsCrossed className="h-8 w-8" />} title="Your menu is empty" hint="Add a category, then your first dish." /> :
        cats.filter((c) => products.some((p) => p.category === c.id)).map((c) => (
          <Card key={c.id} className="overflow-hidden">
            <div className="border-b border-line bg-sunken px-6 py-3 font-bold">{c.name}</div>
            <ul className="divide-y divide-line">
              {products.filter((p) => p.category === c.id).map((p) => (
                <li key={p.id} className="px-6 py-4">
                  <div className="flex items-start justify-between gap-3">
                    <ImagePicker kind="product" id={p.id} src={p.image} name={p.name} onChanged={(url) => setProducts((s) => s.map((x) => (x.id === p.id ? { ...x, image: url } : x)))} />
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold">{p.name}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {p.variants.map((v) => (
                          <Badge key={v.id} tone="neutral" className="gap-2">
                            {v.name} · {money(v.base_price, currency)}
                            {p.variants.length > 1 && <button aria-label={`Remove ${v.name}`} onClick={() => delSize(v.id)} className="opacity-60 hover:text-bad hover:opacity-100"><X className="h-3 w-3" /></button>}
                          </Badge>
                        ))}
                        <button onClick={() => setOptsFor(p)} data-testid={`dish-options-${p.id}`} className="rounded-full border border-dashed border-line px-2.5 py-0.5 text-xs font-semibold text-muted hover:border-brand hover:text-brand">{(p.modifier_groups?.length ?? 0) > 0 ? `Options (${p.modifier_groups!.length})` : "+ options"}</button>
                        <button onClick={() => setSize({ product: p.id, name: "", price: "" })} className="rounded-full border border-dashed border-line px-2.5 py-0.5 text-xs font-semibold text-muted hover:border-brand hover:text-brand">+ size</button>
                      </div>
                    </div>
                    <Button size="sm" variant="ghost" aria-label={`Delete ${p.name}`} onClick={() => delItem(p)}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                  {size.product === p.id && (
                    <div className="mt-3 flex flex-wrap items-end gap-2 rounded-xl bg-sunken p-3">
                      <div className="w-40"><Input label="Size name" placeholder="Large" value={size.name} onChange={(e) => setSize((s) => ({ ...s, name: e.target.value }))} /></div>
                      <div className="w-32"><Input label="Price" type="number" min="0" step="any" value={size.price} onChange={(e) => setSize((s) => ({ ...s, price: e.target.value }))} /></div>
                      <Button size="sm" loading={busy} disabled={!size.name.trim() || !(Number(size.price) > 0)} onClick={addSize}>Add size</Button>
                      <Button size="sm" variant="ghost" onClick={() => setSize({ product: null, name: "", price: "" })}>Cancel</Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        ))}

      <DishOptions product={optsFor} open={!!optsFor} onClose={() => setOptsFor(null)} onChanged={load} />
      <DealsManager products={products} />
    </div>
  );
}
