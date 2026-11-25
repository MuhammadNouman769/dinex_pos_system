import type { Order, OrderStatus } from "@/lib/types";
import type { OutboxEntry } from "./outbox";

/** An Order-shaped object for a bill printed before the server has seen the order (number is the temporary OFF-… one). */
export function localOrder(e: OutboxEntry): Order {
  const d = e.display;
  return {
    id: -1, order_number: d.number, location: e.location, location_name: "", order_type: e.payload.order_type, order_type_display: d.type_label,
    table: e.payload.table ?? null, customer_name: d.customer, customer_phone: e.payload.customer_phone ?? "", delivery_address: e.payload.delivery_address ?? "",
    waiter: null, waiter_name: null, rider: null, rider_name: null, dispatched_at: null, delivered_at: null,
    subtotal: String(d.subtotal), tax: String(d.tax), service_charge: String(d.service), discount: String(d.discount), total_amount: String(d.total),
    status: "CONFIRMED" as OrderStatus, status_display: "Waiting to sync", payment_status: e.payload.payments.length ? "PAID" : "PENDING", notes: e.payload.notes ?? "",
    created_at: e.payload.placed_at,
    items: d.lines.map((l, i) => ({ id: i, product_name: l.name, variant_name: "", quantity: l.qty, unit_price: String(l.price), total_price: String(l.price * l.qty), notes: l.notes, modifiers: (l.mods ?? []).map((m) => ({ name: m })) })),
  };
}
