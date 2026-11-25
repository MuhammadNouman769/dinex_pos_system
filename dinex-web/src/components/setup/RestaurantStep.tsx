"use client";
import { useEffect, useState } from "react";
import { Button, Card, Input, Select, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { LoyaltyCard } from "@/components/setup/LoyaltyCard";
import { BrandingCard } from "@/components/setup/BrandingCard";

const POLICIES = [
  { id: "ALLOW", label: "Always allow the sale", hint: "Stock may go below zero. Best while you are still setting up recipes." },
  { id: "WARN", label: "Allow, but warn", hint: "The sale goes through and the cashier sees a low-stock warning." },
  { id: "BLOCK", label: "Block the sale", hint: "Orders are refused when an ingredient would run out." },
] as const;

export function RestaurantStep() {
  const { me, location, reload } = useAuth();
  const { run, busy } = useAction();
  const [f, setF] = useState({ name: "", address: "", tax_rate: "10", service_charge_rate: "0", inventory_policy: "ALLOW" });

  useEffect(() => {
    if (location) setF({ name: location.name, address: location.address, tax_rate: String(Number(location.tax_rate)), service_charge_rate: String(Number(location.service_charge_rate)), inventory_policy: location.inventory_policy });
  }, [location]);

  if (!location) return null;
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }));
  const policy = POLICIES.find((p) => p.id === f.inventory_policy)!;

  async function save() {
    const r = await run(() => api.patch(`/organizations/locations/${location!.id}/`, f), "Restaurant settings saved");
    if (r !== undefined) reload();
  }

  return (
    <div className="space-y-6">
    <Card className="max-w-3xl space-y-5 p-6">
      <div><h2 className="text-lg font-bold">Restaurant details</h2><p className="text-sm text-muted">These appear on the bill and are used to calculate totals.</p></div>
      <Input label="Branch name" value={f.name} onChange={set("name")} />
      <Input label="Address" value={f.address} onChange={set("address")} />
      <div className="grid grid-cols-2 gap-4">
        <Input label="Sales tax %" type="number" step="0.01" min="0" max="100" value={f.tax_rate} onChange={set("tax_rate")} hint="e.g. 16 for 16%" />
        <Input label="Service charge %" type="number" step="0.01" min="0" max="100" value={f.service_charge_rate} onChange={set("service_charge_rate")} hint="0 if you do not charge one" />
      </div>
      <Select label="When an ingredient runs out" value={f.inventory_policy} onChange={set("inventory_policy")} hint={policy.hint}>
        {POLICIES.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
      </Select>
      <Button loading={busy} onClick={save}>Save</Button>
    </Card>
    {me?.membership_role !== "STAFF" && <BrandingCard />}
    {me?.is_owner && <LoyaltyCard />}
    </div>
  );
}
