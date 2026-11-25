"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Delete, LogIn, LogOut } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { Card, EmptyState, cn } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { fmtMin } from "@/lib/time";

interface Result { action: "IN" | "OUT"; employee: { name: string; role: string }; time: string; late_minutes: number; worked_minutes: number; overtime_minutes: number; early_leave_minutes: number }

export default function KioskPage() {
  const { me, location } = useAuth();
  const [pin, setPin] = useState("");
  const [now, setNow] = useState(new Date());
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { const t = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(t); }, []);
  const reset = useCallback(() => { setPin(""); setResult(null); setError(""); }, []);
  const submit = useCallback(async (value: string) => {
    if (!location || value.length < 4 || busy) return;
    setBusy(true); setError("");
    try {
      const r = await api.post<Result>("/staff/attendance/kiosk/", { location: location.id, pin: value });
      setResult(r); setPin("");
      timer.current = setTimeout(reset, 5000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not record. Try again."); setPin("");
      timer.current = setTimeout(reset, 3500);
    } finally { setBusy(false); }
  }, [location, busy, reset]);
  const press = useCallback((d: string) => { if (result) return; setError(""); setPin((p) => (p.length < 6 ? p + d : p)); }, [result]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (/^\d$/.test(e.key)) press(e.key);
      else if (e.key === "Backspace") setPin((p) => p.slice(0, -1));
      else if (e.key === "Enter") submit(pin);
    };
    window.addEventListener("keydown", onKey);
    return () => { window.removeEventListener("keydown", onKey); if (timer.current) clearTimeout(timer.current); };
  }, [press, submit, pin]);

  if (me && !me.organization) return <PlatformNotice />;
  if (!me?.can_operate_pos) return <EmptyState title="The kiosk runs on a branch login" hint="Sign in as a cashier or manager on the entrance tablet." />;
  const hour = now.getHours();

  return (
    <div className="mx-auto flex max-w-md flex-col items-center py-4">
      <p className="text-sm font-semibold text-muted">{location?.name}</p>
      <p className="mt-1 text-6xl font-bold tabular-nums tracking-tight">{now.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</p>
      <p className="mb-6 text-muted">{now.toLocaleDateString("en-PK", { weekday: "long", day: "numeric", month: "long" })}</p>

      {result ? (
        <Card className={cn("w-full p-8 text-center", result.action === "IN" ? "border-good/50" : "border-brand/50")}>
          <div className={cn("mx-auto grid h-16 w-16 place-items-center rounded-full text-white", result.action === "IN" ? "bg-good" : "bg-brand")}>{result.action === "IN" ? <LogIn className="h-8 w-8" /> : <LogOut className="h-8 w-8" />}</div>
          <p className="mt-4 text-2xl font-bold">{result.action === "IN" ? (hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening") : "Goodbye"}, {result.employee.name.split(" ")[0]}</p>
          <p className="text-muted">{result.employee.role} · checked <b>{result.action === "IN" ? "in" : "out"}</b> at {new Date(result.time).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</p>
          {result.action === "IN" && result.late_minutes > 0 && <p className="mt-3 rounded-xl bg-warn-soft px-3 py-2 text-sm font-semibold text-warn">Late by {fmtMin(result.late_minutes)}</p>}
          {result.action === "OUT" && <p className="mt-3 text-sm text-muted">Worked {fmtMin(result.worked_minutes)}{result.overtime_minutes > 0 && <span className="font-semibold text-good"> · overtime {fmtMin(result.overtime_minutes)}</span>}{result.early_leave_minutes > 0 && <span className="font-semibold text-warn"> · left {fmtMin(result.early_leave_minutes)} early</span>}</p>}
        </Card>
      ) : (
        <Card className="w-full p-6">
          <p className="mb-3 text-center text-sm text-muted">Type your PIN to check in or out</p>
          <div className="mb-5 flex justify-center gap-3" aria-label="PIN">{Array.from({ length: 6 }).map((_, i) => <span key={i} className={cn("h-3.5 w-3.5 rounded-full border-2", i < pin.length ? "border-brand bg-brand" : "border-line")} />)}</div>
          {error && <p role="alert" className="mb-4 rounded-xl bg-bad-soft px-3 py-2 text-center text-sm font-medium text-bad">{error}</p>}
          <div className="grid grid-cols-3 gap-3">
            {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) => <button key={d} onClick={() => press(d)} className="h-16 rounded-2xl bg-sunken text-2xl font-bold transition active:scale-95 hover:bg-line">{d}</button>)}
            <button onClick={() => setPin((p) => p.slice(0, -1))} aria-label="Delete" className="grid h-16 place-items-center rounded-2xl bg-sunken transition active:scale-95 hover:bg-line"><Delete className="h-6 w-6" /></button>
            <button onClick={() => press("0")} className="h-16 rounded-2xl bg-sunken text-2xl font-bold transition active:scale-95 hover:bg-line">0</button>
            <button onClick={() => submit(pin)} disabled={pin.length < 4 || busy} className="h-16 rounded-2xl bg-brand text-lg font-bold text-white transition active:scale-95 disabled:opacity-40">{busy ? "…" : "Go"}</button>
          </div>
        </Card>
      )}
    </div>
  );
}
