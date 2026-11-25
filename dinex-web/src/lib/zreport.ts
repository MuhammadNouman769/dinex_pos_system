import type { DayReport } from "./types";

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
const METHODS: Record<string, string> = { CASH: "Cash", CARD: "Card", WALLET: "JazzCash / Easypaisa", BANK: "Bank transfer" };

/** Printable end-of-day (Z) report on an 80mm roll. Returns false if the popup was blocked. */
export function printZReport(r: DayReport, o: { business: string; currency: string }): boolean {
  const w = window.open("", "_blank", "width=400,height=720");
  if (!w) return false;
  const m = (v: string | number | null | undefined) => `${Number(v ?? 0).toLocaleString("en-PK", { maximumFractionDigits: 2 })}`;
  const row = (a: string, b: string, bold = false) => `<div class="r${bold ? " b" : ""}"><span>${esc(a)}</span><span>${esc(b)}</span></div>`;
  const dt = new Date(r.date + "T00:00").toLocaleDateString("en-PK", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>End of day ${esc(r.date)}</title><style>
@page{size:80mm auto;margin:3mm}*{color:#000!important}body{font:12px/1.35 "Courier New",monospace;width:72mm;margin:0 auto;background:#fff}
h1{font-size:17px;text-align:center;margin:2px 0}.c{text-align:center}hr{border:0;border-top:1px dashed #000;margin:6px 0}
.r{display:flex;justify-content:space-between;gap:8px}.b{font-weight:bold;font-size:13px}h2{font-size:12px;margin:8px 0 2px;text-transform:uppercase;letter-spacing:1px}
</style></head><body>
<h1>${esc(o.business)}</h1><div class="c">END OF DAY REPORT<br>${esc(dt)}<br>${esc(r.locations.join(", "))}</div><hr>
<h2>Sales (${esc(o.currency)})</h2>
${Object.entries(r.by_method).filter(([, v]) => Number(v) !== 0).map(([k, v]) => row(METHODS[k] ?? k, m(v))).join("")}
${row("Gross sales", m(r.sales.gross_sales))}${row("Refunds", "-" + m(r.sales.refunds))}${row("NET SALES", m(r.sales.net_sales), true)}
${row("Orders", String(r.sales.orders))}${row("Discounts given", m(r.sales.discounts))}${row("Tax collected", m(r.sales.tax))}
${r.exceptions.cancelled.count ? row(`Cancelled (${r.exceptions.cancelled.count})`, m(r.exceptions.cancelled.total)) : ""}
<hr><h2>Expenses</h2>${r.expenses.by_category.map((c) => row(c.category, m(c.amount))).join("") || "<div>None</div>"}${row("TOTAL EXPENSES", m(r.expenses.total), true)}
<hr><h2>Purchases</h2>${row("Bought", m(r.purchases.total))}${row("Paid today", m(r.purchases.paid))}${row("Still owed", m(r.purchases.unpaid))}
<hr>${row("NET AFTER COSTS", m(r.net_after_costs), true)}
<hr><h2>Cash drawers</h2>
${r.shifts.map((s) => `<div>${esc(s.cashier)}${s.still_open ? " (STILL OPEN)" : ""}</div>${row(" Expected", m(s.expected_cash))}${s.counted_cash !== null ? row(" Counted", m(s.counted_cash)) + row(" Difference", m(s.difference)) : ""}`).join("") || "<div>No shifts</div>"}
${r.open_shifts ? `<div class="b c">** ${r.open_shifts} SHIFT(S) NOT CLOSED **</div>` : ""}
<hr><div class="c">Printed ${new Date().toLocaleString("en-PK")}</div>
<script>window.onload=function(){window.print();setTimeout(function(){window.close()},400)}</script></body></html>`);
  w.document.close();
  return true;
}
