"use client";
import clsx from "clsx";
import { Loader2, X, CheckCircle2, AlertCircle } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useId, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

export const cn = clsx;

/* ───────── Button ───────── */
type Variant = "primary" | "secondary" | "ghost" | "danger";
const variants: Record<Variant, string> = {
  primary: "bg-brand-gradient text-white shadow-sm hover:brightness-110 dark:text-[#06231b]",
  secondary: "bg-surface text-ink border border-line shadow-sm hover:bg-sunken",
  ghost: "text-ink hover:bg-sunken",
  danger: "bg-bad-soft text-bad hover:bg-bad hover:text-white",
};
export function Button({ variant = "primary", size = "md", loading, className, children, disabled, ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" | "lg"; loading?: boolean }) {
  return (
    <button
      disabled={disabled || loading}
      className={cn(
        "inline-flex select-none items-center justify-center gap-2 rounded-xl font-semibold transition duration-150 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/60 focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
        size === "sm" && "h-9 px-3 text-sm", size === "md" && "h-11 px-4 text-sm", size === "lg" && "h-12 px-6 text-base",
        variants[variant], className)}
      {...rest}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

/* ───────── Card ───────── */
export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("rounded-2xl border border-line/80 bg-surface shadow-card", className)}>{children}</div>;
}
export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="font-display text-2xl font-extrabold tracking-tight md:text-[1.75rem]">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

/* ───────── Form fields ───────── */
const fieldBase = "w-full rounded-xl border border-line bg-surface px-3.5 text-sm text-ink transition placeholder:text-muted/70 hover:border-muted/50 focus:border-brand focus:outline-none focus:ring-4 focus:ring-brand/15 disabled:bg-sunken disabled:text-muted";
export function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: (id: string) => ReactNode }) {
  const id = useId();
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-[13px] font-semibold text-ink/80">{label}</label>
      {children(id)}
      {error ? <p className="text-xs text-bad">{error}</p> : hint ? <p className="text-xs text-muted">{hint}</p> : null}
    </div>
  );
}
export function Input({ label, hint, error, className, ...rest }: InputHTMLAttributes<HTMLInputElement> & { label?: string; hint?: string; error?: string }) {
  const input = (id?: string) => <input id={id} className={cn(fieldBase, "h-11", className)} {...rest} />;
  return label ? <Field label={label} hint={hint} error={error}>{(id) => input(id)}</Field> : input();
}
export function Select({ label, hint, className, children, ...rest }: SelectHTMLAttributes<HTMLSelectElement> & { label?: string; hint?: string }) {
  const el = (id?: string) => <select id={id} className={cn(fieldBase, "h-11", className)} {...rest}>{children}</select>;
  return label ? <Field label={label} hint={hint}>{(id) => el(id)}</Field> : el();
}
export function Textarea({ label, className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string }) {
  const el = (id?: string) => <textarea id={id} className={cn(fieldBase, "py-2.5", className)} {...rest} />;
  return label ? <Field label={label}>{(id) => el(id)}</Field> : el();
}

/* ───────── Badge / states ───────── */
const tones = { neutral: "bg-sunken text-muted", brand: "bg-brand-soft text-brand", good: "bg-good-soft text-good", warn: "bg-warn-soft text-warn", bad: "bg-bad-soft text-bad" };
export function Badge({ tone = "neutral", children, className }: { tone?: keyof typeof tones; children: ReactNode; className?: string }) {
  return <span className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold", tones[tone], className)}>{children}</span>;
}
export function Spinner({ label }: { label?: string }) {
  return <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted"><Loader2 className="h-5 w-5 animate-spin" />{label}</div>;
}
export function EmptyState({ icon, title, hint, action }: { icon?: ReactNode; title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-line bg-surface/50 px-6 py-12 text-center">
      {icon && <div className="mb-1 grid h-12 w-12 place-items-center rounded-2xl bg-sunken text-muted">{icon}</div>}
      <p className="font-display font-bold">{title}</p>
      {hint && <p className="max-w-sm text-sm text-muted">{hint}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

/* ───────── Modal ───────── */
export function Modal({ open, onClose, title, children, width = "max-w-lg" }: { open: boolean; onClose: () => void; title: string; children: ReactNode; width?: string }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-side/60 p-0 backdrop-blur-sm sm:items-center sm:p-4" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} onMouseDown={(e) => e.stopPropagation()}
        className={cn("animate-pop max-h-[92vh] w-full overflow-y-auto rounded-t-3xl bg-surface shadow-pop sm:rounded-2xl", width)}>
        <div className="sticky top-0 flex items-center justify-between border-b border-line bg-surface px-5 py-4">
          <h2 className="font-display text-lg font-extrabold">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="grid h-10 w-10 place-items-center rounded-xl text-muted hover:bg-sunken hover:text-ink"><X className="h-5 w-5" /></button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

/* ───────── Toasts ───────── */
interface Toast { id: number; kind: "ok" | "err"; text: string }
const ToastCtx = createContext<{ ok: (t: string) => void; err: (t: string) => void } | null>(null);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((kind: Toast["kind"], text: string) => {
    const id = Date.now() + Math.random();
    setItems((s) => [...s, { id, kind, text }]);
    setTimeout(() => setItems((s) => s.filter((t) => t.id !== id)), kind === "err" ? 6000 : 3500);
  }, []);
  const api = { ok: (t: string) => push("ok", t), err: (t: string) => push("err", t) };
  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed bottom-20 right-4 z-[60] md:bottom-4 flex w-[min(92vw,380px)] flex-col gap-2">
        {items.map((t) => (
          <div key={t.id} role="status" className={cn("animate-pop pointer-events-auto flex items-start gap-2 rounded-xl border px-4 py-3 text-sm font-medium shadow-pop",
            t.kind === "ok" ? "border-good/30 bg-good-soft text-good" : "border-bad/30 bg-bad-soft text-bad")}>
            {t.kind === "ok" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />}
            <span>{t.text}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
export function useToast() {
  const v = useContext(ToastCtx);
  if (!v) throw new Error("useToast outside ToastProvider");
  return v;
}

/** Run an async action, show its error as a toast. Returns undefined on failure. */
export function useAction() {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const run = useCallback(async <T,>(fn: () => Promise<T>, success?: string): Promise<T | undefined> => {
    setBusy(true);
    try {
      const r = await fn();
      if (success) toast.ok(success);
      return r;
    } catch (e) {
      toast.err(e instanceof Error ? e.message : "Something went wrong.");
      return undefined;
    } finally {
      setBusy(false);
    }
  }, [toast]);
  return { run, busy };
}


/* ───────── Additions ───────── */
export function Stat({ label, value, icon, tone = "brand", hint, className }: { label: string; value: ReactNode; icon?: ReactNode; tone?: keyof typeof tones; hint?: string; className?: string }) {
  return (
    <Card className={cn("p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-muted">{label}</p>
        {icon && <span className={cn("grid h-9 w-9 shrink-0 place-items-center rounded-xl", tones[tone])}>{icon}</span>}
      </div>
      <p className="num mt-2 font-display text-3xl font-extrabold tracking-tight">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </Card>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("skeleton rounded-xl", className)} />;
}

export function Segmented<T extends string>({ value, onChange, options, className }: { value: T; onChange: (v: T) => void; options: { value: T; label: ReactNode }[]; className?: string }) {
  return (
    <div role="tablist" className={cn("inline-flex rounded-xl bg-sunken p-1", className)}>
      {options.map((o) => (
        <button key={o.value} role="tab" aria-selected={value === o.value} onClick={() => onChange(o.value)}
          className={cn("min-h-[40px] rounded-lg px-4 text-sm font-semibold transition", value === o.value ? "bg-surface text-brand shadow-sm" : "text-muted hover:text-ink")}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Tabs<T extends string>({ value, onChange, tabs, className }: { value: T; onChange: (v: T) => void; tabs: { value: T; label: ReactNode; count?: number }[]; className?: string }) {
  return (
    <div role="tablist" className={cn("flex gap-1 overflow-x-auto border-b border-line scroll-thin", className)}>
      {tabs.map((t) => (
        <button key={t.value} role="tab" aria-selected={value === t.value} onClick={() => onChange(t.value)}
          className={cn("-mb-px flex min-h-[44px] items-center gap-2 whitespace-nowrap border-b-2 px-4 text-sm font-semibold transition",
            value === t.value ? "border-brand text-brand" : "border-transparent text-muted hover:text-ink")}>
          {t.label}{t.count !== undefined && <span className="rounded-full bg-sunken px-2 py-0.5 text-xs">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Switch({ checked, onChange, label, disabled }: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} disabled={disabled} onClick={() => onChange(!checked)}
      className={cn("relative h-7 w-12 shrink-0 rounded-full transition disabled:opacity-50", checked ? "bg-brand" : "bg-line")}>
      <span className={cn("absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-all", checked ? "left-[22px]" : "left-0.5")} />
    </button>
  );
}
