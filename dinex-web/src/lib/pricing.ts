import type { Deal, Product } from "./types";

const r2 = (n: number) => Math.round(n * 100 + Number.EPSILON) / 100;

/** What a deal is worth, from the menu prices (same rule as the server: it re-checks everything). */
export function dealMath(deal: Deal, products: Product[]) {
  const price = new Map<number, number>();
  products.forEach((p) => p.variants.forEach((v) => { if (v.is_active && p.is_active) price.set(v.id, Number(v.base_price)); }));
  let base = 0;
  for (const it of deal.items) {
    const p = price.get(it.product_variant);
    if (p === undefined) return null;                    // a dish in the deal is no longer on the menu
    base += p * it.quantity;
  }
  const raw = deal.discount_type === "PERCENTAGE" ? (base * Math.min(Number(deal.discount_value), 100)) / 100 : Number(deal.discount_value);
  const discount = r2(Math.min(raw, base));
  return { base: r2(base), discount, price: r2(base - discount) };
}

export function dealRunning(deal: Deal, locationId: number | undefined, now = Date.now()) {
  if (!deal.is_active || !deal.items.length) return false;
  if (now < new Date(deal.start_at).getTime() || now > new Date(deal.end_at).getTime()) return false;
  if (deal.locations.length && !deal.locations.some((l) => l.location === locationId && l.is_enabled)) return false;
  return true;
}

/** Same totals as the server: tax and service charge are on the full price, the deal discount comes off the total. */
export function orderTotals(subtotal: number, discount: number, taxRate: number, serviceRate: number) {
  const tax = r2(subtotal * (taxRate / 100));
  const service = r2(subtotal * (serviceRate / 100));
  const gross = r2(subtotal) + tax + service;
  return { subtotal: r2(subtotal), tax, service, discount: Math.min(discount, gross), total: r2(gross - Math.min(discount, gross)) };
}
