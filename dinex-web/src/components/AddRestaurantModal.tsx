"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button, Input, Modal, Select, useAction, useToast } from "@/components/ui";
import { genPassword } from "@/components/Platform";
import { api } from "@/lib/api";
import type { PlanRow, RestaurantRow } from "@/lib/types";

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "").slice(0, 20);

export function AddRestaurantModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated?: () => void }) {
  const router = useRouter();
  const toast = useToast();
  const { run, busy } = useAction();
  const [plans, setPlans] = useState<PlanRow[]>([]);
  const [f, setF] = useState({ name: "", first: "", last: "", username: "", email: "", password: genPassword(), branch: "Main branch", address: "", plan: "starter", trial: "14", activate: false });
  const [touchedUser, setTouchedUser] = useState(false);
  const [created, setCreated] = useState<{ row: RestaurantRow; username: string; password: string } | null>(null);

  useEffect(() => { if (open) api.get<PlanRow[]>("/platform/plans/").then((p) => setPlans(p.filter((x) => x.is_active))).catch(() => undefined); }, [open]);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }));
  const setName = (v: string) => setF((s) => ({ ...s, name: v, username: touchedUser ? s.username : slug(v) }));

  const valid = f.name.trim() && f.first.trim() && f.last.trim() && f.username.trim() && f.email.includes("@") && f.password.length >= 8 && f.address.trim().length >= 5;

  async function save() {
    const row = await run(() => api.post<RestaurantRow>("/platform/restaurants/", {
      organization: { name: f.name.trim(), currency: "PKR", timezone: "Asia/Karachi" },
      owner: { username: f.username.trim(), email: f.email.trim(), password: f.password, first_name: f.first.trim(), last_name: f.last.trim() },
      location: { name: f.branch.trim() || "Main branch", address: f.address.trim() },
      plan: f.plan, trial_days: Number(f.trial) || 14, activate: f.activate,
    }));
    if (row) { setCreated({ row, username: f.username.trim(), password: f.password }); onCreated?.(); }
  }
  const close = () => { setCreated(null); setTouchedUser(false); setF((s) => ({ ...s, name: "", first: "", last: "", username: "", email: "", address: "", password: genPassword(), activate: false })); onClose(); };

  return (
    <Modal open={open} onClose={close} title={created ? "Restaurant created" : "Add restaurant"} width="max-w-xl">
      {created ? (
        <div className="space-y-4">
          <p className="text-sm text-muted"><b>{created.row.name}</b> is ready. Give these login details to the owner. The password is shown only now.</p>
          <div className="rounded-2xl bg-sunken p-4 font-mono text-sm"><p>Username: <b>{created.username}</b></p><p>Password: <b>{created.password}</b></p></div>
          <div className="grid grid-cols-2 gap-2">
            <Button variant="secondary" onClick={() => { navigator.clipboard?.writeText(`DineX login\nUsername: ${created.username}\nPassword: ${created.password}`); toast.ok("Copied"); }}>Copy details</Button>
            <Button onClick={() => { const id = created.row.id; close(); router.push(`/admin/restaurants/${id}`); }}>Open restaurant</Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <Input label="Restaurant name" value={f.name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Karachi Grill" autoFocus />
          <div className="grid grid-cols-2 gap-3"><Input label="Owner first name" value={f.first} onChange={set("first")} /><Input label="Owner last name" value={f.last} onChange={set("last")} /></div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Login username" value={f.username} onChange={(e) => { setTouchedUser(true); set("username")(e); }} />
            <Input label="Owner email" type="email" value={f.email} onChange={set("email")} />
          </div>
          <div className="flex items-end gap-2">
            <div className="flex-1"><Input label="Temporary password" value={f.password} onChange={set("password")} className="font-mono" /></div>
            <Button variant="secondary" aria-label="Generate password" onClick={() => setF((s) => ({ ...s, password: genPassword() }))}><RefreshCw className="h-4 w-4" /></Button>
          </div>
          <div className="grid grid-cols-2 gap-3"><Input label="First branch name" value={f.branch} onChange={set("branch")} /><Input label="Branch address" value={f.address} onChange={set("address")} placeholder="Street, area, city" /></div>
          <div className="grid grid-cols-2 gap-3">
            <Select label="Plan" value={f.plan} onChange={set("plan")}>{plans.map((p) => <option key={p.code} value={p.code}>{p.name} · Rs {Number(p.price_monthly).toLocaleString()}/mo</option>)}</Select>
            <Input label="Free trial (days)" type="number" min="1" max="90" value={f.trial} onChange={set("trial")} disabled={f.activate} />
          </div>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.activate} onChange={(e) => setF((s) => ({ ...s, activate: e.target.checked }))} className="h-4 w-4 accent-[rgb(var(--brand))]" />Skip the trial: start billing now (issues the first invoice)</label>
          <Button size="lg" className="w-full" loading={busy} disabled={!valid} onClick={save}>Create restaurant</Button>
        </div>
      )}
    </Modal>
  );
}
