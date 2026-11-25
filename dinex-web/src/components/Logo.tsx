import { useId } from "react";

export function Logo({ className = "h-8 w-8" }: { className?: string }) {
  const gid = useId().replace(/:/g, "");
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="rgb(var(--brand))" />
          <stop offset="1" stopColor="rgb(var(--brand-strong))" />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="12" fill={`url(#${gid})`} />
      <path d="M12.5 10.5v7a3 3 0 0 0 3 3v9M12.5 10.5v5.5M15.5 10.5v5.5M18.5 10.5v7a3 3 0 0 1-3 3" stroke="#fff" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <path d="M27.5 29.5v-19c-3.2 1.6-4.8 5.2-4.8 9.4 0 2.5 1.8 3.8 4.8 3.8" stroke="rgb(var(--accent))" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}
