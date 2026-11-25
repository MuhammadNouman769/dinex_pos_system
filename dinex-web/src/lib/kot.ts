import type { Order } from "./types";

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));

export interface KotOpts { location: string; tableLabel?: string; temporary?: boolean }

/** Kitchen order ticket: big quantities, dish options and notes, no prices. Returns false if the popup was blocked. */
export function printKot(order: Order, o: KotOpts): boolean {
  const w = window.open("", "_blank", "width=380,height=640");
  if (!w) return false;
  const rows = order.items.map((i) => `
    <div class="it"><span class="q">${i.quantity}×</span><span class="n">${esc(i.product_name || i.deal_name || "")}${i.variant_name && i.variant_name !== "Regular" ? ` <small>(${esc(i.variant_name)})</small>` : ""}${i.deal_name ? ` <small>[${esc(i.deal_name)}]</small>` : ""}</span></div>
    ${(i.modifiers ?? []).map((m) => `<div class="m">+ ${esc(m.name)}</div>`).join("")}${i.notes ? `<div class="note">** ${esc(i.notes)} **</div>` : ""}`).join("");
  const kind = order.order_type === "DINE_IN" ? `DINE-IN${o.tableLabel ? ` · TABLE ${esc(o.tableLabel)}` : ""}` : esc(order.order_type_display).toUpperCase();
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>KOT ${esc(order.order_number)}</title>
<style>
  @page { size: 80mm auto; margin: 3mm; }
  * { color: #000 !important; }
  body { font: 13px/1.3 "Courier New", monospace; width: 72mm; margin: 0 auto; background: #fff; }
  h1 { font-size: 20px; text-align: center; margin: 2px 0; letter-spacing: 1px; }
  .c { text-align: center; } hr { border: 0; border-top: 2px dashed #000; margin: 6px 0; }
  .kind { font-size: 17px; font-weight: bold; text-align: center; border: 2px solid #000; padding: 3px; margin: 4px 0; }
  .it { display: flex; gap: 6px; font-size: 17px; font-weight: bold; margin-top: 7px; } .q { min-width: 34px; } .n { flex: 1; }
  .m { font-size: 14px; margin-left: 40px; } .note { font-size: 14px; font-weight: bold; margin: 2px 0 0 40px; }
  small { font-size: 11px; font-weight: normal; }
</style></head><body>
  <h1>KITCHEN ORDER</h1>
  <div class="c">${esc(o.location)}</div>
  <div class="kind">${kind}</div>
  <div>No: <b>${esc(order.order_number)}</b>${o.temporary ? " (not synced yet)" : ""}<br>${new Date(order.created_at).toLocaleTimeString("en-PK", { hour: "2-digit", minute: "2-digit" })}${order.waiter_name ? ` · Waiter: ${esc(order.waiter_name)}` : ""}${order.customer_name ? `<br>Guest: ${esc(order.customer_name)}` : ""}</div>
  <hr>${rows}<hr>
  ${order.notes ? `<div class="note" style="margin-left:0">ORDER NOTE: ${esc(order.notes)}</div><hr>` : ""}
  <div class="c"><small>${order.items.reduce((a, i) => a + i.quantity, 0)} items</small></div>
  <script>window.onload=function(){window.print();setTimeout(function(){window.close()},400)}</script>
</body></html>`);
  w.document.close();
  return true;
}
