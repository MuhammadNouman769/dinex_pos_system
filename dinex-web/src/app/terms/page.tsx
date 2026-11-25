import Link from "next/link";
import { PublicShell } from "@/components/public/PublicShell";
import { TERMS, TERMS_VERSION } from "@/lib/terms";

export const metadata = { title: "Terms of Use · DineX" };

export default function TermsPage() {
  return (
    <PublicShell>
      <article className="rounded-3xl border border-line bg-surface p-6 shadow-card sm:p-8">
        <h1 className="font-display text-3xl font-extrabold tracking-tight">Terms of Use</h1>
        <p className="mt-1 text-sm text-muted">DineX by XverLabs · version {TERMS_VERSION}</p>
        <div className="mt-6 space-y-5 text-sm leading-relaxed">
          {TERMS.map((s) => (<section key={s.title}><h2 className="font-bold">{s.title}</h2>{s.body.map((p) => <p key={p} className="mt-1 text-muted">{p}</p>)}</section>))}
        </div>
        <Link href="/" className="mt-8 inline-flex min-h-[44px] items-center rounded-xl bg-brand px-5 text-sm font-semibold text-white dark:text-[#04201a]">Back</Link>
      </article>
    </PublicShell>
  );
}
