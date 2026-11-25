"use client";
import Link from "next/link";
import type { ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { cn } from "@/components/ui";

/** Frame for the pages a visitor sees before having an account (terms, plans, signup). */
export function PublicShell({ children, wide = false, step }: { children: ReactNode; wide?: boolean; step?: 1 | 2 | 3 }) {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-bg">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-[420px] bg-[radial-gradient(60%_60%_at_50%_0%,rgb(var(--brand)/0.14),transparent)]" />
      <header className="relative mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-4 pt-[max(1rem,env(safe-area-inset-top))] sm:px-6">
        <Link href="/" className="flex items-center gap-2.5"><Logo className="h-9 w-9" /><span className="font-display text-xl font-extrabold tracking-tight">DineX</span></Link>
        {step && (
          <ol className="hidden items-center gap-2 text-xs font-semibold text-muted sm:flex" aria-label="Progress">
            {["Terms", "Choose plan", "Your restaurant"].map((l, i) => (
              <li key={l} className="flex items-center gap-2">
                <span className={cn("grid h-6 w-6 place-items-center rounded-full text-[11px]", i + 1 <= step ? "bg-brand text-white dark:text-[#04201a]" : "bg-sunken")}>{i + 1}</span>
                <span className={cn(i + 1 === step && "text-ink")}>{l}</span>
                {i < 2 && <span className="h-px w-6 bg-line" />}
              </li>
            ))}
          </ol>
        )}
        <Link href="/login" className="inline-flex min-h-[44px] items-center rounded-xl border border-line bg-surface px-4 text-sm font-semibold shadow-sm hover:bg-sunken">Sign in</Link>
      </header>
      <main className={cn("relative mx-auto px-4 pb-16 sm:px-6", wide ? "max-w-6xl" : "max-w-3xl")}>{children}</main>
      <footer className="relative pb-[max(1.5rem,env(safe-area-inset-bottom))] text-center text-xs text-muted">© XverLabs · <Link href="/terms" className="underline">Terms of Use</Link></footer>
    </div>
  );
}

/** Has this visitor agreed to the current Terms on this device? */
export function agreedToTerms(version: string, key: string): boolean {
  try { const v = JSON.parse(localStorage.getItem(key) || "null"); return v?.version === version; } catch { return false; }
}
