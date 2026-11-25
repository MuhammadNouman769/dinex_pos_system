"use client";
import { useRef, useState } from "react";
import { TableVisual, layout } from "@/components/TableVisual";
import type { TableT } from "@/lib/types";

const CELL_W = 200, CELL_H = 190, COLS = 5, PAD = 24, SNAP = 10;
export const autoPos = (i: number) => ({ x: PAD + (i % COLS) * CELL_W, y: PAD + Math.floor(i / COLS) * CELL_H });

interface Props { tables: TableT[]; editing: boolean; sel: number | null; sub: (t: TableT) => string; onOpen: (t: TableT) => void; onMove: (t: TableT, x: number, y: number) => void }

/** Free-form floor plan: tables sit where the owner put them. In edit mode they can be dragged (mouse or touch) and snap to a grid. */
export function FloorCanvas({ tables, editing, sel, sub, onOpen, onMove }: Props) {
  const [drag, setDrag] = useState<{ id: number; x: number; y: number } | null>(null);
  const start = useRef<{ px: number; py: number; ox: number; oy: number; moved: boolean } | null>(null);

  const place = tables.map((t, i) => {
    const a = autoPos(i), L = layout(t.shape ?? "SQUARE", t.capacity);
    const d = drag?.id === t.id ? drag : null;
    return { t, L, x: d?.x ?? t.pos_x ?? a.x, y: d?.y ?? t.pos_y ?? a.y };
  });
  const W = Math.max(640, ...place.map((p) => p.x + p.L.w + PAD));
  const H = Math.max(360, ...place.map((p) => p.y + p.L.h + PAD + 24));

  return (
    <div className="scroll-thin overflow-auto rounded-2xl" data-testid="floor-canvas">
      <div className="relative select-none" style={{ width: W, height: H }}>
        {place.map(({ t, L, x, y }) => (
          <div key={t.id} data-testid={`ft-${t.id}`} style={{ position: "absolute", left: x, top: y, touchAction: editing ? "none" : "auto", cursor: editing ? "grab" : "default" }}
            className={editing ? "rounded-2xl ring-2 ring-dashed ring-brand/40" : undefined}
            onPointerDown={editing ? (e) => { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); start.current = { px: e.clientX, py: e.clientY, ox: x, oy: y, moved: false }; setDrag({ id: t.id, x, y }); } : undefined}
            onPointerMove={editing ? (e) => { const s = start.current; if (!s || drag?.id !== t.id) return; s.moved = true;
              setDrag({ id: t.id, x: Math.max(0, Math.round((s.ox + e.clientX - s.px) / SNAP) * SNAP), y: Math.max(0, Math.round((s.oy + e.clientY - s.py) / SNAP) * SNAP) }); } : undefined}
            onPointerUp={editing ? () => { const s = start.current; start.current = null; if (s?.moved && drag) onMove(t, drag.x, drag.y); setDrag(null); } : undefined}>
            <div style={{ pointerEvents: editing ? "none" : "auto" }}>
              <TableVisual shape={t.shape ?? "SQUARE"} seats={t.capacity} label={t.table_number} status={t.status} sub={sub(t)} selected={sel === t.id} onClick={editing ? undefined : () => onOpen(t)} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
