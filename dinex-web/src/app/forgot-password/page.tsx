"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ArrowLeft, MailCheck } from "lucide-react";
import { Button, Input, useToast } from "@/components/ui";
import { Logo } from "@/components/Logo";
import { api } from "@/lib/api";

/** Forgot password: 1) tell us your username or email, 2) type the 6-digit code from your email and choose a new password. */
export default function ForgotPasswordPage() {
  const router = useRouter();
  const toast = useToast();
  const [step, setStep] = useState<1 | 2>(1);
  const [ident, setIdent] = useState("");
  const [code, setCode] = useState("");
  const [pw, setPw] = useState("");
  const [again, setAgain] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function ask(e: FormEvent) {
    e.preventDefault(); setBusy(true); setErr("");
    try { await api.post("/auth/forgot-password/", { identifier: ident.trim() }); setStep(2); } catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  }
  async function reset(e: FormEvent) {
    e.preventDefault(); setBusy(true); setErr("");
    try { await api.post("/auth/reset-password/", { identifier: ident.trim(), code: code.trim(), new_password: pw }); toast.ok("Password changed. Please sign in."); router.replace("/login"); }
    catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  }
  const mismatch = again !== "" && pw !== again;

  return (
    <main className="grid min-h-dvh place-items-center bg-canvas p-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center gap-3"><Logo className="h-10 w-10" /><span className="font-display text-2xl font-extrabold">DineX</span></div>
        {step === 1 ? (
          <form onSubmit={ask} className="space-y-5">
            <div><h1 className="font-display text-3xl font-extrabold tracking-tight">Forgot password?</h1>
              <p className="mt-1.5 text-sm text-muted">Enter your username or email. We will email you a 6-digit code.</p></div>
            <Input label="Username or email" autoFocus required value={ident} onChange={(e) => setIdent(e.target.value)} data-testid="fp-ident" />
            {err && <p role="alert" className="rounded-xl bg-bad-soft px-3 py-2.5 text-sm font-medium text-bad">{err}</p>}
            <Button type="submit" size="lg" className="w-full" loading={busy} disabled={!ident.trim()} data-testid="fp-send">Send code</Button>
          </form>
        ) : (
          <form onSubmit={reset} className="space-y-4">
            <div><h1 className="font-display text-3xl font-extrabold tracking-tight">Check your email</h1>
              <p className="mt-2 flex gap-2 rounded-xl bg-brand-soft p-3 text-sm text-brand"><MailCheck className="mt-0.5 h-4 w-4 shrink-0" />If this account has an email, we sent a 6-digit code. It works for 10 minutes.</p></div>
            <Input label="6-digit code" inputMode="numeric" autoComplete="one-time-code" maxLength={6} autoFocus required value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} data-testid="fp-code" />
            <Input label="New password" type="password" autoComplete="new-password" required hint="At least 8 characters, not too common" value={pw} onChange={(e) => setPw(e.target.value)} data-testid="fp-new" />
            <Input label="New password again" type="password" autoComplete="new-password" required value={again} error={mismatch ? "Passwords do not match" : undefined} onChange={(e) => setAgain(e.target.value)} data-testid="fp-again" />
            {err && <p role="alert" className="rounded-xl bg-bad-soft px-3 py-2.5 text-sm font-medium text-bad" data-testid="fp-error">{err}</p>}
            <Button type="submit" size="lg" className="w-full" loading={busy} disabled={code.length !== 6 || !pw || mismatch || !again} data-testid="fp-reset">Change password</Button>
            <button type="button" className="w-full text-center text-sm font-semibold text-brand" onClick={() => { setStep(1); setCode(""); setErr(""); }}>Did not get it? Send a new code</button>
          </form>
        )}
        <Link href="/login" className="mt-8 inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink"><ArrowLeft className="h-4 w-4" />Back to sign in</Link>
      </div>
    </main>
  );
}
