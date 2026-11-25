"use client";
import { useCallback, useEffect, useState } from "react";
import { Layers, Plus, Trash2, X } from "lucide-react";
import { Badge, Button, Card, EmptyState, Input, Modal, Spinner, cn, useAction } from "@/components/ui";
import { SHAPES, TableVisual } from "@/components/TableVisual";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import type { Floor, TableShape, TableT } from "@/lib/types";

const PRESETS = [
  { name: "Basement", level: -1 }, { name: "Ground Floor", level: 0 }, { name: "First Floor", level: 1 },
  { name: "Second Floor", level: 2 }, { name: "Rooftop", level: 3 },
];

export function FloorsStep() {
  const { location } = useAuth();
  const { run, busy } = useAction();
  const [floors, setFloors] = useState<Floor[]>([]);
  const [tables, setTables] = useState<TableT[]>([]);
  const [loading, setLoading] = useState(true);
  const [custom, setCustom] = useState("");
  const [bulk, setBulk] = useState<Record<number, { count: string; seats: string; shape: TableShape }>>({});
  const [edit, setEdit] = useState<{ t: TableT; number: string; seats: string; shape: TableShape } | null>(null);

  const load = useCallback(async () => {
    if (!location) return;
    const [f, t] = await Promise.all([api.list<Floor>("/orders/floors/", { location: location.id }), api.list<TableT>("/orders/tables/", { location: location.id })]);
    setFloors(f); setTables(t); setLoading(false);
  }, [location]);
  useEffect(() => { load().catch(() => setLoading(false)); }, [load]);

  if (!location) return null;
  if (loading) return <Spinner />;

  const nextLevel = floors.length ? Math.max(...floors.map((f) => f.level)) + 1 : 0;
  const addFloor = async (name: string, level: number) => {
    const r = await run(() => api.post("/orders/floors/", { location: location.id, name, level }));
    if (r !== undefined) { setCustom(""); load(); }
  };

  const nextTableNumber = () => tables.reduce((m, t) => Math.max(m, Number(t.table_number.replace(/\D/g, "")) || 0), 0) + 1;
  async function addTables(floor: Floor | null) {
    const key = floor?.id ?? 0;
    const { count = "1", seats = "4", shape = "SQUARE" } = bulk[key] ?? {};
    const n = Math.min(Math.max(parseInt(count) || 0, 1), 50);
    let start = nextTableNumber();
    const ok = await run(async () => {
      for (let i = 0; i < n; i++) await api.post("/orders/tables/", { location: location!.id, floor: floor?.id ?? null, table_number: `T-${start++}`, capacity: Math.min(Math.max(parseInt(seats) || 4, 1), 20), shape });
      return true;
    }, `${n} table${n > 1 ? "s" : ""} added`);
    if (ok) load();
  }
  const delTable = async (t: TableT) => { if ((await run(() => api.del(`/orders/tables/${t.id}/`), "Table removed")) !== undefined) { setEdit(null); load(); } };
  async function saveEdit() {
    if (!edit) return;
    const r = await run(() => api.patch(`/orders/tables/${edit.t.id}/`, { table_number: edit.number.trim(), capacity: Math.min(Math.max(parseInt(edit.seats) || 1, 1), 20), shape: edit.shape }), "Table updated");
    if (r !== undefined) { setEdit(null); load(); }
  }
  const delFloor = async (f: Floor) => { if (!confirm(`Delete ${f.name}?`)) return; if ((await run(() => api.del(`/orders/floors/${f.id}/`), "Floor removed")) !== undefined) load(); };

  const groups: { floor: Floor | null; items: TableT[] }[] = [
    ...floors.map((f) => ({ floor: f, items: tables.filter((t) => t.floor === f.id) })),
    ...(tables.some((t) => !t.floor) ? [{ floor: null, items: tables.filter((t) => !t.floor) }] : []),
  ];

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-lg font-bold">Floors</h2>
        <p className="mb-4 text-sm text-muted">Add every floor or area where guests sit. You can add more any time.</p>
        <div className="flex flex-wrap gap-2">
          {PRESETS.filter((p) => !floors.some((f) => f.name.toLowerCase() === p.name.toLowerCase())).map((p) => (
            <button key={p.name} disabled={busy} onClick={() => addFloor(p.name, p.level)} className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-line px-3.5 py-1.5 text-sm font-semibold text-muted transition hover:border-brand hover:text-brand">
              <Plus className="h-3.5 w-3.5" />{p.name}
            </button>
          ))}
        </div>
        <form className="mt-4 flex max-w-md gap-2" onSubmit={(e) => { e.preventDefault(); if (custom.trim()) addFloor(custom.trim(), nextLevel); }}>
          <Input aria-label="Custom floor name" placeholder="Other area, e.g. Family Hall" value={custom} onChange={(e) => setCustom(e.target.value)} />
          <Button type="submit" variant="secondary" disabled={!custom.trim()} loading={busy}>Add</Button>
        </form>
      </Card>

      {groups.length === 0 ? <EmptyState icon={<Layers className="h-8 w-8" />} title="No floors yet" hint="Pick a floor above to start. Takeaway-only restaurants can skip this step." /> : groups.map(({ floor, items }) => {
        const key = floor?.id ?? 0;
        const b = bulk[key] ?? { count: "1", seats: "4", shape: "SQUARE" as TableShape };
        return (
          <Card key={key} className="p-6">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2"><h3 className="text-lg font-bold">{floor?.name ?? "No floor assigned"}</h3><Badge>{items.length} table{items.length === 1 ? "" : "s"}</Badge></div>
              {floor && items.length === 0 && <Button size="sm" variant="danger" onClick={() => delFloor(floor)}><Trash2 className="h-4 w-4" />Remove floor</Button>}
            </div>
            <div className="mb-5 flex flex-wrap items-end gap-3">
              {items.map((t) => <TableVisual key={t.id} shape={t.shape ?? "SQUARE"} seats={t.capacity} label={t.table_number} status={t.status} scale={0.78} onClick={() => setEdit({ t, number: t.table_number, seats: String(t.capacity), shape: t.shape ?? "SQUARE" })} />)}
              {items.length === 0 && <p className="text-sm text-muted">No tables on this floor yet.</p>}
            </div>
            {items.length > 0 && <p className="-mt-2 mb-4 text-xs text-muted">Tap a table to change its number, seats or shape.</p>}
            <div className="space-y-4 border-t border-line pt-4">
              <p className="text-sm font-semibold">Add tables</p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4" role="radiogroup" aria-label="Table shape">
                {SHAPES.map((sh) => (
                  <button key={sh.id} type="button" role="radio" aria-checked={b.shape === sh.id} data-testid={`shape-${sh.id}`} onClick={() => setBulk((x) => ({ ...x, [key]: { ...b, shape: sh.id } }))}
                    className={cn("flex flex-col items-center gap-1 rounded-2xl border p-3 text-center transition", b.shape === sh.id ? "border-brand bg-brand-soft" : "border-line hover:bg-sunken")}>
                    <TableVisual shape={sh.id} seats={Math.min(Math.max(parseInt(b.seats) || 4, 1), 12)} sub=" " scale={0.62} />
                    <span className="text-sm font-bold">{sh.label}</span><span className="text-[11px] leading-tight text-muted">{sh.hint}</span>
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap items-end gap-3">
                <div className="w-28"><Input label="Seats each" type="number" min="1" max="20" value={b.seats} onChange={(e) => setBulk((x) => ({ ...x, [key]: { ...b, seats: e.target.value } }))} /></div>
                <div className="w-28"><Input label="How many" type="number" min="1" max="50" value={b.count} onChange={(e) => setBulk((x) => ({ ...x, [key]: { ...b, count: e.target.value } }))} /></div>
                <Button variant="secondary" loading={busy} onClick={() => addTables(floor)} data-testid="add-tables"><Plus className="h-4 w-4" />Add tables</Button>
              </div>
            </div>
          </Card>
        );
      })}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={`Edit ${edit?.t.table_number ?? "table"}`} width="max-w-md">
        {edit && (
          <div className="space-y-4">
            <div className="grid place-items-center rounded-2xl bg-sunken py-4"><TableVisual shape={edit.shape} seats={Math.min(Math.max(parseInt(edit.seats) || 1, 1), 20)} label={edit.number || "T-?"} scale={1} /></div>
            <div className="grid grid-cols-2 gap-3">
              <Input label="Table number" value={edit.number} onChange={(e) => setEdit({ ...edit, number: e.target.value })} hint="Format: T-1, T-2…" />
              <Input label="Seats" type="number" min="1" max="20" value={edit.seats} onChange={(e) => setEdit({ ...edit, seats: e.target.value })} />
            </div>
            <div className="grid grid-cols-4 gap-2">
              {SHAPES.map((sh) => <button key={sh.id} type="button" onClick={() => setEdit({ ...edit, shape: sh.id })} className={cn("rounded-xl border px-1 py-2 text-xs font-bold transition", edit.shape === sh.id ? "border-brand bg-brand-soft text-brand" : "border-line hover:bg-sunken")}>{sh.label}</button>)}
            </div>
            <div className="flex gap-2">
              <Button className="flex-1" loading={busy} disabled={!edit.number.trim()} onClick={saveEdit}>Save</Button>
              <Button variant="danger" onClick={() => { if (confirm(`Delete ${edit.t.table_number}?`)) delTable(edit.t); }}><Trash2 className="h-4 w-4" /></Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
