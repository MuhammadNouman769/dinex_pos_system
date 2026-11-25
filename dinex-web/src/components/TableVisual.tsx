"use client";
import type { TableShape } from "@/lib/types";

type Side = "top" | "bottom" | "left" | "right";
const SIDES: Record<TableShape, Side[]> = { SQUARE: ["top", "bottom", "left", "right"], LONG: ["top", "bottom"], WALL: ["bottom", "left", "right"], ROUND: [] };
const CH = 26;          // space one chair takes along a side
const CW = 20, CD = 9;  // chair width / depth
const GAP = 5, PAD = 6;

export const SHAPES: { id: TableShape; label: string; hint: string }[] = [
  { id: "SQUARE", label: "4 sides", hint: "Seats on all four sides" },
  { id: "ROUND", label: "Round", hint: "Seats all around" },
  { id: "LONG", label: "Long", hint: "Seats on the two long sides" },
  { id: "WALL", label: "3 sides", hint: "One side against the wall" },
];

/** Status colours: [fill, stroke, chair] as CSS colour strings. */
export const STATUS_STYLE: Record<string, { label: string; c: string }> = {
  AVAILABLE: { label: "Available", c: "var(--good)" },
  OCCUPIED: { label: "Occupied", c: "var(--bad)" },
  RESERVED: { label: "Reserved", c: "var(--warn)" },
  CLEANING: { label: "Cleaning", c: "var(--muted)" },
};

function split(n: number, sides: Side[]) {
  const c: Record<Side, number> = { top: 0, bottom: 0, left: 0, right: 0 };
  for (let i = 0; i < n; i++) c[sides[i % sides.length]]++;
  return c;
}

export function layout(shape: TableShape, seats: number) {
  const n = Math.max(1, Math.min(seats, 20));
  const m = CD + GAP + PAD;
  if (shape === "ROUND") {
    const d = Math.max(70, n * 13.5), r = d / 2, R = r + GAP + CD / 2, size = d + 2 * m;
    const chairs = Array.from({ length: n }, (_, i) => { const a = (i / n) * Math.PI * 2 - Math.PI / 2; return { x: size / 2 + R * Math.cos(a), y: size / 2 + R * Math.sin(a), rot: (a * 180) / Math.PI + 90, w: CW, h: CD }; });
    return { w: size, h: size, round: true, r, tx: m, ty: m, tw: d, th: d, chairs };
  }
  const c = split(n, SIDES[shape]);
  const tw = Math.max(shape === "LONG" ? 96 : 76, CH * Math.max(c.top, c.bottom) + 14);
  const th = Math.max(shape === "LONG" ? 56 : 76, CH * Math.max(c.left, c.right) + 14);
  const w = tw + 2 * m, h = th + 2 * m;
  const chairs: { x: number; y: number; rot: number; w: number; h: number }[] = [];
  const row = (count: number, len: number, fn: (pos: number) => { x: number; y: number; rot: number }) => { for (let i = 0; i < count; i++) chairs.push({ ...fn(((i + 0.5) / count) * len), w: CW, h: CD }); };
  row(c.top, tw, (p) => ({ x: m + p, y: m - GAP - CD / 2, rot: 0 }));
  row(c.bottom, tw, (p) => ({ x: m + p, y: m + th + GAP + CD / 2, rot: 0 }));
  row(c.left, th, (p) => ({ x: m - GAP - CD / 2, y: m + p, rot: 90 }));
  row(c.right, th, (p) => ({ x: m + tw + GAP + CD / 2, y: m + p, rot: 90 }));
  return { w, h, round: false, r: 0, tx: m, ty: m, tw, th, chairs };
}

interface Props { shape: TableShape; seats: number; label?: string; status?: string; scale?: number; selected?: boolean; onClick?: () => void; sub?: string; className?: string }

/** A table with its chairs, drawn as SVG. Works for the floor plan, the POS picker and the shape chooser. */
export function TableVisual({ shape, seats, label, status = "AVAILABLE", scale = 1, selected, onClick, sub, className }: Props) {
  const L = layout(shape, seats);
  const c = (STATUS_STYLE[status] ?? STATUS_STYLE.AVAILABLE).c;
  const body = { fill: `rgb(${c} / 0.14)`, stroke: `rgb(${c})`, strokeWidth: selected ? 2.4 : 1.4 };
  const inner = (
    <svg viewBox={`0 0 ${L.w} ${L.h}`} width={L.w * scale} height={L.h * scale} {...(label ? { role: "img", "aria-label": `${label}, ${seats} seats, ${(STATUS_STYLE[status] ?? STATUS_STYLE.AVAILABLE).label}` } : { "aria-hidden": true })} className={className}>
      {L.chairs.map((k, i) => <rect key={i} x={-k.w / 2} y={-k.h / 2} width={k.w} height={k.h} rx={4} fill={`rgb(${c} / 0.8)`} transform={`translate(${k.x} ${k.y}) rotate(${k.rot})`} />)}
      {L.round ? <circle cx={L.tx + L.r} cy={L.ty + L.r} r={L.r} {...body} /> : <rect x={L.tx} y={L.ty} width={L.tw} height={L.th} rx={12} {...body} />}
      {selected && (L.round ? <circle cx={L.tx + L.r} cy={L.ty + L.r} r={L.r + 14} fill="none" stroke={`rgb(${c})`} strokeDasharray="3 4" opacity={0.7} /> : <rect x={L.tx - 14} y={L.ty - 14} width={L.tw + 28} height={L.th + 28} rx={20} fill="none" stroke={`rgb(${c})`} strokeDasharray="3 4" opacity={0.7} />)}
      {label && <text x={L.tx + L.tw / 2} y={L.ty + L.th / 2 - (sub ? 2 : -1)} textAnchor="middle" dominantBaseline="middle" fontSize={13} fontWeight={800} style={{ fill: "rgb(var(--ink))", fontFamily: "inherit" }}>{label}</text>}
      <text x={L.tx + L.tw / 2} y={L.ty + L.th / 2 + (label ? 14 : 1)} textAnchor="middle" dominantBaseline="middle" fontSize={10.5} fontWeight={600} style={{ fill: "rgb(var(--muted))", fontFamily: "inherit" }}>{sub ?? `${seats} seats`}</text>
    </svg>
  );
  return onClick ? <button type="button" onClick={onClick} aria-pressed={selected} className="rounded-2xl p-1 outline-none transition hover:scale-[1.04] focus-visible:ring-2 focus-visible:ring-brand active:scale-95">{inner}</button> : inner;
}

export function Legend() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-medium text-muted">
      {Object.entries(STATUS_STYLE).filter(([k]) => k !== "CLEANING").map(([k, v]) => <span key={k} className="inline-flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full" style={{ background: `rgb(${v.c})` }} />{v.label}</span>)}
    </div>
  );
}
