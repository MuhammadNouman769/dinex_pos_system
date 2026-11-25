"use client";
import { useEffect, useState } from "react";
import { Gift, Mail } from "lucide-react";
import { Button, Card, Input, Switch, useAction, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";

interface S { enabled: boolean; spend_per_point: string; point_value: string; min_redeem: number; email_customers: boolean; reminders: boolean }

/** Loyalty rules: each restaurant chooses how many points customers earn and what a point is worth. */
export function LoyaltyCard() {
  const { currency, reload } = useAuth();
  const { run, busy } = useAction();
  const toast = useToast();
  const [s, setS] = useState<S | null>(null);
  useEffect(() => { api.get<S>("/loyalty/settings/").then(setS).catch((e) => toast.err(e.message)); }, [toast]);
  if (!s) return null;
  const sp = Number(s.spend_per_point) || 0, pv = Number(s.point_value) || 0;
  const valid = sp >= 1 && pv > 0 && s.min_redeem >= 1;
  const earnExample = sp > 0 ? Math.floor(1000 / sp) : 0;
  const save = async () => { const r = await run(() => api.patch<S>("/loyalty/settings/", s), "Loyalty rules saved"); if (r) { setS(r); reload(); } };
  const remind = async () => {
    const r = await run(() => api.post<{ sent: number; skipped: number }>("/loyalty/reminders/send/", {}));
    if (r) toast.ok(r.sent ? `Reminder sent to ${r.sent} customer${r.sent > 1 ? "s" : ""}` : "No one needs a reminder right now");
  };

  return (
    <Card className="p-5" >
      <div data-testid="loyalty-card">
        <div className="flex items-start justify-between gap-3">
          <div><h3 className="flex items-center gap-2 font-display text-lg font-bold"><Gift className="h-5 w-5 text-brand" />Loyalty points</h3>
            <p className="mt-1 text-sm text-muted">Reward customers who come back. Cashiers type the customer&apos;s phone number at the POS, and points are added when the bill is paid.</p></div>
          <Switch checked={s.enabled} onChange={(v) => setS({ ...s, enabled: v })} label="Loyalty points" />
        </div>
        {s.enabled && (
          <div className="mt-4 space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <Input label={`Spend (${currency}) for 1 point`} type="number" min={1} data-testid="loy-spend" value={s.spend_per_point} onChange={(e) => setS({ ...s, spend_per_point: e.target.value })} />
              <Input label={`1 point is worth (${currency})`} type="number" min={0.01} step="any" data-testid="loy-value" value={s.point_value} onChange={(e) => setS({ ...s, point_value: e.target.value })} />
              <Input label="Use points from" hint="points" type="number" min={1} data-testid="loy-min" value={s.min_redeem} onChange={(e) => setS({ ...s, min_redeem: Number(e.target.value) })} />
            </div>
            {valid && (
              <p className="rounded-xl bg-brand-soft p-3 text-sm text-brand" data-testid="loy-preview">
                A {money(1000, currency)} bill earns <b>{earnExample} points</b>. {s.min_redeem} points are worth <b>{money(s.min_redeem * pv, currency)}</b>. That gives back about <b>{sp > 0 ? Math.round((pv / sp) * 1000) / 10 : 0}%</b> of what customers spend.
              </p>
            )}
            <div className="space-y-2.5 rounded-2xl border border-line p-3.5">
              <Switch checked={s.email_customers} onChange={(v) => setS({ ...s, email_customers: v })} label="Email customers when they earn points (needs their email)" />
              <Switch checked={s.reminders} onChange={(v) => setS({ ...s, reminders: v })} label="Remind customers of their points once or twice a week" />
              <p className="flex items-start gap-2 text-xs text-muted"><Mail className="mt-0.5 h-3.5 w-3.5 shrink-0" />Reminders go out automatically when the server schedule is set (see README). You can also send them now.</p>
              <Button variant="secondary" size="sm" loading={busy} onClick={remind} data-testid="loy-remind">Send reminders now</Button>
            </div>
          </div>
        )}
        <Button className="mt-4" loading={busy} disabled={s.enabled && !valid} onClick={save} data-testid="loy-save">Save loyalty rules</Button>
      </div>
    </Card>
  );
}
