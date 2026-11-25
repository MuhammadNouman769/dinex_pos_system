import type { Order, OrderStatus } from "./types";

export type Tone = "neutral" | "brand" | "good" | "warn" | "bad";

export function statusTone(s: OrderStatus): Tone {
  switch (s) {
    case "PENDING": return "warn";
    case "CONFIRMED": case "PREPARING": return "brand";
    case "READY": case "OUT_FOR_DELIVERY": case "COMPLETED": return "good";
    case "CANCELLED": return "bad";
    default: return "neutral";
  }
}

/** The one forward step the kitchen/cashier can take from a status. */
export function nextStep(o: Order): { to: OrderStatus; label: string } | null {
  switch (o.status) {
    case "PENDING": return { to: "CONFIRMED", label: "Send to kitchen" };
    case "CONFIRMED": return { to: "PREPARING", label: "Start preparing" };
    case "PREPARING": return { to: "READY", label: "Mark ready" };
    case "READY": return o.order_type === "DELIVERY" ? { to: "OUT_FOR_DELIVERY", label: "Out for delivery" } : { to: "COMPLETED", label: "Complete" };
    case "OUT_FOR_DELIVERY": return { to: "COMPLETED", label: "Delivered" };
    default: return null;
  }
}

export const canCancel = (o: Order) => o.status === "PENDING" || o.status === "CONFIRMED" || o.status === "PREPARING";
