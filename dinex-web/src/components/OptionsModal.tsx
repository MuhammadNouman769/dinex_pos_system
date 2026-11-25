"use client";
import { useEffect, useMemo, useState } from "react";
import { Check, Minus, Plus } from "lucide-react";
import { Button, Input, Modal, cn } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/api";
import type { ModGroup, Product, Variant } from "@/lib/types";

export interface Picked { mods: { id: number; group: string; name: string; price: number }[]; note: string; qty: number }

/** Ask for a dish's options (spice level, extras…) and an optional note before it goes into the order. */
export function OptionsModal({ product, variant, open, onClose, onAdd }: { product: Product | null; variant: Variant | null; open: boolean; onClose: () => void; onAdd: (p: Picked) => void }) {
  const { currency } = useAuth();
  const groups = useMemo(() => product?.modifier_groups ?? [], [product]);
  const [sel, setSel] = useState<Record<number, number[]>>({});
  const [note, setNote] = useState("");
  const [qty, setQty] = useState(1);
  useEffect(() => {
    if (!open) return;
    const init: Record<number, number[]> = {};
    groups.forEach((g) => { if (g.required && g.max === 1 && g.options[0]) init[g.id] = []; });
    setSel(init); setNote(""); setQty(1);
  }, [open, groups]);
  if (!product || !variant) return null;

  const toggle = (g: ModGroup, id: number) => setSel((s) => {
    const cur = s[g.id] ?? [];
    if (cur.includes(id)) return { ...s, [g.id]: cur.filter((x) => x !== id) };
    if (g.max === 1) return { ...s, [g.id]: [id] };
    if (g.max > 0 && cur.length >= g.max) return s;
    return { ...s, [g.id]: [...cur, id] };
  });
  const missing = groups.find((g) => (sel[g.id]?.length ?? 0) < g.min);
  const mods = groups.flatMap((g) => (sel[g.id] ?? []).map((id) => { const o = g.options.find((x) => x.id === id)!; return { id, group: g.name, name: o.name, price: Number(o.price) }; }));
  const unit = Number(variant.base_price) + mods.reduce((a, m) => a + m.price, 0);

  return (
    <Modal open={open} onClose={onClose} title={product.name + (product.variants.length > 1 ? ` · ${variant.name}` : "")} width="max-w-md">
      <div className="space-y-5">
        {groups.map((g) => {
          const n = sel[g.id]?.length ?? 0;
          return (
            <section key={g.id} data-testid={`group-${g.id}`}>
              <div className="mb-2 flex items-baseline justify-between"><h3 className="font-semibold">{g.name}</h3>
                <span className="text-xs font-medium text-muted">{g.min > 0 ? "Required" : "Optional"}{g.max > 1 ? ` · up to ${g.max}` : g.max === 0 ? " · any" : ""}{g.max > 1 && n > 0 ? ` (${n})` : ""}</span></div>
              <div className="grid gap-2">
                {g.options.map((o) => {
                  const on = sel[g.id]?.includes(o.id);
                  return (
                    <button key={o.id} type="button" role={g.max === 1 ? "radio" : "checkbox"} aria-checked={!!on} onClick={() => toggle(g, o.id)} data-testid={`opt-${o.id}`}
                      className={cn("flex min-h-[48px] items-center justify-between gap-3 rounded-xl border px-3.5 text-left text-sm font-medium transition", on ? "border-brand bg-brand-soft" : "border-line hover:bg-sunken")}>
                      <span className="flex items-center gap-2.5"><span className={cn("grid h-5 w-5 place-items-center border", g.max === 1 ? "rounded-full" : "rounded-md", on ? "border-brand bg-brand text-white" : "border-line")}>{on && <Check className="h-3 w-3" strokeWidth={3} />}</span>{o.name}</span>
                      {Number(o.price) !== 0 && <span className="num text-xs font-semibold text-muted">{Number(o.price) > 0 ? "+" : "−"} {money(Math.abs(Number(o.price)), currency)}</span>}
                    </button>
                  );
                })}
              </div>
            </section>
          );
        })}
        <Input label="Note for the kitchen (optional)" placeholder="e.g. no onions, extra crispy" maxLength={200} value={note} onChange={(e) => setNote(e.target.value)} data-testid="opt-note" />
        <div className="flex items-center gap-3">
          <div className="flex items-center rounded-full border border-line p-0.5">
            <button type="button" aria-label="Less" onClick={() => setQty(Math.max(1, qty - 1))} className="grid h-10 w-10 place-items-center rounded-full hover:bg-sunken"><Minus className="h-4 w-4" /></button>
            <span className="num w-8 text-center font-bold">{qty}</span>
            <button type="button" aria-label="More" onClick={() => setQty(qty + 1)} className="grid h-10 w-10 place-items-center rounded-full hover:bg-sunken"><Plus className="h-4 w-4" /></button>
          </div>
          <Button size="lg" className="flex-1" disabled={!!missing} onClick={() => onAdd({ mods, note: note.trim(), qty })} data-testid="opt-add">{missing ? `Choose ${missing.name}` : `Add · ${money(unit * qty, currency)}`}</Button>
        </div>
      </div>
    </Modal>
  );
}
