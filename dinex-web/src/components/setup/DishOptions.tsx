"use client";
import { useCallback, useEffect, useState } from "react";
import { Plus, SlidersHorizontal, Trash2, X } from "lucide-react";
import { Badge, Button, Input, Modal, Select, Spinner, useAction, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { ModGroup, Product } from "@/lib/types";

interface OrgGroup { id: number; name: string; options: { id: number; name: string; price_adjustment: string }[] }

/** Manage a dish's options (spice level, extras, sides): create a group, attach a shared one, or detach. */
export function DishOptions({ product, open, onClose, onChanged }: { product: Product | null; open: boolean; onClose: () => void; onChanged: () => void }) {
  const { currency } = useAuth();
  const toast = useToast();
  const { run, busy } = useAction();
  const [groups, setGroups] = useState<ModGroup[]>([]);
  const [all, setAll] = useState<OrgGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const blank = { name: "", required: false, multi: false, max: "3", options: [{ name: "", price: "" }, { name: "", price: "" }] };
  const [form, setForm] = useState(blank);
  const [attach, setAttach] = useState("");

  const load = useCallback(async () => {
    if (!product) return;
    setLoading(true);
    const [p, g] = await Promise.all([api.get<Product>(`/catalog/products/${product.id}/`), api.list<OrgGroup>("/catalog/modifier-groups/")]);
    setGroups(p.modifier_groups ?? []); setAll(g); setLoading(false);
  }, [product]);
  useEffect(() => { if (open) { setForm(blank); setAttach(""); load().catch((e) => toast.err(e.message)); } /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [open, load, toast]);
  if (!product) return null;

  const opts = form.options.filter((o) => o.name.trim());
  const max = form.multi ? Math.max(1, Number(form.max) || 1) : 1;
  const valid = form.name.trim() && opts.length >= 1;

  async function create() {
    const r = await run(async () => {
      const g = await api.post<{ id: number }>("/catalog/modifier-groups/", { name: form.name.trim(), is_required: form.required, min_selections: form.required ? 1 : 0, max_selections: max });
      for (const [i, o] of opts.entries()) await api.post("/catalog/modifier-options/", { modifier_group: g.id, name: o.name.trim(), price_adjustment: o.price || "0", position: i });
      await api.post("/catalog/product-modifier-groups/", { product: product!.id, modifier_group: g.id });
      return true;
    }, "Option group added");
    if (r) { setForm(blank); await load(); onChanged(); }
  }
  async function link() {
    const r = await run(() => api.post("/catalog/product-modifier-groups/", { product: product!.id, modifier_group: Number(attach) }), "Attached");
    if (r) { setAttach(""); await load(); onChanged(); }
  }
  async function detach(linkId?: number) {
    if (!linkId) return;
    if ((await run(() => api.del(`/catalog/product-modifier-groups/${linkId}/`), "Removed from this dish")) !== undefined) { await load(); onChanged(); }
  }
  const free = all.filter((g) => !groups.some((x) => x.id === g.id) && g.options.length > 0);

  return (
    <Modal open={open} onClose={onClose} title={`Options · ${product.name}`} width="max-w-lg">
      {loading ? <Spinner /> : (
        <div className="space-y-5">
          <section>
            <h3 className="mb-2 text-sm font-bold">On this dish</h3>
            {groups.length === 0 ? <p className="text-sm text-muted">No options yet. Customers get this dish exactly as listed.</p> : (
              <ul className="space-y-2">
                {groups.map((g) => (
                  <li key={g.id} className="rounded-xl border border-line p-3" data-testid={`attached-${g.id}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div><p className="font-semibold">{g.name} <Badge tone={g.required ? "warn" : "neutral"}>{g.required ? "Required" : "Optional"}</Badge></p>
                        <p className="mt-1 text-xs text-muted">{g.options.map((o) => `${o.name}${Number(o.price) ? ` (+${money(o.price, currency)})` : ""}`).join(" · ")}</p></div>
                      <button aria-label={`Remove ${g.name}`} onClick={() => detach(g.link_id)} className="text-muted hover:text-bad"><Trash2 className="h-4 w-4" /></button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {free.length > 0 && (
            <section className="flex items-end gap-2">
              <div className="flex-1"><Select label="Reuse an existing group" value={attach} onChange={(e) => setAttach(e.target.value)}><option value="">Choose…</option>{free.map((g) => <option key={g.id} value={g.id}>{g.name} ({g.options.length})</option>)}</Select></div>
              <Button variant="secondary" disabled={!attach} loading={busy} onClick={link}>Attach</Button>
            </section>
          )}

          <section className="space-y-3 rounded-2xl bg-sunken p-4">
            <h3 className="flex items-center gap-2 text-sm font-bold"><SlidersHorizontal className="h-4 w-4" />New option group</h3>
            <Input label="Group name" placeholder="e.g. Spice level, Extras, Drink" data-testid="grp-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <div className="flex flex-wrap gap-4 text-sm">
              <label className="flex items-center gap-2"><input type="checkbox" checked={form.required} data-testid="grp-required" onChange={(e) => setForm({ ...form, required: e.target.checked })} className="h-4 w-4 accent-[rgb(var(--brand))]" />Customer must choose</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={form.multi} data-testid="grp-multi" onChange={(e) => setForm({ ...form, multi: e.target.checked })} className="h-4 w-4 accent-[rgb(var(--brand))]" />Allow several</label>
              {form.multi && <label className="flex items-center gap-2">up to <input type="number" min={2} max={20} value={form.max} onChange={(e) => setForm({ ...form, max: e.target.value })} className="h-9 w-16 rounded-lg border border-line bg-surface px-2" /></label>}
            </div>
            <div className="space-y-2">
              {form.options.map((o, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Input aria-label={`Option ${i + 1} name`} placeholder={i === 0 ? "Mild" : "Option"} data-testid={`opt-name-${i}`} value={o.name} onChange={(e) => setForm({ ...form, options: form.options.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)) })} />
                  <div className="w-28 shrink-0"><Input aria-label={`Option ${i + 1} extra price`} type="number" step="any" placeholder="+ price" data-testid={`opt-price-${i}`} value={o.price} onChange={(e) => setForm({ ...form, options: form.options.map((x, j) => (j === i ? { ...x, price: e.target.value } : x)) })} /></div>
                  {form.options.length > 1 && <button aria-label="Remove option" onClick={() => setForm({ ...form, options: form.options.filter((_, j) => j !== i) })} className="text-muted hover:text-bad"><X className="h-4 w-4" /></button>}
                </div>
              ))}
              <button type="button" onClick={() => setForm({ ...form, options: [...form.options, { name: "", price: "" }] })} className="text-xs font-semibold text-brand"><Plus className="mr-1 inline h-3 w-3" />Add option</button>
            </div>
            <Button className="w-full" loading={busy} disabled={!valid} onClick={create} data-testid="grp-save">Save group on this dish</Button>
          </section>
        </div>
      )}
    </Modal>
  );
}
