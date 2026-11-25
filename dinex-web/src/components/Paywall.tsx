"use client";
import Link from "next/link";
import { Lock } from "lucide-react";
import { useAuth } from "@/lib/auth";

/** Shown instead of the app when the trial/subscription is over. Billing stays reachable so the owner can pay. */
export function Paywall() {
  const { me } = useAuth();
  const s = me?.subscription;
  return (
    <div className="mx-auto mt-10 max-w-lg rounded-3xl border border-line bg-surface p-8 text-center shadow-card">
      <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-brand-soft text-brand"><Lock className="h-7 w-7" /></div>
      <h2 className="font-display text-2xl font-extrabold">{s?.status === "TRIAL" ? "Your free trial has ended" : "Subscription paused"}</h2>
      <p className="mt-2 text-sm text-muted">{me?.is_owner ? "Your data is safe. Send your subscription payment and DineX switches back on as soon as we confirm it." : "Please ask the restaurant owner to renew the DineX subscription. Your data is safe."}</p>
      {me?.is_owner && <Link href="/billing" className="mt-6 inline-flex min-h-[48px] items-center rounded-xl bg-brand-gradient px-6 font-semibold text-white dark:text-[#04201a]">Choose plan &amp; pay</Link>}
    </div>
  );
}
