"use client";
import { useState } from "react";
import { KeyRound, LogOut, Mail } from "lucide-react";
import { Button, Input, Modal, useAction } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

/** My account: who I am, change my password, sign out. */
export function AccountModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { me, logout, reload } = useAuth();
  const { run, busy } = useAction();
  const [f, setF] = useState({ cur: "", next: "", again: "" });
  const [em, setEm] = useState({ email: "", pw: "", code: "", sent: false });
  async function sendCode() {
    const r = await run(() => api.post("/auth/email/request/", { email: em.email.trim(), current_password: em.pw }), "Code sent. Check your email.");
    if (r) setEm({ ...em, sent: true });
  }
  async function confirmEmail() {
    const r = await run(() => api.post("/auth/email/confirm/", { code: em.code.trim() }), "Email confirmed");
    if (r) { setEm({ email: "", pw: "", code: "", sent: false }); await reload(); }
  }
  const mismatch = f.again !== "" && f.next !== f.again;
  async function save() {
    const r = await run(() => api.post("/auth/change-password/", { current_password: f.cur, new_password: f.next }), "Password changed");
    if (r) { setF({ cur: "", next: "", again: "" }); onClose(); }
  }
  if (!me) return null;
  return (
    <Modal open={open} onClose={onClose} title="My account" width="max-w-md">
      <div className="space-y-5">
        <div className="flex items-center gap-3 rounded-2xl bg-sunken p-3.5">
          <div className="grid h-11 w-11 place-items-center rounded-full bg-brand text-lg font-bold text-white dark:text-[#04201a]">{(me.first_name || me.username)[0]?.toUpperCase()}</div>
          <div className="min-w-0"><p className="truncate font-semibold">{[me.first_name, me.last_name].filter(Boolean).join(" ") || me.username}</p><p className="truncate text-xs text-muted">@{me.username}{me.email ? ` · ${me.email}` : ""}</p></div>
        </div>
        <section className="space-y-3 rounded-2xl border border-line p-3.5" data-testid="email-section">
          <h3 className="flex items-center gap-2 text-sm font-bold"><Mail className="h-4 w-4" />Email for password reset</h3>
          <p className="text-sm text-muted">Codes are sent to <b className="text-ink" data-testid="cur-email">{me.email || "no email yet"}</b>. To change it, enter the new email. We will send a code there to confirm it is yours.</p>
          {!em.sent ? (
            <>
              <Input label="New email" type="email" autoComplete="email" data-testid="em-new" value={em.email} onChange={(e) => setEm({ ...em, email: e.target.value })} />
              <Input label="Your current password" type="password" autoComplete="current-password" data-testid="em-pw" value={em.pw} onChange={(e) => setEm({ ...em, pw: e.target.value })} />
              <Button variant="secondary" className="w-full" loading={busy} disabled={!em.email.includes("@") || !em.pw} onClick={sendCode} data-testid="em-send">Send code to this email</Button>
            </>
          ) : (
            <>
              <Input label={`6-digit code sent to ${em.email}`} inputMode="numeric" maxLength={6} data-testid="em-code" value={em.code} onChange={(e) => setEm({ ...em, code: e.target.value.replace(/\D/g, "") })} />
              <Button className="w-full" loading={busy} disabled={em.code.length !== 6} onClick={confirmEmail} data-testid="em-confirm">Confirm email</Button>
              <button type="button" className="w-full text-center text-xs font-semibold text-brand" onClick={() => setEm({ ...em, sent: false, code: "" })}>Use a different email</button>
            </>
          )}
        </section>
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); if (!mismatch && f.next) save(); }}>
          <h3 className="flex items-center gap-2 text-sm font-bold"><KeyRound className="h-4 w-4" />Change password</h3>
          <Input label="Current password" type="password" autoComplete="current-password" data-testid="pw-cur" value={f.cur} onChange={(e) => setF({ ...f, cur: e.target.value })} />
          <Input label="New password" type="password" autoComplete="new-password" hint="At least 8 characters, not too common" data-testid="pw-new" value={f.next} onChange={(e) => setF({ ...f, next: e.target.value })} />
          <Input label="New password again" type="password" autoComplete="new-password" data-testid="pw-again" error={mismatch ? "Passwords do not match" : undefined} value={f.again} onChange={(e) => setF({ ...f, again: e.target.value })} />
          <Button type="submit" className="w-full" loading={busy} disabled={!f.cur || !f.next || mismatch || !f.again} data-testid="pw-save">Update password</Button>
        </form>
        <Button variant="secondary" className="w-full" onClick={logout} data-testid="account-logout"><LogOut className="h-4 w-4" />Sign out</Button>
      </div>
    </Modal>
  );
}
