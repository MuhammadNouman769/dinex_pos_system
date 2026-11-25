"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Button, Input } from "@/components/ui";
import { Logo } from "@/components/Logo";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

const TICKET = [
  { q: 2, name: "Chicken Karahi (half)", price: "1,900" },
  { q: 4, name: "Garlic Naan", price: "480" },
  { q: 1, name: "Mint Raita", price: "150" },
  { q: 3, name: "Doodh Patti", price: "540" },
];

export default function LoginPage() {
  const { me, login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { if (me) router.replace(me.role === "PLATFORM" ? "/admin" : "/dashboard"); }, [me, router]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError("");
    try { await login(username.trim(), password); }
    catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Wrong username or password." : err instanceof Error ? err.message : "Could not sign in.");
    } finally { setBusy(false); }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      <section className="relative hidden overflow-hidden bg-side p-12 text-white lg:flex lg:flex-col lg:justify-between xl:p-14">
        <div className="absolute -left-32 top-1/3 h-[28rem] w-[28rem] rounded-full bg-brand/25 blur-[110px]" />
        <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-accent/15 blur-[100px]" />
        <div className="relative flex items-center gap-3"><Logo className="h-11 w-11" /><span className="font-display text-2xl font-extrabold tracking-tight">DineX</span></div>

        <div className="relative grid items-center gap-10 xl:grid-cols-[1fr_16rem]">
          <div className="max-w-md">
            <h1 className="font-display text-4xl font-extrabold leading-[1.1] xl:text-[2.6rem] tracking-tight">Every order, bill and bag of flour, on one screen.</h1>
            <p className="mt-5 text-lg leading-relaxed text-white/70">Take orders at the counter, send them to the kitchen, and watch stock fall as dishes sell. It keeps working when the internet drops.</p>
          </div>

          <div className="ticket-edge mx-auto w-full max-w-[17rem] rotate-[2.5deg] bg-[#fbfaf5] px-5 pb-6 pt-5 font-mono text-[12.5px] text-[#1c2622] shadow-pop" aria-hidden>
            <p className="text-center text-sm font-bold">KARACHI GRILL</p>
            <p className="text-center text-[11px] text-[#5b6862]">Table 7 · Order #0142</p>
            <div className="my-3 border-t border-dashed border-[#9aa6a0]" />
            <ul className="space-y-1.5">
              {TICKET.map((t) => (
                <li key={t.name} className="flex justify-between gap-2"><span>{t.q}× {t.name}</span><span className="num">{t.price}</span></li>
              ))}
            </ul>
            <div className="my-3 border-t border-dashed border-[#9aa6a0]" />
            <p className="flex justify-between text-sm font-bold"><span>TOTAL</span><span className="num">PKR 3,070</span></p>
            <p className="mt-2 text-center text-[11px] text-[#5b6862]">Saved · syncs when online</p>
          </div>
        </div>

        <p className="relative text-sm text-white/50">© XverLabs</p>
      </section>

      <section className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-3 lg:hidden"><Logo className="h-10 w-10" /><span className="font-display text-2xl font-extrabold">DineX</span></div>
          <form onSubmit={submit} className="space-y-5">
            <div>
              <h2 className="font-display text-3xl font-extrabold tracking-tight">Welcome back</h2>
              <p className="mt-1.5 text-sm text-muted">Sign in to your restaurant.</p>
            </div>
            <Input label="Username" autoComplete="username" autoFocus required value={username} onChange={(e) => setUsername(e.target.value)} />
            <div className="relative">
              <Input label="Password" type={show ? "text" : "password"} autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} className="pr-12" />
              <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? "Hide password" : "Show password"} className="absolute bottom-0 right-0 grid h-11 w-11 place-items-center text-muted hover:text-ink">
                {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {error && <p role="alert" className="rounded-xl bg-bad-soft px-3 py-2.5 text-sm font-medium text-bad">{error}</p>}
            <Button type="submit" size="lg" loading={busy} className="w-full">Sign in</Button>
            <p className="text-center text-sm"><Link href="/forgot-password" data-testid="forgot-link" className="font-semibold text-brand hover:underline">Forgot password?</Link></p>
          </form>
          <div className="mt-8 rounded-2xl border border-line bg-surface p-4 text-center text-sm shadow-card">
            <p className="text-muted">New restaurant?</p>
            <Link href="/" className="mt-0.5 inline-block font-semibold text-brand hover:underline">Start your 14-day free trial</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
