"use client";
import { useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import { ImagePlus, Plus, Printer, Trash2 } from "lucide-react";
import { Button, Card, Input, Switch, useAction, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { compressImage } from "@/lib/image";
import type { Branding } from "@/lib/types";

const EMPTY: Branding = { logo: null, logo_bw: "", qr_bw: "", qr_text: "", accounts: [], footer: "", show_logo: true, show_accounts: true, show_qr: true };

/** Logo, payment accounts and QR that are printed on every bill. */
export function BrandingCard() {
  const { me, location, reload } = useAuth();
  const { run, busy } = useAction();
  const toast = useToast();
  const [b, setB] = useState<Branding>(EMPTY);
  const [qrPreview, setQrPreview] = useState("");
  const logoRef = useRef<HTMLInputElement>(null), qrRef = useRef<HTMLInputElement>(null);

  useEffect(() => { api.get<Branding>("/organizations/me/branding/").then(setB).catch(() => {}); }, []);
  useEffect(() => {
    if (b.qr_bw || !b.qr_text) { setQrPreview(""); return; }
    QRCode.toDataURL(b.qr_text, { margin: 1, width: 200, color: { dark: "#000000", light: "#ffffff" } }).then(setQrPreview).catch(() => setQrPreview(""));
  }, [b.qr_bw, b.qr_text]);

  const upload = async (kind: "logo" | "qr", file?: File) => {
    if (!file) return;
    try {
      const f = await compressImage(file, 1200, 0.9);
      const fd = new FormData(); fd.append("image", f);
      setB(await api.upload<Branding>(`/organizations/me/branding/${kind}/`, fd)); reload(); toast.ok(kind === "logo" ? "Logo saved" : "QR saved");
    } catch (e) { toast.err((e as Error).message); }
    finally { if (logoRef.current) logoRef.current.value = ""; if (qrRef.current) qrRef.current.value = ""; }
  };
  const remove = async (kind: "logo" | "qr") => { try { await api.del(`/organizations/me/branding/${kind}/`); setB(await api.get<Branding>("/organizations/me/branding/")); reload(); } catch (e) { toast.err((e as Error).message); } };
  const setAcc = (i: number, k: "label" | "title" | "number", v: string) => setB((s) => ({ ...s, accounts: s.accounts.map((a, j) => (j === i ? { ...a, [k]: v } : a)) }));
  const save = async () => {
    const r = await run(() => api.patch<Branding>("/organizations/me/branding/", { accounts: b.accounts, footer: b.footer, qr_text: b.qr_text, show_logo: b.show_logo, show_accounts: b.show_accounts, show_qr: b.show_qr }), "Bill settings saved");
    if (r) { setB(r); reload(); }
  };
  const qr = b.qr_bw || qrPreview;

  return (
    <Card className="max-w-3xl space-y-6 p-6" data-testid="branding-card">
      <div><h2 className="text-lg font-bold">Bill &amp; payment details</h2><p className="text-sm text-muted">Printed on every bill: your logo at the top (in black &amp; white for thermal printers), and your account numbers and payment QR at the bottom.</p></div>

      <div className="grid gap-6 sm:grid-cols-[1fr_1fr]">
        <section className="space-y-3">
          <div className="flex items-center justify-between"><h3 className="font-semibold">Logo</h3><Switch label="Show logo on bill" checked={b.show_logo} onChange={(v) => setB({ ...b, show_logo: v })} /></div>
          <div className="grid h-36 place-items-center rounded-2xl border border-dashed border-line bg-white p-3">
            {b.logo_bw ? <img src={b.logo_bw} alt="Logo as printed" className="max-h-full max-w-full" style={{ imageRendering: "pixelated" }} /> : <span className="text-center text-sm text-muted"><ImagePlus className="mx-auto mb-1 h-7 w-7 opacity-50" />No logo yet</span>}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => logoRef.current?.click()} data-testid="upload-logo"><ImagePlus className="h-4 w-4" />{b.logo_bw ? "Change logo" : "Upload logo"}</Button>
            {b.logo_bw && <Button variant="ghost" size="sm" aria-label="Remove logo" onClick={() => remove("logo")}><Trash2 className="h-4 w-4" /></Button>}
            <input ref={logoRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" data-testid="logo-input" onChange={(e) => upload("logo", e.target.files?.[0])} />
          </div>
          <p className="text-xs text-muted">Preview shows how it prints: pure black on white. Use a simple, high-contrast logo.</p>
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between"><h3 className="font-semibold">Payment QR</h3><Switch label="Show QR on bill" checked={b.show_qr} onChange={(v) => setB({ ...b, show_qr: v })} /></div>
          <div className="grid h-36 place-items-center rounded-2xl border border-dashed border-line bg-white p-3">
            {qr ? <img src={qr} alt="Payment QR" className="h-full" style={{ imageRendering: "pixelated" }} /> : <span className="text-center text-sm text-muted">No QR yet</span>}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => qrRef.current?.click()} data-testid="upload-qr"><ImagePlus className="h-4 w-4" />Upload QR picture</Button>
            {b.qr_bw && <Button variant="ghost" size="sm" aria-label="Remove QR" onClick={() => remove("qr")}><Trash2 className="h-4 w-4" /></Button>}
            <input ref={qrRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" data-testid="qr-input" onChange={(e) => upload("qr", e.target.files?.[0])} />
          </div>
          <Input label="…or type a link / text to make the QR" placeholder="e.g. your Raast / payment link" value={b.qr_text} onChange={(e) => setB({ ...b, qr_text: e.target.value })} hint="Used only when no QR picture is uploaded." />
        </section>
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between"><h3 className="font-semibold">Account numbers</h3><Switch label="Show accounts on bill" checked={b.show_accounts} onChange={(v) => setB({ ...b, show_accounts: v })} /></div>
        {b.accounts.map((a, i) => (
          <div key={i} className="grid gap-2 sm:grid-cols-[1fr_1.2fr_1.4fr_auto]" data-testid={`acc-${i}`}>
            <Input aria-label="Bank or wallet" placeholder="JazzCash / Meezan" value={a.label} onChange={(e) => setAcc(i, "label", e.target.value)} />
            <Input aria-label="Account title" placeholder="Account title" value={a.title} onChange={(e) => setAcc(i, "title", e.target.value)} />
            <Input aria-label="Account number" placeholder="Number / IBAN" value={a.number} onChange={(e) => setAcc(i, "number", e.target.value)} />
            <Button variant="ghost" aria-label="Remove account" onClick={() => setB({ ...b, accounts: b.accounts.filter((_, j) => j !== i) })}><Trash2 className="h-4 w-4" /></Button>
          </div>
        ))}
        {b.accounts.length < 6 && <button type="button" onClick={() => setB({ ...b, accounts: [...b.accounts, { label: "", title: "", number: "" }] })} className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand" data-testid="add-account"><Plus className="h-4 w-4" />Add account</button>}
      </section>

      <Input label="Line at the bottom of the bill" placeholder="Thank you! Please visit again." value={b.footer} onChange={(e) => setB({ ...b, footer: e.target.value })} maxLength={200} />
      <div className="flex flex-wrap gap-2">
        <Button loading={busy} onClick={save} data-testid="save-branding">Save bill settings</Button>
        <Button variant="secondary" onClick={() => window.dispatchEvent(new Event("dinex:test-bill"))}><Printer className="h-4 w-4" />Print a test bill</Button>
      </div>
      <TestBill b={b} name={me?.organization?.name ?? ""} location={location?.name ?? ""} address={location?.address} />
    </Card>
  );
}

import { printReceipt } from "@/lib/receipt";
import type { Order } from "@/lib/types";
function TestBill({ b, name, location, address }: { b: Branding; name: string; location: string; address?: string }) {
  const { currency } = useAuth();
  useEffect(() => {
    const h = () => {
      const o = { id: 0, order_number: "TEST-0001", location: 0, location_name: location, order_type: "TAKEAWAY", order_type_display: "Takeaway", table: null, customer_name: "", customer_phone: "", delivery_address: "", waiter: null, waiter_name: null, rider: null, rider_name: null, dispatched_at: null, delivered_at: null,
        subtotal: "700.00", tax: "70.00", service_charge: "0", discount: "0", total_amount: "770.00", status: "COMPLETED", status_display: "Completed", payment_status: "PAID", notes: "", created_at: new Date().toISOString(),
        items: [{ id: 1, product_name: "Zinger Burger", variant_name: "Regular", quantity: 1, unit_price: "500.00", total_price: "500.00" }, { id: 2, product_name: "Fries", variant_name: "Regular", quantity: 1, unit_price: "200.00", total_price: "200.00" }] } as unknown as Order;
      printReceipt(o, { business: name, location, address, currency, branding: b });
    };
    window.addEventListener("dinex:test-bill", h); return () => window.removeEventListener("dinex:test-bill", h);
  }, [b, name, location, address, currency]);
  return null;
}
