"use client";
import { useCallback, useEffect, useState } from "react";
import { CalendarClock, ChevronLeft, ChevronRight, Phone, Plus, Users } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { TablePicker } from "@/components/TablePicker";
import { Badge, Button, Card, EmptyState, Input, Modal, PageHeader, Spinner, cn, useAction, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import type { Reservation, TableT } from "@/lib/types";

const TONE = { BOOKED: "brand", SEATED: "good", COMPLETED: "neutral", CANCELLED: "bad", NO_SHOW: "warn" } as const;
const LABEL = { BOOKED: "Booked", SEATED: "Seated", COMPLETED: "Completed", CANCELLED: "Cancelled", NO_SHOW: "No-show" } as const;
const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const hhmm = (iso: string) => new Date(iso).toLocaleTimeString("en-PK", { hour: "numeric", minute: "2-digit" });

export default function ReservationsPage() {
  const { me, location } = useAuth();
  const toast = useToast();
  const { run, busy } = useAction();
  const [day, setDay] = useState(() => new Date());
  const [rows, setRows] = useState<Reservation[]>([]);
  const [tables, setTables] = useState<TableT[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [pick, setPick] = useState(false);
  const blank = { guest_name: "", phone: "", party_size: "2", time: "20:00", duration: "90", table: null as TableT | null, notes: "" };
  const [f, setF] = useState(blank);

  const load = useCallback(async () => {
    if (!location) return;
    const [r, t] = await Promise.all([api.list<Reservation>("/operations/reservations/", { location: location.id, date: ymd(day) }), api.list<TableT>("/orders/tables/", { location: location.id })]);
    setRows(r); setTables(t.filter((x) => x.is_active !== false)); setLoading(false);
  }, [location, day]);
  useEffect(() => { load().catch(() => setLoading(false)); }, [load]);

  const shift = (n: number) => setDay((d) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; });
  const isToday = ymd(day) === ymd(new Date());
  const act = async (r: Reservation, a: string, msg: string) => { if ((await run(() => api.post(`/operations/reservations/${r.id}/${a}/`), msg)) !== undefined) load(); };

  async function save() {
    const starts = new Date(`${ymd(day)}T${f.time}`);
    const r = await run(() => api.post("/operations/reservations/", {
      location: location!.id, table: f.table?.id ?? null, guest_name: f.guest_name, phone: f.phone, party_size: Number(f.party_size),
      starts_at: starts.toISOString(), duration_minutes: Number(f.duration), notes: f.notes,
    }), "Booking saved");
    if (r) { setOpen(false); setF(blank); load(); }
  }

  if (me && !me.organization) return <PlatformNotice />;
  const live = rows.filter((r) => r.status === "BOOKED" || r.status === "SEATED");
  const guests = live.reduce((a, r) => a + r.party_size, 0);

  return (
    <>
      <PageHeader title="Reservations" subtitle={`${location?.name} · ${live.length} active · ${guests} guests`} actions={<Button onClick={() => { setF(blank); setOpen(true); }} data-testid="new-booking"><Plus className="h-4 w-4" />New booking</Button>} />
      <div className="mb-4 flex items-center gap-2">
        <button aria-label="Previous day" onClick={() => shift(-1)} className="grid h-10 w-10 place-items-center rounded-xl border border-line bg-surface hover:bg-sunken"><ChevronLeft className="h-5 w-5" /></button>
        <div className="min-w-[180px] rounded-xl border border-line bg-surface px-4 py-2 text-center text-sm font-semibold" data-testid="res-day">{isToday ? "Today · " : ""}{day.toLocaleDateString("en-PK", { weekday: "short", day: "numeric", month: "short" })}</div>
        <button aria-label="Next day" onClick={() => shift(1)} className="grid h-10 w-10 place-items-center rounded-xl border border-line bg-surface hover:bg-sunken"><ChevronRight className="h-5 w-5" /></button>
        {!isToday && <Button variant="ghost" size="sm" onClick={() => setDay(new Date())}>Today</Button>}
      </div>
      {loading ? <Spinner /> : rows.length === 0 ? (
        <EmptyState icon={<CalendarClock className="h-8 w-8" />} title="No bookings for this day" hint="Add one when a guest calls or walks in to book." action={<Button onClick={() => setOpen(true)}>New booking</Button>} />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((r) => (
            <Card key={r.id} className="p-4" >
              <div data-testid={`res-${r.id}`}>
                <div className="flex items-start justify-between gap-2">
                  <div><p className="num text-2xl font-extrabold leading-none">{hhmm(r.starts_at)}</p><p className="mt-1 text-xs text-muted">until {hhmm(r.ends_at)}</p></div>
                  <Badge tone={TONE[r.status]}>{LABEL[r.status]}</Badge>
                </div>
                <p className="mt-3 font-semibold">{r.guest_name}</p>
                <p className="mt-0.5 flex flex-wrap items-center gap-x-3 text-sm text-muted"><span className="inline-flex items-center gap-1"><Users className="h-3.5 w-3.5" />{r.party_size}</span>
                  <span>{r.table_number ? `Table ${r.table_number}` : "No table yet"}</span>{r.phone && <span className="inline-flex items-center gap-1"><Phone className="h-3.5 w-3.5" />{r.phone}</span>}</p>
                {r.notes && <p className="mt-1 text-xs italic text-muted">“{r.notes}”</p>}
                {(r.status === "BOOKED" || r.status === "SEATED") && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {r.status === "BOOKED" && <><Button size="sm" onClick={() => act(r, "seat", "Guest seated")} data-testid="res-seat">Seat now</Button>
                      <Button size="sm" variant="ghost" onClick={() => act(r, "no-show", "Marked no-show")}>No-show</Button>
                      <Button size="sm" variant="ghost" onClick={() => act(r, "cancel", "Booking cancelled")} data-testid="res-cancel">Cancel</Button></>}
                    {r.status === "SEATED" && <Button size="sm" variant="secondary" onClick={() => act(r, "complete", "Completed")}>Mark completed</Button>}
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title={`New booking · ${day.toLocaleDateString("en-PK", { day: "numeric", month: "short" })}`}>
        <div className="space-y-3">
          <Input label="Guest name" data-testid="res-name" value={f.guest_name} onChange={(e) => setF({ ...f, guest_name: e.target.value })} />
          <div className="grid grid-cols-2 gap-3"><Input label="Phone" inputMode="tel" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />
            <Input label="Guests" type="number" min={1} data-testid="res-party" value={f.party_size} onChange={(e) => setF({ ...f, party_size: e.target.value })} /></div>
          <div className="grid grid-cols-2 gap-3"><Input label="Time" type="time" data-testid="res-time" value={f.time} onChange={(e) => setF({ ...f, time: e.target.value })} />
            <Input label="Stay (minutes)" type="number" min={15} step={15} value={f.duration} onChange={(e) => setF({ ...f, duration: e.target.value })} /></div>
          <div><p className="mb-1.5 text-sm font-medium">Table</p>
            <button type="button" onClick={() => setPick(true)} data-testid="res-table" className={cn("flex h-11 w-full items-center justify-between rounded-xl border px-3 text-sm", f.table ? "border-brand bg-brand-soft font-semibold" : "border-line text-muted")}>
              {f.table ? `Table ${f.table.table_number} · seats ${f.table.capacity}` : "Choose a table (optional)"}</button></div>
          <Input label="Note" placeholder="Birthday, high chair…" maxLength={200} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} />
          <Button className="w-full" size="lg" loading={busy} disabled={!f.guest_name.trim() || !Number(f.party_size)} onClick={save} data-testid="res-save">Save booking</Button>
        </div>
      </Modal>
      <TablePicker open={pick} onClose={() => setPick(false)} tables={tables} value={String(f.table?.id ?? "")} taken={new Set()} onPick={(t) => { if (t.capacity < Number(f.party_size)) toast.err(`Table ${t.table_number} seats only ${t.capacity}.`); else { setF({ ...f, table: t }); setPick(false); } }} />
    </>
  );
}
