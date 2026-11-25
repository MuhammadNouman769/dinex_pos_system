"use client";
import { Minus, Plus, Tag } from "lucide-react";
import { FoodImage } from "@/components/FoodImage";
import { cn } from "@/components/ui";

interface Props {
  name: string; image?: string | null; price: string; strike?: string; badge?: string;
  qty: number; deal?: boolean; testId: string; onAdd: () => void; onLess: () => void;
}

/** POS menu card: photo, name, price and a  − qty +  control. No description text. */
export function MenuCard({ name, image, price, strike, badge, qty, deal, testId, onAdd, onLess }: Props) {
  return (
    <div data-testid={testId} role="button" tabIndex={0} aria-label={`Add ${name}`}
      onClick={onAdd} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onAdd(); } }}
      className={cn(
        "group relative flex cursor-pointer select-none flex-col overflow-hidden rounded-[20px] bg-surface p-2 text-left outline-none ring-1 transition duration-200",
        "shadow-[0_1px_2px_rgb(0_0_0/0.04),0_6px_18px_-10px_rgb(0_0_0/0.16)] hover:-translate-y-0.5 hover:shadow-[0_14px_30px_-14px_rgb(0_0_0/0.28)] active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-brand",
        qty > 0 ? "ring-2 ring-brand" : deal ? "ring-accent/60" : "ring-line",
      )}>
      <div className="relative aspect-[4/3] w-full overflow-hidden rounded-2xl bg-sunken">
        <FoodImage src={image} name={name} className="transition duration-500 group-hover:scale-105" />
        {badge && <span className="absolute left-2 top-2 inline-flex items-center gap-1 rounded-full bg-accent px-2.5 py-1 text-[11px] font-extrabold uppercase tracking-wide text-black/80 shadow"><Tag className="h-3 w-3" />{badge}</span>}
      </div>
      <p className="mt-2.5 line-clamp-2 min-h-[2.4rem] px-1 font-display text-[15px] font-bold leading-tight text-ink">{name}</p>
      <div className="mt-1.5 flex flex-col gap-2 px-1 pb-1" onClick={(e) => e.stopPropagation()}>
        <div className="min-w-0">
          <span className="num block whitespace-nowrap text-[15px] font-extrabold leading-none text-ink">{price}</span>
          {strike && <span className="num mt-0.5 block text-xs font-medium leading-none text-muted line-through">{strike}</span>}
        </div>
        <div className={cn("flex w-full items-center justify-between rounded-full border p-0.5 transition", qty > 0 ? "border-brand bg-brand-soft" : "border-line bg-bg")}>
          <button type="button" aria-label={`Remove one ${name}`} disabled={qty === 0} onClick={onLess} className="grid h-8 w-8 place-items-center rounded-full text-ink hover:bg-sunken disabled:opacity-30"><Minus className="h-3.5 w-3.5" strokeWidth={2.6} /></button>
          <span className="num text-center text-sm font-extrabold" data-testid={`qty-${testId}`}>{qty}</span>
          <button type="button" aria-label={`Add one more ${name}`} onClick={onAdd} className="grid h-8 w-8 place-items-center rounded-full bg-brand text-white hover:bg-brand-strong"><Plus className="h-3.5 w-3.5" strokeWidth={2.6} /></button>
        </div>
      </div>
    </div>
  );
}
