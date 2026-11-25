import type { PaySlipFull } from "./types";

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
const fmt = (v: string | number) => Number(v).toLocaleString("en-PK", { minimumFractionDigits: 0, maximumFractionDigits: 2 });

/** Opens a printable payslip (A5). Returns false if the pop-up was blocked. */
export function printPayslip(s: PaySlipFull, business: string, currency = "PKR"): boolean {
  const w = window.open("", "_blank", "width=720,height=900");
  if (!w) return false;
  const month = new Date(s.month).toLocaleDateString("en-PK", { month: "long", year: "numeric" });
  const rows = (kind: "earning" | "deduction") => s.lines.filter((l) => l.kind === kind)
    .map((l) => `<tr><td>${esc(l.label)}${l.note ? `<br><small>${esc(l.note)}</small>` : ""}</td><td class="r">${fmt(l.amount)}</td></tr>`).join("") || `<tr><td colspan="2"><small>None</small></td></tr>`;
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Payslip ${esc(s.employee.name)} ${esc(month)}</title>
<style>
  @page { size: A5; margin: 10mm; }
  body { font: 13px/1.4 system-ui, Arial, sans-serif; color: #111; }
  h1 { font-size: 18px; margin: 0; } h2 { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: #666; margin: 14px 0 4px; }
  .head { display: flex; justify-content: space-between; border-bottom: 2px solid #111; padding-bottom: 8px; }
  table { width: 100%; border-collapse: collapse; } td { padding: 3px 0; vertical-align: top; } .r { text-align: right; white-space: nowrap; }
  small { color: #666; } .tot td { border-top: 1px solid #111; font-weight: 700; padding-top: 5px; }
  .net { margin-top: 12px; padding: 10px; background: #f3f3f3; display: flex; justify-content: space-between; font-size: 16px; font-weight: 700; }
  .facts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px 12px; font-size: 12px; }
  .sig { margin-top: 28px; display: flex; justify-content: space-between; font-size: 11px; color: #666; } .sig div { border-top: 1px solid #999; padding-top: 3px; width: 40%; text-align: center; }
</style></head><body>
  <div class="head"><div><h1>${esc(business)}</h1><small>${esc(s.location_name)}</small></div><div style="text-align:right"><b>Payslip</b><br>${esc(month)}</div></div>
  <h2>Employee</h2><div><b>${esc(s.employee.name)}</b> · ${esc(s.employee.role_display)} · ${esc(s.employee.code)}</div>
  <h2>Attendance</h2><div class="facts"><span>Worked days: <b>${s.present_days}</b></span><span>Absent: <b>${s.absent_days}</b></span><span>Leave: <b>${s.leave_paid + s.leave_unpaid}</b></span>
    <span>Late: <b>${s.late_days}</b></span><span>Hours: <b>${(s.worked_minutes / 60).toFixed(1)}</b></span><span>Overtime: <b>${(s.overtime_minutes / 60).toFixed(1)} h</b></span></div>
  <h2>Earnings</h2><table>${rows("earning")}<tr class="tot"><td>Gross</td><td class="r">${fmt(s.gross)}</td></tr></table>
  <h2>Deductions</h2><table>${rows("deduction")}<tr class="tot"><td>Total deductions</td><td class="r">${fmt(s.deductions)}</td></tr></table>
  <div class="net"><span>Net pay (${esc(currency)})</span><span>${fmt(s.net)}</span></div>
  ${s.status === "PAID" ? `<p><small>Paid ${esc(s.paid_method)}${s.paid_reference ? ` · ${esc(s.paid_reference)}` : ""}${s.paid_at ? ` · ${new Date(s.paid_at).toLocaleDateString("en-PK")}` : ""}</small></p>` : ""}
  <div class="sig"><div>Employer</div><div>Employee</div></div>
  <script>window.onload=function(){window.print()}</script>
</body></html>`);
  w.document.close();
  return true;
}
