"use client";
import { useEffect, useState } from "react";
import { Banknote, CheckCircle2, CreditCard, Landmark, Smartphone } from "lucide-react";
import { Button, Input, Modal, cn } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/api";
import { outbox, type OutboxEntry, type SyncPayment } from "@/lib/offline/outbox";

const METHODS: { id: SyncPayment["method"]; label: string; icon: typeof Banknote }[] = [
  { id: "CASH", label: "Cash", icon: Banknote }, { id: "CARD", label: "Card", icon: CreditCard },
  { id: "WALLET", label: "JazzCash / Easypaisa", icon: Smartphone }, { id: "BANK", label: "Bank transfer", icon: Landmark },
];

/** Take payment for an order that is still only on this device. The payment is sent together with the order. */
export function LocalPayModal({ entry, open, onClose, onSaved }: { entry: OutboxEntry | null; open: boolean; onClose: () => void; onSaved: (e: OutboxEntry) => void }) {
  const { currency } = useAuth();
  const [method, setMethod] = useState<SyncPayment["method"]>("CASH");
  const [tendered, setTendered] = useState("");
  const [ref, setRef] = useState("");
  const [saved, setSaved] = useState<{ change: number } | null>(null);
  useEffect(() => { if (open) { setMethod("CASH"); setTendered(""); setRef(""); setSaved(null); } }, [open]);
  if (!entry) return null;
  const total = entry.display.total;
  const change = method === "CASH" && Number(tendered) > total ? Number(tendered) - total : 0;
  const quick = Array.from(new Set([total, Math.ceil(total / 100) * 100, Math.ceil(total / 500) * 500, Math.ceil(total / 1000) * 1000])).filter((v) => v >= total).slice(0, 4);

  async function save() {
    const p: SyncPayment = { method, amount: total.toFixed(2), ...(method === "CASH" && tendered ? { tendered: Number(tendered).toFixed(2) } : {}), ...(method !== "CASH" && ref ? { reference: ref } : {}) };
    const next = { ...entry!, payload: { ...entry!.payload, payments: [p] } };
    await outbox.update(next);
    onSaved(next);
    setSaved({ change });
  }

  return (
    <Modal open={open} onClose={onClose} title={`Payment · ${entry.display.number}`} width="max-w-md">
      {saved ? (
        <div className="text-center">
          <CheckCircle2 className="mx-auto h-14 w-14 text-good" />
          <p className="mt-3 text-xl font-bold">Payment recorded</p>
          <p className="text-sm text-muted">It will be added to your shift when the order syncs.</p>
          {saved.change > 0 && <div className="mx-auto mt-4 w-fit rounded-2xl bg-warn-soft px-6 py-3"><p className="text-xs font-semibold text-warn">Give change</p><p className="num text-3xl font-bold text-warn">{money(saved.change, currency)}</p></div>}
          <Button className="mt-5 w-full" onClick={onClose}>Done</Button>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="rounded-2xl bg-sunken p-4 text-center"><p className="text-xs font-semibold text-muted">Amount due</p><p className="num text-4xl font-bold tracking-tight">{money(total, currency)}</p></div>
          <div className="grid grid-cols-2 gap-2">
            {METHODS.map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setMethod(id)} className={cn("flex min-h-[52px] items-center gap-2 rounded-xl border px-3 text-left text-sm font-semibold transition", method === id ? "border-brand bg-brand-soft text-brand" : "border-line hover:bg-sunken")}>
                <Icon className="h-5 w-5 shrink-0" /><span className="leading-tight">{label}</span>
              </button>
            ))}
          </div>
          {method === "CASH" ? (
            <div className="space-y-3">
              <Input label="Cash received" type="number" min="0" step="any" inputMode="decimal" value={tendered} onChange={(e) => setTendered(e.target.value)} placeholder="Optional: to work out the change" />
              <div className="flex flex-wrap gap-2">{quick.map((v) => <button key={v} onClick={() => setTendered(String(v))} className="min-h-[40px] rounded-full border border-line px-3.5 text-sm font-semibold hover:border-brand hover:text-brand">{v === total ? "Exact" : v.toLocaleString()}</button>)}</div>
              {change > 0 && <div className="flex items-center justify-between rounded-xl bg-warn-soft px-4 py-3 text-warn"><span className="text-sm font-semibold">Change to give</span><span className="num text-xl font-bold">{money(change, currency)}</span></div>}
            </div>
          ) : <Input label="Reference (optional)" placeholder={method === "CARD" ? "Slip / approval no." : "Transaction id"} value={ref} onChange={(e) => setRef(e.target.value)} />}
          <Button size="lg" className="w-full" disabled={method === "CASH" && !!tendered && Number(tendered) < total} onClick={save}>Receive {money(total, currency)}</Button>
        </div>
      )}
    </Modal>
  );
}
