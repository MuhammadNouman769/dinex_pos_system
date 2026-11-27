"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Check, Sparkles } from "lucide-react";
import { agreedToTerms, PublicShell } from "@/components/public/PublicShell";
import { Button, Skeleton, cn } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import { FALLBACK_PLANS, POPULAR_PLAN } from "@/lib/plans";
import { TERMS_KEY, TERMS_VERSION } from "@/lib/terms";
import type { PublicPlan } from "@/lib/types";

export default function PlansPage() {
  const { me, loading } = useAuth();
  const router = useRouter();
  const [plans, setPlans] = useState<PublicPlan[] | null>(null);
  const [days, setDays] = useState(14);

  useEffect(() => {
    if (loading) return;
    if (me) { router.replace(me.role === "PLATFORM" ? "/admin" : "/billing"); return; }
    if (!agreedToTerms(TERMS_VERSION, TERMS_KEY)) { router.replace("/start"); return; }
    api.get<{ plans: PublicPlan[]; trial_days: number }>("/public/plans/")
      .then((d) => { setPlans(d.plans); setDays(d.trial_days); })
      .catch(() => setPlans(FALLBACK_PLANS));
  }, [me, loading, router]);

  return (
    <PublicShell wide step={2}>
      <div className="pb-8 pt-4 text-center sm:pt-8">
        <h1 className="font-display text-3xl font-extrabold tracking-tight sm:text-4xl">Pick your plan</h1>
        <p className="mx-auto mt-2 max-w-lg text-muted">Start free for {days} days on any plan. You can change it before the trial ends.</p>
      </div>
      <div className="grid gap-5 md:grid-cols-3 md:items-stretch">
        {!plans && [0, 1, 2].map((i) => <Skeleton key={i} className="h-[440px] rounded-3xl" />)}
        {plans?.map((p) => {
          const popular = p.code === POPULAR_PLAN;
          return (
            <article key={p.code} className={cn("relative flex flex-col rounded-3xl border bg-surface p-6 shadow-card transition hover:-translate-y-0.5", popular ? "border-brand ring-2 ring-brand/30 md:-mt-3 md:pb-9" : "border-line")}>
              {popular && <span className="absolute -top-3 left-1/2 inline-flex -translate-x-1/2 items-center gap-1 rounded-full bg-brand px-3 py-1 text-xs font-bold text-white dark:text-[#04201a]"><Sparkles className="h-3 w-3" />Most popular</span>}
              <h2 className="font-display text-xl font-extrabold">{p.name}</h2>
              <p className="mt-1 min-h-[2.5rem] text-sm text-muted">{p.description}</p>
              <p className="num mt-4 font-display text-4xl font-extrabold tracking-tight">{money(p.price_monthly)}<span className="text-sm font-medium text-muted"> / month</span></p>
              <p className="mt-1 text-sm font-semibold text-good">{days} days free first</p>
              <ul className="mt-5 flex-1 space-y-2.5 text-sm">
                <li className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-good" />{p.max_locations} {p.max_locations === 1 ? "branch" : "branches"} · {p.max_users} staff accounts</li>
                {p.features.map((f) => <li key={f} className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-good" />{f}</li>)}
              </ul>
              <Button size="lg" variant={popular ? "primary" : "secondary"} className="mt-6 w-full" onClick={() => router.push(`/signup?plan=${p.code}`)}>Start {days}-day free trial</Button>
            </article>
          );
        })}
      </div>
      <p className="mt-8 text-center text-sm text-muted">No card needed. After the trial you pay by JazzCash, Easypaisa or bank transfer and the system continues as soon as we confirm it.</p>
    </PublicShell>
  );
}
