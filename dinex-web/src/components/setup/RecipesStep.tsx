"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { BookOpen, Plus, Trash2 } from "lucide-react";
import { Badge, Button, Card, EmptyState, Input, Select, Spinner, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, ApiError, money } from "@/lib/api";
import { UNIT_OPTIONS } from "@/lib/units";
import type { Ingredient, Product, Recipe } from "@/lib/types";

interface Line { ingredient: string; qty: string; unit: string }
type Target = { kind: "variant" | "ingredient"; id: number; label: string; price?: number };
const baseUnitName = { G: "g", ML: "ml", PCS: "pcs" } as const;

export function RecipesStep() {
  const { currency } = useAuth();
  const { run, busy } = useAction();
  const [products, setProducts] = useState<Product[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [targetKey, setTargetKey] = useState("");
  const [lines, setLines] = useState<Line[]>([]);
  const [makes, setMakes] = useState("1");
  const [saved, setSaved] = useState<Recipe | null>(null);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    Promise.all([api.list<Product>("/catalog/products/"), api.list<Ingredient>("/inventory/ingredients/")])
      .then(([p, i]) => { setProducts(p); setIngredients(i); })
      .finally(() => setLoading(false));
  }, []);

  const targets: Target[] = useMemo(() => [
    ...products.flatMap((p) => p.variants.map((v) => ({ kind: "variant" as const, id: v.id, price: Number(v.base_price), label: p.variants.length > 1 ? `${p.name} · ${v.name}` : p.name }))),
    ...ingredients.filter((i) => i.is_prepared).map((i) => ({ kind: "ingredient" as const, id: i.id, label: i.name })),
  ], [products, ingredients]);
  const target = targets.find((t) => `${t.kind}:${t.id}` === targetKey);
  const prepTarget = target?.kind === "ingredient" ? ingredients.find((i) => i.id === target.id) : undefined;
  const usable = ingredients.filter((i) => i.is_active && i.id !== target?.id);

  const loadRecipe = useCallback(async (t: Target) => {
    setFetching(true); setSaved(null);
    try {
      const r = await api.get<Recipe>(`/inventory/recipes/${t.kind}/${t.id}/`);
      setSaved(r); setMakes(String(Number(r.output_quantity)));
      setLines(r.lines.map((l) => ({ ingredient: String(l.ingredient), qty: String(Number(l.quantity)), unit: baseUnitName[l.base_unit] })));
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 404)) throw e;
      setLines([{ ingredient: "", qty: "", unit: "" }]); setMakes("1");
    } finally { setFetching(false); }
  }, []);
  useEffect(() => { if (target) loadRecipe(target).catch(() => undefined); }, [targetKey]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <Spinner />;
  if (targets.length === 0 || ingredients.length === 0) {
    return <EmptyState icon={<BookOpen className="h-8 w-8" />} title="Add dishes and ingredients first" hint="Recipes connect your menu to your ingredients. Finish the Menu and Ingredients steps, then come back." />;
  }

  const setLine = (i: number, patch: Partial<Line>) => setLines((ls) => ls.map((l, j) => (j === i ? { ...l, ...patch } : l)));
  const onPick = (i: number, id: string) => {
    const ing = ingredients.find((x) => String(x.id) === id);
    setLine(i, { ingredient: id, unit: ing ? baseUnitName[ing.base_unit] : "" });
  };
  const valid = lines.length > 0 && lines.every((l) => l.ingredient && Number(l.qty) > 0);

  async function save() {
    if (!target) return;
    const r = await run(() => api.put<Recipe>(`/inventory/recipes/${target.kind}/${target.id}/`, {
      output_quantity: target.kind === "ingredient" ? makes : "1",
      lines: lines.map((l) => ({ ingredient: Number(l.ingredient), quantity: l.qty, unit: l.unit })),
    }), "Recipe saved");
    if (r) { setSaved(r); setLines(r.lines.map((l) => ({ ingredient: String(l.ingredient), qty: String(Number(l.quantity)), unit: baseUnitName[l.base_unit] }))); }
  }
  async function remove() {
    if (!target || !confirm("Remove this recipe? Selling it will stop using stock.")) return;
    if ((await run(() => api.del(`/inventory/recipes/${target.kind}/${target.id}/`), "Recipe removed")) !== undefined) { setSaved(null); setLines([{ ingredient: "", qty: "", unit: "" }]); }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <Card className="space-y-5 p-6">
        <div>
          <h2 className="text-lg font-bold">Recipe</h2>
          <p className="text-sm text-muted">Tell DineX what <b>one serving</b> uses. Every time that dish is sold, these ingredients are taken out of stock automatically.</p>
        </div>
        <Select label="Recipe for" value={targetKey} onChange={(e) => setTargetKey(e.target.value)}>
          <option value="">Choose a dish or prepared item…</option>
          <optgroup label="Dishes">{targets.filter((t) => t.kind === "variant").map((t) => <option key={`v${t.id}`} value={`variant:${t.id}`}>{t.label}</option>)}</optgroup>
          {targets.some((t) => t.kind === "ingredient") && <optgroup label="Prepared in-house">{targets.filter((t) => t.kind === "ingredient").map((t) => <option key={`i${t.id}`} value={`ingredient:${t.id}`}>{t.label}</option>)}</optgroup>}
        </Select>

        {target && (fetching ? <Spinner /> : (
          <>
            {prepTarget && (
              <div className="max-w-xs"><Input label={`One batch makes (${baseUnitName[prepTarget.base_unit]})`} type="number" min="0" step="any" value={makes} onChange={(e) => setMakes(e.target.value)} hint="e.g. a batch of patty mix makes 20 patties" /></div>
            )}
            <div className="space-y-2">
              <p className="text-[13px] font-semibold text-muted">{prepTarget ? "Ingredients per batch" : "Ingredients per serving"}</p>
              {lines.map((l, i) => {
                const ing = ingredients.find((x) => String(x.id) === l.ingredient);
                return (
                  <div key={i} className="grid grid-cols-[1fr_90px_90px_auto] items-center gap-2">
                    <Select aria-label="Ingredient" value={l.ingredient} onChange={(e) => onPick(i, e.target.value)}>
                      <option value="">Ingredient…</option>
                      {usable.map((x) => <option key={x.id} value={x.id} disabled={lines.some((o, j) => j !== i && o.ingredient === String(x.id))}>{x.name}{x.is_prepared ? " (prepared)" : ""}</option>)}
                    </Select>
                    <Input aria-label="Quantity" type="number" min="0" step="any" inputMode="decimal" placeholder="Qty" value={l.qty} onChange={(e) => setLine(i, { qty: e.target.value })} />
                    <Select aria-label="Unit" value={l.unit} disabled={!ing} onChange={(e) => setLine(i, { unit: e.target.value })}>
                      {(ing ? UNIT_OPTIONS[ing.base_unit] : []).map((u) => <option key={u.value} value={u.value}>{u.label}</option>)}
                    </Select>
                    <button aria-label="Remove line" onClick={() => setLines((ls) => ls.filter((_, j) => j !== i))} className="grid h-10 w-10 place-items-center rounded-xl text-muted hover:bg-bad-soft hover:text-bad"><Trash2 className="h-4 w-4" /></button>
                  </div>
                );
              })}
              <Button variant="ghost" size="sm" onClick={() => setLines((ls) => [...ls, { ingredient: "", qty: "", unit: "" }])}><Plus className="h-4 w-4" />Add ingredient</Button>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button loading={busy} disabled={!valid} onClick={save}>Save recipe</Button>
              {saved && <Button variant="danger" onClick={remove}>Remove recipe</Button>}
            </div>
          </>
        ))}
      </Card>

      <Card className="h-fit p-6">
        <h3 className="font-bold">Food cost</h3>
        {!saved ? <p className="mt-2 text-sm text-muted">Save the recipe to see what one serving costs you and your profit.</p> : (
          <dl className="mt-3 space-y-3 text-sm">
            <div className="flex justify-between"><dt className="text-muted">Cost{prepTarget ? " per unit" : " per serving"}</dt><dd className="font-bold">{money(saved.cost, currency)}</dd></div>
            {saved.price !== undefined && <>
              <div className="flex justify-between"><dt className="text-muted">Selling price</dt><dd className="font-bold">{money(saved.price, currency)}</dd></div>
              <div className="flex justify-between border-t border-line pt-3"><dt className="text-muted">Profit</dt><dd className={Number(saved.profit) >= 0 ? "font-bold text-good" : "font-bold text-bad"}>{money(saved.profit, currency)}</dd></div>
              {saved.margin_percent != null && <div className="flex justify-between"><dt className="text-muted">Margin</dt><dd><Badge tone={Number(saved.margin_percent) >= 50 ? "good" : Number(saved.margin_percent) >= 25 ? "warn" : "bad"}>{saved.margin_percent}%</Badge></dd></div>}
            </>}
            {Number(saved.cost) === 0 && <p className="rounded-lg bg-warn-soft p-2 text-xs text-warn">Cost is 0: add ingredient prices (Ingredients step or when you record a purchase).</p>}
          </dl>
        )}
      </Card>
    </div>
  );
}
