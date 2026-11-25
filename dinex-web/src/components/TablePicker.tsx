"use client";
import { useMemo, useState } from "react";
import { Legend, TableVisual } from "@/components/TableVisual";
import { Modal, cn } from "@/components/ui";
import type { TableT } from "@/lib/types";

/** Pick a table on the floor plan. Busy tables are shown but cannot be chosen. */
export function TablePicker({ open, onClose, tables, value, taken, onPick }: { open: boolean; onClose: () => void; tables: TableT[]; value: string; taken: Set<number>; onPick: (t: TableT) => void }) {
  const floors = useMemo(() => {
    const m = new Map<string, TableT[]>();
    tables.filter((t) => t.is_active !== false).forEach((t) => { const k = t.floor_name ?? "Tables"; m.set(k, [...(m.get(k) ?? []), t]); });
    return [...m.entries()];
  }, [tables]);
  const [f, setF] = useState(0);
  const cur = floors[Math.min(f, Math.max(floors.length - 1, 0))];
  return (
    <Modal open={open} onClose={onClose} title="Choose a table" width="max-w-3xl">
      {floors.length === 0 ? <p className="py-10 text-center text-sm text-muted">No tables yet. Add them in Setup → Floors &amp; tables.</p> : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="scroll-thin flex gap-2 overflow-x-auto">
              {floors.map(([name], i) => <button key={name} onClick={() => setF(i)} className={cn("min-h-[40px] shrink-0 rounded-full border px-4 text-sm font-semibold", i === f ? "border-brand bg-brand text-white dark:text-[#04201a]" : "border-line text-muted")}>{name}</button>)}
            </div>
            <Legend />
          </div>
          <div className="flex max-h-[60vh] flex-wrap items-end justify-center gap-x-6 gap-y-5 overflow-y-auto rounded-2xl bg-sunken p-5">
            {cur?.[1].map((t) => {
              const busy = t.status !== "AVAILABLE" || taken.has(t.id);
              return (
                <div key={t.id} className={cn(busy && "pointer-events-none opacity-45")}>
                  <TableVisual shape={t.shape ?? "SQUARE"} seats={t.capacity} label={t.table_number} status={taken.has(t.id) ? "OCCUPIED" : t.status} scale={0.85} selected={String(t.id) === value} onClick={() => onPick(t)} />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Modal>
  );
}
