"use client";
import { useCallback, useEffect, useState } from "react";
import { ChefHat, Package, Plus, Trash2 } from "lucide-react";
import { Badge, Button, Card, EmptyState, Input, Select, Spinner, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import { BASE_LABEL, PRICE_UNIT } from "@/lib/units";
import type { BaseUnit, Ingredient } from "@/lib/types";

export function IngredientsStep() {
  const { currency } = useAuth();
  const { run, busy } = useAction();
  const [items, setItems] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [f, setF] = useState<{ name: string; base_unit: BaseUnit; price: string; reorder: string; prepared: boolean }>({ name: "", base_unit: "G", price: "", reorder: "", prepared: false });

  const load = useCallback(async () => { setItems(await api.list<Ingredient>("/inventory/ingredients/")); setLoading(false); }, []);
  useEffect(() => { load().catch(() => setLoading(false)); }, [load]);
  if (loading) return <Spinner />;

  const unit = PRICE_UNIT[f.base_unit];
  const bigName = f.base_unit === "G" ? "kg" : f.base_unit === "ML" ? "litre" : "piece";

  async function add() {
    const r = await run(() => api.post("/inventory/ingredients/", {
      name: f.name.trim(), base_unit: f.base_unit, is_prepared: f.prepared,
      // people think in Rs/kg and "reorder at 2 kg"; the API stores per gram / per ml
      cost_per_unit: f.prepared || !f.price ? "0" : String(Number(f.price) / unit.factor),
      reorder_level: f.prepared || !f.reorder ? "0" : String(Number(f.reorder) * unit.factor),
    }), `${f.name.trim()} added`);
    if (r !== undefined) { setF((s) => ({ ...s, name: "", price: "", reorder: "", prepared: false })); load(); }
  }
  const del = async (i: Ingredient) => { if (confirm(`Delete ${i.name}?`) && (await run(() => api.del(`/inventory/ingredients/${i.id}/`))) !== undefined) load(); };

  const raw = items.filter((i) => !i.is_prepared);
  const prepared = items.filter((i) => i.is_prepared);

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-lg font-bold">Add an ingredient</h2>
        <p className="mb-4 text-sm text-muted">Everything your kitchen uses: chicken, buns, cheese, oil, sauces. Things you make in-house (patty, marinated chicken) are “prepared items”: you give them their own recipe in the next step.</p>
        <div className="grid items-end gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input label="Name" placeholder="e.g. Chicken mince" value={f.name} onChange={(e) => setF((s) => ({ ...s, name: e.target.value }))} />
          <Select label="Measured in" value={f.base_unit} onChange={(e) => setF((s) => ({ ...s, base_unit: e.target.value as BaseUnit }))}>
            {(Object.keys(BASE_LABEL) as BaseUnit[]).map((u) => <option key={u} value={u}>{BASE_LABEL[u]}</option>)}
          </Select>
          <Input label={`Cost (${currency} ${unit.label})`} type="number" min="0" step="any" disabled={f.prepared} value={f.price} onChange={(e) => setF((s) => ({ ...s, price: e.target.value }))} />
          <Input label={`Reorder at (${bigName})`} type="number" min="0" step="any" disabled={f.prepared} value={f.reorder} onChange={(e) => setF((s) => ({ ...s, reorder: e.target.value }))} hint="Warn me below this" />
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.prepared} onChange={(e) => setF((s) => ({ ...s, prepared: e.target.checked, base_unit: e.target.checked ? "PCS" : s.base_unit }))} className="h-4 w-4 accent-[rgb(var(--brand))]" />This is made in-house (has its own recipe)</label>
          <Button loading={busy} disabled={!f.name.trim()} onClick={add}><Plus className="h-4 w-4" />Add</Button>
        </div>
      </Card>

      {items.length === 0 ? <EmptyState icon={<Package className="h-8 w-8" />} title="No ingredients yet" hint="Add your first ingredient above." /> : (
        <div className="grid gap-6 lg:grid-cols-2">
          <List title="Raw ingredients" icon={<Package className="h-4 w-4" />} items={raw} currency={currency} onDelete={del} />
          <List title="Prepared in-house" icon={<ChefHat className="h-4 w-4" />} items={prepared} currency={currency} onDelete={del} empty="Patties, sauces, marinades…" />
        </div>
      )}
    </div>
  );
}

function List({ title, icon, items, currency, onDelete, empty = "None yet." }: { title: string; icon: React.ReactNode; items: Ingredient[]; currency: string; onDelete: (i: Ingredient) => void; empty?: string }) {
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-2 border-b border-line bg-sunken px-5 py-3 font-bold">{icon}{title}<Badge className="ml-auto">{items.length}</Badge></div>
      <ul className="divide-y divide-line">
        {items.map((i) => (
          <li key={i.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
            <div><p className="font-semibold">{i.name}</p><p className="text-xs text-muted">{i.base_unit === "PCS" ? "pieces" : i.base_unit === "G" ? "by weight" : "by volume"}{!i.is_prepared && Number(i.cost_per_unit) > 0 ? ` · ${money(Number(i.cost_per_unit) * PRICE_UNIT[i.base_unit].factor, currency)} ${PRICE_UNIT[i.base_unit].label}` : ""}</p></div>
            <Button size="sm" variant="ghost" aria-label={`Delete ${i.name}`} onClick={() => onDelete(i)}><Trash2 className="h-4 w-4" /></Button>
          </li>
        ))}
        {items.length === 0 && <li className="px-5 py-6 text-center text-sm text-muted">{empty}</li>}
      </ul>
    </Card>
  );
}
