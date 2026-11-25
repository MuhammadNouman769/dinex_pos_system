"use client";
import { useEffect, useState } from "react";
import { Check, Pencil, Plus } from "lucide-react";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Spinner, Textarea, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import type { PlanRow } from "@/lib/types";

const blank = { code: "", name: "", description: "", price_monthly: "", max_locations: "1", max_users: "5", features: "", is_active: true };

export default function PlansPage() {
  const { me } = useAuth();
  const { run, busy } = useAction();
  const [plans, setPlans] = useState<PlanRow[] | null>(null);
  const [edit, setEdit] = useState<PlanRow | "new" | null>(null);
  const [f, setF] = useState(blank);
  const load = () => api.get<PlanRow[]>("/platform/plans/").then(setPlans);
  useEffect(() => { if (me?.role === "PLATFORM") load(); }, [me]);
  const set = (k: keyof typeof blank) => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }));

  if (me && me.role !== "PLATFORM") return <EmptyState title="DineX Admin is for XverLabs staff" />;
  if (!plans) return <Spinner />;

  const open = (p: PlanRow | "new") => {
    setF(p === "new" ? blank : { code: p.code, name: p.name, description: p.description, price_monthly: String(Number(p.price_monthly)), max_locations: String(p.max_locations), max_users: String(p.max_users), features: p.features.join("\n"), is_active: p.is_active });
    setEdit(p);
  };
  async function save() {
    const body = { ...f, price_monthly: f.price_monthly, max_locations: Number(f.max_locations), max_users: Number(f.max_users), features: f.features.split("\n").map((x) => x.trim()).filter(Boolean) };
    const r = await run(() => edit === "new" ? api.post("/platform/plans/", body) : api.patch(`/platform/plans/${(edit as PlanRow).id}/`, body), "Plan saved");
    if (r) { setEdit(null); load(); }
  }

  return (
    <>
      <PageHeader title="Plans" subtitle="What you sell. Changing a price does not affect existing invoices." actions={<Button onClick={() => open("new")}><Plus className="h-4 w-4" />New plan</Button>} />
      <div className="grid gap-5 md:grid-cols-3">
        {plans.map((p) => (
          <Card key={p.id} className={`flex flex-col p-6 ${!p.is_active ? "opacity-60" : ""}`}>
            <div className="flex items-start justify-between"><div><h2 className="text-xl font-bold">{p.name}</h2><p className="mt-0.5 text-sm text-muted">{p.description}</p></div>{!p.is_active && <Badge>Hidden</Badge>}</div>
            <p className="mt-4 text-3xl font-bold tracking-tight">{money(p.price_monthly)}<span className="text-sm font-medium text-muted"> / month</span></p>
            <p className="mt-1 text-sm text-muted">{p.max_locations} branch{p.max_locations > 1 ? "es" : ""} · {p.max_users} staff accounts</p>
            <ul className="my-4 flex-1 space-y-2 text-sm">{p.features.map((x) => <li key={x} className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-good" />{x}</li>)}</ul>
            <div className="flex items-center justify-between border-t border-line pt-4"><span className="text-sm text-muted">{p.restaurants} restaurant{p.restaurants === 1 ? "" : "s"}</span><Button size="sm" variant="secondary" onClick={() => open(p)}><Pencil className="h-3.5 w-3.5" />Edit</Button></div>
          </Card>
        ))}
      </div>

      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit === "new" ? "New plan" : `Edit ${f.name}`}><div className="space-y-4">
        <div className="grid grid-cols-2 gap-3"><Input label="Name" value={f.name} onChange={set("name")} /><Input label="Code" value={f.code} onChange={set("code")} disabled={edit !== "new"} placeholder="e.g. growth" hint={edit === "new" ? "Lowercase, no spaces" : undefined} /></div>
        <Input label="Short description" value={f.description} onChange={set("description")} />
        <div className="grid grid-cols-3 gap-3"><Input label="Price / month" type="number" min="0" value={f.price_monthly} onChange={set("price_monthly")} /><Input label="Branches" type="number" min="1" value={f.max_locations} onChange={set("max_locations")} /><Input label="Staff accounts" type="number" min="1" value={f.max_users} onChange={set("max_users")} /></div>
        <Textarea label="Features (one per line)" rows={4} value={f.features} onChange={set("features")} />
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.is_active} onChange={(e) => setF((s) => ({ ...s, is_active: e.target.checked }))} className="h-4 w-4 accent-[rgb(var(--brand))]" />Available to new restaurants</label>
        <Button className="w-full" size="lg" loading={busy} disabled={!f.name.trim() || !f.price_monthly} onClick={save}>Save plan</Button></div></Modal>
    </>
  );
}
