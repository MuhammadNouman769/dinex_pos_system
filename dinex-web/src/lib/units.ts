import type { BaseUnit } from "./types";

/** Units a person can type for each base unit. The server converts to g / ml / pcs. */
export const UNIT_OPTIONS: Record<BaseUnit, { value: string; label: string }[]> = {
  G: [{ value: "g", label: "g" }, { value: "kg", label: "kg" }],
  ML: [{ value: "ml", label: "ml" }, { value: "l", label: "litre" }],
  PCS: [{ value: "pcs", label: "pcs" }, { value: "dozen", label: "dozen" }],
};
export const BASE_LABEL: Record<BaseUnit, string> = { G: "Weight (g / kg)", ML: "Liquid (ml / litre)", PCS: "Pieces" };

/** 5000 g -> "5 kg", 250 ml -> "250 ml", 24 pcs -> "24 pcs" */
export function formatQty(qty: string | number, base: BaseUnit): string {
  const n = Number(qty);
  const f = (x: number) => x.toLocaleString("en-PK", { maximumFractionDigits: 2 });
  if (base === "G") return Math.abs(n) >= 1000 ? `${f(n / 1000)} kg` : `${f(n)} g`;
  if (base === "ML") return Math.abs(n) >= 1000 ? `${f(n / 1000)} l` : `${f(n)} ml`;
  return `${f(n)} pcs`;
}

/** Friendly price unit for an ingredient: Rs per kg / litre / piece, converted to/from the per-base-unit cost the API stores. */
export const PRICE_UNIT: Record<BaseUnit, { label: string; factor: number }> = {
  G: { label: "per kg", factor: 1000 },
  ML: { label: "per litre", factor: 1000 },
  PCS: { label: "per piece", factor: 1 },
};
