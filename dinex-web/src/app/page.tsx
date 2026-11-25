"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, CloudOff, FileCheck2, ShieldCheck, Wallet } from "lucide-react";
import { agreedToTerms, PublicShell } from "@/components/public/PublicShell";
import { Button, Spinner, cn } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { TERMS, TERMS_KEY, TERMS_VERSION } from "@/lib/terms";

export default function Welcome() {
  const { me, loading } = useAuth();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [agree, setAgree] = useState(false);
  const [readAll, setReadAll] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (loading) return;
    if (me) { router.replace(me.role === "PLATFORM" ? "/admin" : "/dashboard"); return; }
    if (agreedToTerms(TERMS_VERSION, TERMS_KEY)) { router.replace("/plans"); return; }
    setReady(true);
  }, [me, loading, router]);

  const onScroll = () => {
    const el = box.current;
    if (el && el.scrollTop + el.clientHeight >= el.scrollHeight - 24) setReadAll(true);
  };
  useEffect(() => { const el = box.current; if (ready && el && el.scrollHeight <= el.clientHeight + 24) setReadAll(true); }, [ready]);

  function proceed() {
    try { localStorage.setItem(TERMS_KEY, JSON.stringify({ version: TERMS_VERSION, at: new Date().toISOString() })); } catch { /* private mode: still continue */ }
    try { sessionStorage.setItem("dinex_terms_ok", TERMS_VERSION); } catch { /* ignore */ }
    router.push("/plans");
  }

  if (!ready) return <div className="grid min-h-screen place-items-center"><Spinner /></div>;
  return (
    <PublicShell step={1}>
      <section className="pb-6 pt-4 text-center sm:pt-10">
        <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-xs font-semibold text-brand shadow-sm"><ShieldCheck className="h-3.5 w-3.5" />14-day free trial · no card needed</span>
        <h1 className="mx-auto mt-4 max-w-xl font-display text-3xl font-extrabold leading-tight tracking-tight sm:text-5xl">Run your restaurant from one screen.</h1>
        <p className="mx-auto mt-3 max-w-xl text-base text-muted sm:text-lg">POS, kitchen orders, recipe-based inventory, cash desk, staff and payroll. It keeps working even when the internet drops.</p>
        <ul className="mx-auto mt-5 flex max-w-xl flex-wrap justify-center gap-2 text-xs font-semibold text-muted">
          {[[CloudOff, "Works offline"], [Wallet, "Daily-wage payroll"], [FileCheck2, "Bills & reports"]].map(([I, t]) => { const Icon = I as typeof CloudOff; return <li key={t as string} className="inline-flex items-center gap-1.5 rounded-full bg-sunken px-3 py-1.5"><Icon className="h-3.5 w-3.5" />{t as string}</li>; })}
        </ul>
      </section>

      <section aria-labelledby="terms-h" className="rounded-3xl border border-line bg-surface p-4 shadow-card sm:p-6">
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 id="terms-h" className="font-display text-lg font-extrabold">Terms of Use</h2>
          <span className="text-xs text-muted">Version {TERMS_VERSION}</span>
        </div>
        <div ref={box} onScroll={onScroll} tabIndex={0} aria-label="Terms of Use text" className="scroll-thin h-64 space-y-4 overflow-y-auto rounded-2xl bg-sunken/70 p-4 text-sm leading-relaxed sm:h-72">
          {TERMS.map((s) => (
            <div key={s.title}><h3 className="font-bold">{s.title}</h3>{s.body.map((p) => <p key={p} className="mt-1 text-muted">{p}</p>)}</div>
          ))}
        </div>
        {!readAll && <p className="mt-2 text-xs text-muted">Scroll to the end of the terms to continue.</p>}
        <label className={cn("mt-4 flex min-h-[44px] cursor-pointer items-start gap-3 rounded-xl p-2 text-sm font-medium", !readAll && "pointer-events-none opacity-50")}>
          <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} disabled={!readAll} className="mt-0.5 h-5 w-5 shrink-0 accent-[rgb(var(--brand))]" />
          <span>I have read and agree to the Terms of Use.</span>
        </label>
        <Button size="lg" className="mt-3 w-full" disabled={!agree} onClick={proceed}>I agree, choose my plan <ArrowRight className="h-4 w-4" /></Button>
        <p className="mt-3 text-center text-sm text-muted">Already have an account? <Link href="/login" className="font-semibold text-brand underline">Sign in</Link></p>
      </section>
    </PublicShell>
  );
}
