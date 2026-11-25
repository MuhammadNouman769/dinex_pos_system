import QRCode from "qrcode";
import type { Branding, Order, LoyaltyRules } from "./types";

const plain = (v: string | number | undefined) => String(Number(v ?? 0));
const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
const fmt = (v: string | number) => Number(v).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export interface ReceiptOpts { business: string; location: string; address?: string; currency: string; branding?: Branding; tableLabel?: string; loyalty?: LoyaltyRules }

/** Payment QR as a black-and-white image: the uploaded picture if there is one, else a code made from the saved text. */
async function qrImage(b?: Branding): Promise<string> {
  if (!b || !b.show_qr) return "";
  if (b.qr_bw) return b.qr_bw;
  if (b.qr_text) { try { return await QRCode.toDataURL(b.qr_text, { margin: 1, width: 240, errorCorrectionLevel: "M", color: { dark: "#000000", light: "#ffffff" } }); } catch { return ""; } }
  return "";
}

/** Opens an 80mm thermal bill and prints it. Returns false if the popup was blocked (the window opens at once, the content is filled in a moment later). */
export function printReceipt(order: Order, o: ReceiptOpts): boolean {
  const w = window.open("", "_blank", "width=380,height=760");
  if (!w) return false;
  w.document.write("<!doctype html><title>Printing…</title><body style='font:14px sans-serif;padding:24px'>Preparing bill…</body>");
  qrImage(o.branding).then((qr) => {
    const b = o.branding;
    const rows = order.items.map((i) =>
      `<tr><td>${esc(i.product_name || i.deal_name || "")}${i.variant_name && i.variant_name !== "Regular" ? ` <small>(${esc(i.variant_name)})</small>` : ""}<br><small>${i.quantity} x ${fmt(i.unit_price)}</small>${i.notes ? `<br><small>* ${esc(i.notes)}</small>` : ""}</td><td class="r">${fmt(i.total_price)}</td></tr>`).join("");
    const line = (label: string, v: string, strong = false) => Number(v) === 0 && !strong ? "" : `<tr class="${strong ? "tot" : ""}"><td>${label}</td><td class="r">${fmt(v)}</td></tr>`;
    const L = o.loyalty;
    const ol = order.loyalty;
    const loyaltyBlock = L?.enabled ? `<hr><div class="c b">LOYALTY POINTS</div>
      ${ol ? `<table>${ol.earned ? `<tr><td>Points earned</td><td class="r">+${ol.earned}</td></tr>` : ""}${ol.redeemed ? `<tr><td>Points used (${o.currency} ${fmt(ol.redeemed_value)} off)</td><td class="r">-${ol.redeemed}</td></tr>` : ""}<tr><td><b>Your points balance</b></td><td class="r"><b>${ol.balance}</b></td></tr></table>` : ""}
      <div class="c"><small>Earn 1 point for every ${esc(o.currency)} ${esc(plain(L.spend_per_point))} you spend.<br>1 point = ${esc(o.currency)} ${esc(plain(L.point_value))} off. Use points when you have ${L.min_redeem ?? 100}+.</small></div>` : "";
    const accounts = b?.show_accounts && b.accounts.length
      ? `<hr><div class="c b">PAY TO / ACCOUNT DETAILS</div><table class="acc">${b.accounts.map((a) => `<tr><td class="lbl">${esc(a.label)}</td><td>${a.title ? `${esc(a.title)}<br>` : ""}<b>${esc(a.number)}</b></td></tr>`).join("")}</table>` : "";
    const qrBlock = qr ? `<div class="c" style="margin-top:6px"><img class="qr" src="${qr}" alt="Payment QR"><div><small>Scan to pay</small></div></div>` : "";
    w.document.open();
    w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${esc(order.order_number)}</title>
<style>
  @page { size: 80mm auto; margin: 3mm; }
  * { color: #000 !important; -webkit-print-color-adjust: exact; }
  body { font: 12px/1.35 "Courier New", monospace; width: 72mm; margin: 0 auto; background: #fff; }
  h1 { font-size: 17px; text-align: center; margin: 4px 0 2px; text-transform: uppercase; letter-spacing: .5px; }
  .logo { display: block; margin: 0 auto 2px; max-width: 46mm; max-height: 24mm; image-rendering: pixelated; }
  .qr { width: 34mm; height: 34mm; image-rendering: pixelated; }
  .c { text-align: center; } .r { text-align: right; white-space: nowrap; } .b { font-weight: bold; }
  hr { border: 0; border-top: 1px dashed #000; margin: 6px 0; }
  table { width: 100%; border-collapse: collapse; } td { padding: 2px 0; vertical-align: top; }
  .tot td { font-weight: bold; font-size: 14px; border-top: 1px solid #000; padding-top: 4px; }
  .acc td.lbl { width: 24mm; font-weight: bold; padding-right: 2mm; } .acc td { padding: 2px 0 4px; }
  small { font-size: 10px; }
</style></head><body>
  ${b?.show_logo !== false && b?.logo_bw ? `<img class="logo" src="${b.logo_bw}" alt="">` : ""}
  <h1>${esc(o.business)}</h1>
  <div class="c">${esc(o.location)}${o.address ? `<br>${esc(o.address)}` : ""}</div>
  <hr>
  <div>Bill: <b>${esc(order.order_number)}</b><br>${new Date(order.created_at).toLocaleString("en-PK")}<br>${esc(order.order_type_display)}${o.tableLabel ? ` · Table ${esc(o.tableLabel)}` : ""}${order.customer_name ? `<br>Customer: ${esc(order.customer_name)}` : ""}${order.waiter_name ? `<br>Waiter: ${esc(order.waiter_name)}` : ""}</div>
  <hr>
  <table>${rows}</table>
  <hr>
  <table>${line("Subtotal", order.subtotal, true).replace('class="tot"', "")}${line("Service charge", order.service_charge)}${line("Tax", order.tax)}${line("Discount", order.discount)}${line(`TOTAL (${o.currency})`, order.total_amount, true)}</table>
  ${loyaltyBlock}
  ${accounts}${qrBlock}
  <hr>
  <div class="c">${esc(b?.footer || "Thank you! Please visit again.")}<br><small>Powered by DineX · XverLabs</small></div>
  <script>window.onload=function(){window.print();setTimeout(function(){window.close()},400)}</script>
</body></html>`);
    w.document.close();
  });
  return true;
}
