"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Boxes, PackagePlus, Search } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Select, Spinner, Textarea, cn, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import { UNIT_OPTIONS, formatQty } from "@/lib/units";
import type { Ingredient, Movement, Paginated, StockRow } from "@/lib/types";

const KINDS = [
  { id: "PURCHASE", label: "Purchase (stock arrived)" },
  { id: "OPENING", label: "Opening stock" },
  { id: "WASTAGE", label: "Wastage (spoiled / dropped)" },
  { id: "ADJUSTMENT", label: "Count correction (+ / −)" },
] as const;

export default function InventoryPage() {
  const { me, location, currency } = useAuth();
  const { run, busy } = useAction();
  const [rows, setRows] = useState<StockRow[]>([]);
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [moves, setMoves] = useState<Movement[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"stock" | "history">("stock");
  const [search, setSearch] = useState("");
  const [lowOnly, setLowOnly] = useState(false);
  const [open, setOpen] = useState(false);

  const [ingId, setIngId] = useState("");
  const [kind, setKind] = useState<(typeof KINDS)[number]["id"]>("PURCHASE");
  const [qty, setQty] = useState("");
  const [unit, setUnit] = useState("");
  const [cost, setCost] = useState("");
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    if (!location) return;
    const [s, i, m] = await Promise.all([
      api.get<{ results: StockRow[] }>("/inventory/stock/", { location: location.id }),
      api.list<Ingredient>("/inventory/ingredients/"),
      api.get<Paginated<Movement>>("/inventory/stock/movements/", { location: location.id, page_size: 50 }).then((r) => r.results).catch(() => []),
    ]);
    setRows(s.results); setIngredients(i.filter((x) => !x.is_prepared)); setMoves(m);
    setLoading(false);
  }, [location]);

  useEffect(() => { load().catch(() => setLoading(false)); }, [load]);

  const chosen = ingredients.find((i) => String(i.id) === ingId);
  const units = chosen ? UNIT_OPTIONS[chosen.base_unit] : [];
  useEffect(() => { if (chosen) setUnit(UNIT_OPTIONS[chosen.base_unit][0].value); }, [ingId]); // eslint-disable-line react-hooks/exhaustive-deps

  const shown = useMemo(() => rows.filter((r) =>
    (!lowOnly || r.is_low) && r.ingredient_name.toLowerCase().includes(search.trim().toLowerCase())), [rows, search, lowOnly]);
  const totalValue = rows.reduce((s, r) => s + Number(r.stock_value), 0);
  const lowCount = rows.filter((r) => r.is_low).length;

  async function save() {
    if (!location || !chosen) return;
    const ok = await run(() => api.post("/inventory/stock/movements/", {
      location: location.id, ingredient: chosen.id, movement_type: kind, quantity: qty, unit,
      ...(cost && (kind === "PURCHASE" || kind === "OPENING") ? { unit_cost: cost } : {}), note,
    }), "Stock updated");
    if (ok !== undefined) { setOpen(false); setQty(""); setCost(""); setNote(""); load(); }
  }

  if (me && !me.organization) return <PlatformNotice />;
  if (loading) return <Spinner label="Loading stock…" />;

  return (
    <>
      <PageHeader title="Inventory" subtitle={`${location?.name} · stock updates automatically when orders go to the kitchen`}
        actions={me?.can_manage_inventory ? <Button onClick={() => setOpen(true)} disabled={ingredients.length === 0}><PackagePlus className="h-4 w-4" />Add / adjust stock</Button> : undefined} />

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-3">
        <Card className="p-5"><p className="text-sm text-muted">Ingredients</p><p className="text-3xl font-bold">{rows.length}</p></Card>
        <Card className="p-5"><p className="text-sm text-muted">Low stock</p><p className={cn("text-3xl font-bold", lowCount > 0 && "text-warn")}>{lowCount}</p></Card>
        <Card className="col-span-2 p-5 lg:col-span-1"><p className="text-sm text-muted">Stock value</p><p className="text-3xl font-bold">{money(totalValue, currency)}</p></Card>
      </div>

      {ingredients.length === 0 ? (
        <EmptyState icon={<Boxes className="h-8 w-8" />} title="No ingredients yet" hint="Add ingredients and recipes in Setup, then record your opening stock here."
          action={me?.is_owner ? <a href="/setup?step=ingredients"><Button>Go to Setup</Button></a> : undefined} />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="inline-flex rounded-xl bg-sunken p-1">
              {(["stock", "history"] as const).map((t) => (
                <button key={t} onClick={() => setTab(t)} className={cn("rounded-lg px-4 py-2 text-sm font-semibold capitalize transition", tab === t ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink")}>{t}</button>
              ))}
            </div>
            {tab === "stock" && (
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm text-muted"><input type="checkbox" checked={lowOnly} onChange={(e) => setLowOnly(e.target.checked)} className="accent-[rgb(var(--brand))]" />Low only</label>
                <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input aria-label="Search" placeholder="Search…" className="w-48 pl-9" value={search} onChange={(e) => setSearch(e.target.value)} /></div>
              </div>
            )}
          </div>

          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              {tab === "stock" ? (
                <table className="w-full text-sm">
                  <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">Ingredient</th><th className="px-5 py-3 text-right">In stock</th><th className="px-5 py-3 text-right">Reorder at</th><th className="px-5 py-3 text-right">Value</th><th className="px-5 py-3">Status</th></tr></thead>
                  <tbody className="divide-y divide-line">
                    {shown.map((r) => (
                      <tr key={r.ingredient} className="hover:bg-sunken/50">
                        <td className="px-5 py-3 font-semibold">{r.ingredient_name}</td>
                        <td className={cn("px-5 py-3 text-right font-semibold", Number(r.quantity) < 0 && "text-bad")}>{formatQty(r.quantity, r.base_unit)}</td>
                        <td className="px-5 py-3 text-right text-muted">{Number(r.reorder_level) > 0 ? formatQty(r.reorder_level, r.base_unit) : "-"}</td>
                        <td className="px-5 py-3 text-right">{money(r.stock_value, currency)}</td>
                        <td className="px-5 py-3">{Number(r.quantity) < 0 ? <Badge tone="bad">Negative</Badge> : r.is_low ? <Badge tone="warn"><AlertTriangle className="h-3 w-3" />Low</Badge> : <Badge tone="good">OK</Badge>}</td>
                      </tr>
                    ))}
                    {shown.length === 0 && <tr><td colSpan={5} className="px-5 py-10 text-center text-muted">No ingredients match.</td></tr>}
                  </tbody>
                </table>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-sunken text-left text-[13px] font-semibold text-muted"><tr><th className="px-5 py-3">When</th><th className="px-5 py-3">Ingredient</th><th className="px-5 py-3">Type</th><th className="px-5 py-3 text-right">Change</th><th className="px-5 py-3 text-right">Balance</th><th className="px-5 py-3">Note</th></tr></thead>
                  <tbody className="divide-y divide-line">
                    {moves.map((m) => (
                      <tr key={m.id}>
                        <td className="whitespace-nowrap px-5 py-3 text-muted">{new Date(m.created_at).toLocaleString("en-PK", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</td>
                        <td className="px-5 py-3 font-semibold">{m.ingredient_name}</td>
                        <td className="px-5 py-3"><Badge tone={Number(m.quantity_change) >= 0 ? "good" : "neutral"}>{m.movement_type_display}</Badge></td>
                        <td className={cn("px-5 py-3 text-right font-semibold", Number(m.quantity_change) >= 0 ? "text-good" : "text-bad")}>{Number(m.quantity_change) > 0 ? "+" : ""}{formatQty(m.quantity_change, m.base_unit)}</td>
                        <td className="px-5 py-3 text-right">{formatQty(m.balance_after, m.base_unit)}</td>
                        <td className="px-5 py-3 text-muted">{m.note}{m.created_by_name ? ` · ${m.created_by_name}` : ""}</td>
                      </tr>
                    ))}
                    {moves.length === 0 && <tr><td colSpan={6} className="px-5 py-10 text-center text-muted">No stock movements yet.</td></tr>}
                  </tbody>
                </table>
              )}
            </div>
          </Card>
        </>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="Add / adjust stock">
        <div className="space-y-4">
          <Select label="Ingredient" value={ingId} onChange={(e) => setIngId(e.target.value)}>
            <option value="">Choose…</option>
            {ingredients.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
          </Select>
          <Select label="What happened?" value={kind} onChange={(e) => setKind(e.target.value as typeof kind)}>
            {KINDS.map((k) => <option key={k.id} value={k.id}>{k.label}</option>)}
          </Select>
          <div className="grid grid-cols-[1fr_130px] gap-3">
            <Input label="Quantity" type="number" inputMode="decimal" step="any" value={qty} onChange={(e) => setQty(e.target.value)} placeholder={kind === "ADJUSTMENT" ? "e.g. -2 or 5" : "e.g. 5"} />
            <Select label="Unit" value={unit} onChange={(e) => setUnit(e.target.value)} disabled={!chosen}>{units.map((u) => <option key={u.value} value={u.value}>{u.label}</option>)}</Select>
          </div>
          {(kind === "PURCHASE" || kind === "OPENING") && (
            <Input label={`Price ${unit ? `per ${unit === "l" ? "litre" : unit}` : ""} (optional)`} type="number" inputMode="decimal" step="any" value={cost} onChange={(e) => setCost(e.target.value)} hint="Used to keep your food cost accurate (weighted average)." />
          )}
          <Textarea label="Note (optional)" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
          <Button className="w-full" size="lg" loading={busy} disabled={!chosen || !qty || Number(qty) === 0} onClick={save}>Save</Button>
        </div>
      </Modal>
    </>
  );
}
