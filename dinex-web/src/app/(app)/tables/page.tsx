"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Armchair, CalendarClock, ClipboardList, Move, Plus, RotateCcw, Sparkles, Users } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { FloorCanvas } from "@/components/FloorCanvas";
import { Legend, STATUS_STYLE, TableVisual } from "@/components/TableVisual";
import { Badge, Button, EmptyState, Modal, PageHeader, Spinner, cn, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import { onSynced } from "@/lib/offline/outbox";
import type { Floor, Order, TableT } from "@/lib/types";

const ACTIVE = ["PENDING", "CONFIRMED", "PREPARING", "READY", "OUT_FOR_DELIVERY"];

export default function TablesPage() {
  const { me, location, currency } = useAuth();
  const { run, busy } = useAction();
  const [floors, setFloors] = useState<Floor[]>([]);
  const [tables, setTables] = useState<TableT[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [floor, setFloor] = useState<number | "none" | null>(null);
  const [sel, setSel] = useState<TableT | null>(null);
  const [editing, setEditing] = useState(false);
  const [booked, setBooked] = useState<{ table: number | null; starts_at: string; guest_name: string }[]>([]);

  const load = useCallback(async () => {
    if (!location) return;
    const [f, t, o] = await Promise.all([
      api.list<Floor>("/orders/floors/", { location: location.id }), api.list<TableT>("/orders/tables/", { location: location.id }),
      api.list<Order>("/orders/", { location: location.id }).catch(() => [] as Order[]),
    ]);
    setBooked(await api.list<{ table: number | null; starts_at: string; guest_name: string; status: string }>("/operations/reservations/", { location: location.id, upcoming: 1 }).catch(() => []));
    setFloors(f); setTables(t.filter((x) => x.is_active !== false)); setOrders(o.filter((x) => ACTIVE.includes(x.status) && x.table)); setLoading(false);
  }, [location]);
  useEffect(() => { load().catch(() => setLoading(false)); const i = setInterval(() => load().catch(() => {}), 15000); return () => clearInterval(i); }, [load]);
  useEffect(() => onSynced(() => { load().catch(() => {}); }), [load]);

  const groups = useMemo(() => [
    ...floors.map((f) => ({ id: f.id as number | "none", name: f.name, items: tables.filter((t) => t.floor === f.id) })),
    ...(tables.some((t) => !t.floor) ? [{ id: "none" as const, name: "Other", items: tables.filter((t) => !t.floor) }] : []),
  ], [floors, tables]);
  const current = groups.find((g) => g.id === floor) ?? groups[0];

  if (me && !me.organization) return <PlatformNotice />;
  if (loading) return <Spinner label="Loading tables…" />;

  const count = (s: string) => current?.items.filter((t) => t.status === s).length ?? 0;
  const seatsFree = current?.items.filter((t) => t.status === "AVAILABLE").reduce((a, t) => a + t.capacity, 0) ?? 0;
  const orderOf = (t: TableT) => orders.filter((o) => o.table === t.id);
  const canEdit = !!me?.can_view_reports;
  const moveTable = async (t: TableT, x: number, y: number) => {
    setTables((all) => all.map((q) => (q.id === t.id ? { ...q, pos_x: x, pos_y: y } : q)));
    await run(() => api.patch(`/orders/tables/${t.id}/`, { pos_x: x, pos_y: y }));
  };
  const resetLayout = async () => {
    if (!current) return;
    await run(() => Promise.all(current.items.map((t) => api.patch(`/orders/tables/${t.id}/`, { pos_x: null, pos_y: null }))), "Layout reset");
    load();
  };
  const setStatus = async (t: TableT, status: string, msg: string) => {
    const r = await run(() => api.patch<TableT>(`/orders/tables/${t.id}/`, { status }), msg);
    if (r !== undefined) { setSel(null); load(); }
  };

  return (
    <>
      <PageHeader title="Tables" subtitle={`${location?.name} · live floor plan`} actions={<><Link href="/reservations"><Button variant="secondary" data-testid="to-reservations"><CalendarClock className="h-4 w-4" />Bookings{booked.length > 0 ? ` (${booked.length})` : ""}</Button></Link><Link href="/setup"><Button variant="secondary"><Plus className="h-4 w-4" />Add / edit tables</Button></Link></>} />
      {groups.length === 0 ? (
        <EmptyState icon={<Armchair className="h-8 w-8" />} title="No tables yet" hint="Add floors and tables in Setup, choose the shape and seats, then they appear here."
          action={<Link href="/setup"><Button>Go to Setup</Button></Link>} />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="scroll-thin -mx-1 flex gap-2 overflow-x-auto px-1">
              {groups.map((g) => (
                <button key={String(g.id)} onClick={() => setFloor(g.id)} data-testid={`floor-${g.id}`}
                  className={cn("min-h-[44px] shrink-0 rounded-full border px-4 text-sm font-semibold transition", current?.id === g.id ? "border-brand bg-brand text-white dark:text-[#04201a]" : "border-line bg-surface text-muted hover:text-ink")}>
                  {g.name} <span className="ml-1 text-xs opacity-70">{g.items.length}</span>
                </button>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-3">
              {canEdit && (editing
                ? <><Button size="sm" variant="ghost" onClick={resetLayout} data-testid="reset-layout"><RotateCcw className="h-4 w-4" />Auto-arrange</Button><Button size="sm" onClick={() => setEditing(false)} data-testid="done-layout">Done</Button></>
                : <Button size="sm" variant="secondary" onClick={() => setEditing(true)} data-testid="edit-layout"><Move className="h-4 w-4" />Rearrange</Button>)}
              <Legend />
            </div>
          </div>
          {editing && <p className="mb-3 rounded-xl bg-brand-soft px-3 py-2 text-sm font-medium text-brand">Drag each table to where it really is in your restaurant. It saves automatically.</p>}
          <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Mini label="Available" value={count("AVAILABLE")} tone="AVAILABLE" />
            <Mini label="Occupied" value={count("OCCUPIED")} tone="OCCUPIED" />
            <Mini label="Reserved" value={count("RESERVED")} tone="RESERVED" />
            <Mini label="Free seats" value={seatsFree} />
          </div>
          <div className="rounded-3xl border border-line bg-surface p-4 shadow-card sm:p-8" style={{ backgroundImage: "radial-gradient(rgb(var(--line)) 1px, transparent 1px)", backgroundSize: "18px 18px" }} data-testid="floor-plan">
            {current?.items.length ? (
              <FloorCanvas tables={current.items} editing={editing} sel={sel?.id ?? null} onOpen={setSel} onMove={moveTable}
                sub={(t) => { const o = orderOf(t)[0]; return o ? money(o.total_amount, currency) : `${t.capacity} seats`; }} />
            ) : <p className="py-16 text-center text-sm text-muted">No tables on this floor.</p>}
          </div>
        </>
      )}

      <Modal open={!!sel} onClose={() => setSel(null)} title={sel ? `Table ${sel.table_number}` : ""} width="max-w-md">
        {sel && (() => {
          const os = orderOf(sel);
          const st = STATUS_STYLE[sel.status] ?? STATUS_STYLE.AVAILABLE;
          return (
            <div className="space-y-4">
              <div className="grid place-items-center rounded-2xl bg-sunken py-4"><TableVisual shape={sel.shape ?? "SQUARE"} seats={sel.capacity} label={sel.table_number} status={sel.status} scale={1.1} /></div>
              <div className="flex items-center justify-between text-sm">
                <span className="inline-flex items-center gap-1.5 font-semibold"><Users className="h-4 w-4 text-muted" />{sel.capacity} seats</span>
                <Badge tone={sel.status === "AVAILABLE" ? "good" : sel.status === "OCCUPIED" ? "bad" : "warn"}>{st.label}</Badge>
              </div>
              {booked.filter((b) => b.table === sel.id).map((b, k) => <p key={k} className="rounded-xl bg-brand-soft px-3 py-2 text-sm font-medium text-brand" data-testid="table-booking">Booked {new Date(b.starts_at).toLocaleString("en-PK", { weekday: "short", hour: "numeric", minute: "2-digit" })} · {b.guest_name}</p>)}
              {os.map((o) => (
                <Link key={o.id} href="/orders" className="flex items-center justify-between rounded-xl border border-line p-3 text-sm hover:bg-sunken">
                  <span><b>{o.order_number}</b><br /><span className="text-xs text-muted">{o.items.length} items · {o.status_display}{o.waiter_name ? ` · ${o.waiter_name}` : ""}</span></span>
                  <span className="num font-bold">{money(o.total_amount, currency)}</span>
                </Link>
              ))}
              <div className="grid gap-2">
                {(sel.status === "AVAILABLE" || sel.status === "RESERVED") && me?.can_operate_pos && (
                  <Link href={`/pos?table=${sel.id}`}><Button size="lg" className="w-full"><ClipboardList className="h-5 w-5" />Start order for this table</Button></Link>
                )}
                {sel.status === "OCCUPIED" && <Link href="/orders"><Button size="lg" variant="secondary" className="w-full"><ClipboardList className="h-5 w-5" />Open orders</Button></Link>}
                {sel.status === "AVAILABLE" && <Button variant="secondary" loading={busy} onClick={() => setStatus(sel, "RESERVED", "Table reserved")}><CalendarClock className="h-4 w-4" />Mark as reserved</Button>}
                {sel.status === "RESERVED" && <Button variant="secondary" loading={busy} onClick={() => setStatus(sel, "AVAILABLE", "Reservation cleared")}>Cancel reservation</Button>}
                {sel.status === "CLEANING" && <Button loading={busy} onClick={() => setStatus(sel, "AVAILABLE", "Table is ready")}><Sparkles className="h-4 w-4" />Table is clean · make available</Button>}
              </div>
            </div>
          );
        })()}
      </Modal>
    </>
  );
}

function Mini({ label, value, tone }: { label: string; value: number; tone?: string }) {
  const c = tone ? STATUS_STYLE[tone].c : "var(--ink)";
  return <div className="rounded-2xl border border-line bg-surface p-3.5"><p className="text-xs font-semibold text-muted">{label}</p><p className="num mt-0.5 text-2xl font-extrabold" style={{ color: `rgb(${c})` }}>{value}</p></div>;
}
