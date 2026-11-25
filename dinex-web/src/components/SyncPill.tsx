"use client";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, CloudOff, Printer, RefreshCw, Trash2, Wifi } from "lucide-react";
import { Badge, Button, Modal, cn, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/api";
import { localOrder } from "@/lib/offline/bill";
import { flush, onSynced, outbox, useOutbox, type OutboxEntry } from "@/lib/offline/outbox";
import { isOnline, useOnline } from "@/lib/offline/status";
import { printReceipt } from "@/lib/receipt";

/** Runs the background sync: on start, when the internet returns, when the tab is shown, and every 15 s while something waits. */
export function useSyncEngine() {
  const { me } = useAuth();
  const toast = useToast();
  const orgId = me?.organization?.id;
  const online = useOnline();
  const box = useOutbox(orgId);
  const [syncing, setSyncing] = useState(false);

  const sync = useCallback(async () => {
    if (!orgId || !isOnline()) return;
    setSyncing(true);
    try { await flush(orgId); } finally { setSyncing(false); box.refresh(); }
  }, [orgId, box]);

  useEffect(() => { if (online && box.pending > 0) void sync(); }, [online, box.pending, sync]);
  useEffect(() => {
    if (!orgId) return;
    const t = setInterval(() => { if (box.pending > 0) void sync(); }, 15000);
    const vis = () => { if (document.visibilityState === "visible" && box.pending > 0) void sync(); };
    document.addEventListener("visibilitychange", vis);
    return () => { clearInterval(t); document.removeEventListener("visibilitychange", vis); };
  }, [orgId, box.pending, sync]);
  useEffect(() => onSynced(({ synced, failed }) => {
    if (synced) toast.ok(`${synced} offline order${synced === 1 ? "" : "s"} synced`);
    if (failed) toast.err(`${failed} order${failed === 1 ? "" : "s"} could not be synced. Open the sync list.`);
  }), [toast]);

  return { ...box, online, syncing, sync };
}

export function SyncPill() {
  const s = useSyncEngine();
  const [open, setOpen] = useState(false);
  const tone = s.failed > 0 ? "bad" : !s.online ? "warn" : s.pending > 0 ? "brand" : "good";
  const label = s.failed > 0 ? `${s.failed} need attention` : !s.online ? (s.pending ? `Offline · ${s.pending} saved` : "Offline") : s.pending > 0 ? (s.syncing ? "Syncing…" : `${s.pending} to sync`) : "Online";
  const Icon = s.failed > 0 ? AlertTriangle : !s.online ? CloudOff : s.pending > 0 ? RefreshCw : Wifi;
  // When everything is fine the pill stays small (icon only on phones) so it does not crowd the top bar.
  const quiet = tone === "good";
  return (
    <>
      <button onClick={() => setOpen(true)} aria-label={`Connection: ${label}`} data-testid="sync-pill"
        className={cn("inline-flex min-h-[40px] items-center gap-2 rounded-xl border px-3 text-sm font-semibold shadow-sm transition",
          tone === "good" && "border-line bg-surface text-good", tone === "warn" && "border-warn/40 bg-warn-soft text-warn",
          tone === "bad" && "border-bad/40 bg-bad-soft text-bad", tone === "brand" && "border-brand/40 bg-brand-soft text-brand")}>
        <Icon className={cn("h-4 w-4", s.syncing && "animate-spin")} /><span className={cn(quiet && "hidden sm:inline")}>{label}</span>
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="Connection & sync" width="max-w-lg">
        <SyncCenter online={s.online} rows={s.rows} syncing={s.syncing} onSync={s.sync} onChanged={s.refresh} />
      </Modal>
    </>
  );
}

/** Thin bar under the top bar while offline. */
export function OfflineBar() {
  const online = useOnline();
  const { me } = useAuth();
  const { pending } = useOutbox(me?.organization?.id);
  if (online) return null;
  return (
    <div role="status" className="flex items-center gap-3 bg-warn-soft px-4 py-2 text-sm font-medium text-warn md:px-8">
      <CloudOff className="h-4 w-4 shrink-0" />
      <span className="flex-1">You are offline. POS orders are saved on this device{pending ? ` (${pending} waiting)` : ""} and send automatically when the internet is back. Other changes need internet.</span>
    </div>
  );
}

export function SyncCenter({ online, rows, syncing, onSync, onChanged }: { online: boolean; rows: OutboxEntry[]; syncing: boolean; onSync: () => void; onChanged: () => void }) {
  const { me, location, currency } = useAuth();
  const toast = useToast();
  const retry = async (e: OutboxEntry) => { await outbox.update({ ...e, status: "queued", error: undefined }); onChanged(); onSync(); };
  const discard = async (e: OutboxEntry) => { if (confirm(`Discard order ${e.display.number}? It will NOT be sent to the server.`)) { await outbox.remove(e.client_uuid); onChanged(); } };
  const print = (e: OutboxEntry) => { if (!printReceipt(localOrder(e), { business: me?.organization?.name ?? "", branding: me?.organization?.branding, loyalty: me?.organization?.loyalty, location: location?.name ?? "", address: location?.address, currency })) toast.err("Allow pop-ups to print the bill."); };
  return (
    <div className="space-y-4">
      <div className={cn("flex items-center gap-3 rounded-2xl p-4 text-sm", online ? "bg-good-soft text-good" : "bg-warn-soft text-warn")}>
        {online ? <CheckCircle2 className="h-5 w-5 shrink-0" /> : <CloudOff className="h-5 w-5 shrink-0" />}
        <p className="font-medium">{online ? "Connected to the server." : "No internet. You can keep taking POS orders: they are saved on this device and sent automatically when the internet returns."}</p>
      </div>
      {rows.length === 0 ? <p className="py-6 text-center text-sm text-muted">Nothing is waiting. All orders are on the server.</p> : (
        <>
          <ul className="space-y-2">
            {rows.map((e) => (
              <li key={e.client_uuid} className="rounded-2xl border border-line p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0"><p className="font-bold">{e.display.number} <span className="font-medium text-muted">· {e.display.type_label}{e.table_label ? ` · ${e.table_label}` : ""}</span></p>
                    <p className="truncate text-xs text-muted">{e.display.lines.map((l) => `${l.qty}× ${l.name}`).join(", ")}</p></div>
                  <div className="text-right"><p className="num font-bold">{money(e.display.total, currency)}</p>
                    <Badge tone={e.status === "failed" ? "bad" : e.status === "blocked" ? "warn" : "brand"}>{e.status === "failed" ? "Needs attention" : e.status === "blocked" ? "On hold" : e.payload.payments.length ? "Paid · waiting" : "Waiting"}</Badge></div>
                </div>
                {e.error && <p className="mt-2 rounded-lg bg-sunken p-2 text-xs text-bad">{e.error}</p>}
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" onClick={() => print(e)}><Printer className="h-3.5 w-3.5" />Bill</Button>
                  {e.status !== "queued" && <Button size="sm" variant="secondary" onClick={() => retry(e)}><RefreshCw className="h-3.5 w-3.5" />Try again</Button>}
                  {e.status === "failed" && <Button size="sm" variant="ghost" onClick={() => discard(e)}><Trash2 className="h-3.5 w-3.5" />Discard</Button>}
                </div>
              </li>
            ))}
          </ul>
          <Button className="w-full" disabled={!online || syncing} loading={syncing} onClick={onSync}><RefreshCw className="h-4 w-4" />Sync now</Button>
        </>
      )}
    </div>
  );
}

/** Used by the Orders page. */
export function useOutboxFor() { const { me } = useAuth(); return useOutbox(me?.organization?.id); }
