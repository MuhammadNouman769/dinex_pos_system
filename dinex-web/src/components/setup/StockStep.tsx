"use client";
import { useEffect, useState } from "react";
import { PackageCheck } from "lucide-react";
import { Button, Card, EmptyState, Input, Select, Spinner, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { UNIT_OPTIONS } from "@/lib/units";
import type { Ingredient, StockRow } from "@/lib/types";

export function StockStep() {
  const { location } = useAuth();
  const { run, busy } = useAction();
  const [items, setItems] = useState<Ingredient[]>([]);
  const [have, setHave] = useState<Record<number, number>>({});
  const [vals, setVals] = useState<Record<number, { qty: string; unit: string }>>({});
  const [loading, setLoading] = useState(true);

  const load = async () => {
    if (!location) return;
    const [i, s] = await Promise.all([api.list<Ingredient>("/inventory/ingredients/", { prepared: "false" }), api.get<{ results: StockRow[] }>("/inventory/stock/", { location: location.id })]);
    setItems(i.filter((x) => !x.is_prepared));
    setHave(Object.fromEntries(s.results.map((r) => [r.ingredient, Number(r.quantity)])));
    setLoading(false);
  };
  useEffect(() => { load().catch(() => setLoading(false)); }, [location]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <Spinner />;
  if (items.length === 0) return <EmptyState icon={<PackageCheck className="h-8 w-8" />} title="No ingredients yet" hint="Add ingredients first, then enter what you have on the shelf today." />;

  const filled = items.filter((i) => Number(vals[i.id]?.qty) > 0);
  async function save() {
    const ok = await run(async () => {
      for (const i of filled) {
        const v = vals[i.id];
        await api.post("/inventory/stock/movements/", { location: location!.id, ingredient: i.id, movement_type: "OPENING", quantity: v.qty, unit: v.unit || UNIT_OPTIONS[i.base_unit][0].value, note: "Opening stock" });
      }
      return true;
    }, "Opening stock saved");
    if (ok) { setVals({}); load(); }
  }

  return (
    <Card className="max-w-3xl p-6">
      <h2 className="text-lg font-bold">Opening stock</h2>
      <p className="mb-5 text-sm text-muted">Count what you have today at <b>{location?.name}</b> and enter it once. After this, purchases and sales keep it up to date. Leave blank anything you have none of.</p>
      <div className="divide-y divide-line">
        {items.map((i) => {
          const v = vals[i.id] ?? { qty: "", unit: UNIT_OPTIONS[i.base_unit][0].value };
          return (
            <div key={i.id} className="grid grid-cols-[1fr_110px_100px] items-center gap-3 py-3">
              <div><p className="font-semibold">{i.name}</p>{have[i.id] ? <p className="text-xs text-muted">Already recorded: {have[i.id].toLocaleString()} {i.base_unit.toLowerCase()}</p> : null}</div>
              <Input aria-label={`${i.name} quantity`} type="number" min="0" step="any" inputMode="decimal" placeholder="0" value={v.qty} onChange={(e) => setVals((s) => ({ ...s, [i.id]: { ...v, qty: e.target.value } }))} />
              <Select aria-label={`${i.name} unit`} value={v.unit} onChange={(e) => setVals((s) => ({ ...s, [i.id]: { ...v, unit: e.target.value } }))}>
                {UNIT_OPTIONS[i.base_unit].map((u) => <option key={u.value} value={u.value}>{u.label}</option>)}
              </Select>
            </div>
          );
        })}
      </div>
      <Button className="mt-5" loading={busy} disabled={filled.length === 0} onClick={save}>Save opening stock{filled.length ? ` (${filled.length})` : ""}</Button>
    </Card>
  );
}
