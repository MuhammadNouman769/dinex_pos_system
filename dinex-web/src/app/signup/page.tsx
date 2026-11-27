"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState, type FormEvent } from "react";
import { Eye, EyeOff } from "lucide-react";
import { agreedToTerms, PublicShell } from "@/components/public/PublicShell";
import { Button, Input, Spinner, Textarea } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, ApiError, tokens, money } from "@/lib/api";
import { FALLBACK_PLANS } from "@/lib/plans";
import { TERMS_KEY, TERMS_VERSION } from "@/lib/terms";
import type { PublicPlan } from "@/lib/types";

const EMPTY = { restaurant_name: "", branch_name: "", address: "", phone: "", owner_name: "", email: "", username: "", password: "" };

function SignupForm() {
  const { me, loading, reload } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const code = params.get("plan") ?? "";
  const [plan, setPlan] = useState<PublicPlan | null>(null);
  const [f, setF] = useState(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const created = useRef(false);   // after signing up we go to /setup ourselves, not to the dashboard

  useEffect(() => {
    if (loading) return;
    if (me) { if (!created.current) router.replace("/dashboard"); return; }
    if (!agreedToTerms(TERMS_VERSION, TERMS_KEY)) { router.replace("/start"); return; }
    api.get<{ plans: PublicPlan[] }>("/public/plans/").then((d) => d.plans).catch(() => FALLBACK_PLANS)
      .then((list) => { const p = list.find((x) => x.code === code); if (!p) router.replace("/plans"); else setPlan(p); });
  }, [me, loading, code, router]);

  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setErrors({}); setGeneral("");
    try {
      const t = await api.post<{ access: string; refresh: string }>("/public/signup/", { ...f, plan: code, accept_terms: true });
      created.current = true;
      tokens.set(t.access, t.refresh);
      await reload();
      router.replace("/setup");
    } catch (err) {
      if (err instanceof ApiError && err.status === 400 && err.data && typeof err.data === "object") {
        const out: Record<string, string> = {};
        for (const [k, v] of Object.entries(err.data as Record<string, unknown>)) out[k] = Array.isArray(v) ? v.join(" ") : String(v);
        setErrors(out);
        if (out.accept_terms) { setGeneral(out.accept_terms); }
      } else setGeneral(err instanceof ApiError && err.status === 429 ? "Too many attempts. Please try again in a little while." : err instanceof Error ? err.message : "Could not create your account.");
    } finally { setBusy(false); }
  }

  if (!plan) return <div className="grid min-h-[50vh] place-items-center"><Spinner /></div>;
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <form onSubmit={submit} className="space-y-6 rounded-3xl border border-line bg-surface p-5 shadow-card sm:p-7" noValidate>
        <div>
          <h1 className="font-display text-2xl font-extrabold tracking-tight sm:text-3xl">Set up your restaurant</h1>
          <p className="mt-1 text-sm text-muted">Takes about a minute. Your free trial starts right away.</p>
        </div>
        <fieldset className="space-y-4"><legend className="mb-1 text-sm font-bold">Restaurant</legend>
          <Input label="Restaurant name" required autoFocus autoComplete="organization" value={f.restaurant_name} onChange={set("restaurant_name")} error={errors.restaurant_name} />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Branch name" placeholder="Main branch" value={f.branch_name} onChange={set("branch_name")} error={errors.branch_name} />
            <Input label="Restaurant phone" type="tel" inputMode="tel" required autoComplete="tel" placeholder="03XX XXXXXXX" value={f.phone} onChange={set("phone")} error={errors.phone} />
          </div>
          <Textarea label="Address" rows={2} required value={f.address} onChange={set("address")} />
          {errors.address && <p className="-mt-2 text-xs text-bad">{errors.address}</p>}
        </fieldset>
        <fieldset className="space-y-4"><legend className="mb-1 text-sm font-bold">Your login</legend>
          <Input label="Your name" required autoComplete="name" value={f.owner_name} onChange={set("owner_name")} error={errors.owner_name} />
          <Input label="Email" type="email" inputMode="email" required autoComplete="email" value={f.email} onChange={set("email")} error={errors.email} />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Username" required autoComplete="username" autoCapitalize="none" value={f.username} onChange={set("username")} error={errors.username} hint="Letters, numbers, . _ -" />
            <div className="relative">
              <Input label="Password" type={show ? "text" : "password"} required autoComplete="new-password" value={f.password} onChange={set("password")} error={errors.password} className="pr-11" hint="At least 8 characters" />
              <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? "Hide password" : "Show password"} className="absolute right-0 top-6 grid h-10 w-10 place-items-center text-muted hover:text-ink">{show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>
            </div>
          </div>
        </fieldset>
        {general && <p role="alert" className="rounded-xl bg-bad-soft px-3 py-2 text-sm text-bad">{general}</p>}
        <Button type="submit" size="lg" className="w-full" loading={busy}>Start my {14}-day free trial</Button>
        <p className="text-center text-xs text-muted">By continuing you confirm you agreed to the <Link href="/terms" target="_blank" className="underline">Terms of Use</Link>.</p>
      </form>

      <aside className="h-fit rounded-3xl border border-brand/40 bg-brand-soft/60 p-5 lg:sticky lg:top-6">
        <p className="text-xs font-bold uppercase tracking-wide text-brand">Your plan</p>
        <h2 className="mt-1 font-display text-2xl font-extrabold">{plan.name}</h2>
        <p className="num mt-1 text-xl font-bold">{money(plan.price_monthly)}<span className="text-sm font-medium text-muted"> / month</span></p>
        <p className="mt-1 text-sm font-semibold text-good">Free for 14 days, nothing to pay today</p>
        <ul className="mt-4 space-y-1.5 text-sm text-muted"><li>{plan.max_locations} {plan.max_locations === 1 ? "branch" : "branches"}, {plan.max_users} staff accounts</li>{plan.features.slice(0, 4).map((x) => <li key={x}>{x}</li>)}</ul>
        <Link href="/plans" className="mt-4 inline-flex min-h-[44px] items-center text-sm font-semibold text-brand underline">Change plan</Link>
      </aside>
    </div>
  );
}

export default function SignupPage() {
  return <PublicShell wide step={3}><Suspense fallback={<Spinner />}><SignupForm /></Suspense></PublicShell>;
}
