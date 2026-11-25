"use client";
import { useState } from "react";
import { imgUrl } from "@/lib/api";
import { cn } from "@/components/ui";

const HUES = [152, 28, 12, 200, 42, 330, 262];
/** Dish / deal picture; falls back to a soft coloured tile with the first letters when there is no picture (or it cannot load offline). */
export function FoodImage({ src, name, className }: { src?: string | null; name: string; className?: string }) {
  const [bad, setBad] = useState(false);
  const url = imgUrl(src);
  if (url && !bad) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} alt="" loading="lazy" decoding="async" onError={() => setBad(true)} className={cn("h-full w-full object-cover", className)} />;
  }
  const hue = HUES[[...name].reduce((a, c) => a + c.charCodeAt(0), 0) % HUES.length];
  return (
    <div aria-hidden className={cn("grid h-full w-full place-items-center font-display text-2xl font-extrabold", className)}
      style={{ background: `linear-gradient(135deg, hsl(${hue} 60% 92%), hsl(${hue} 55% 82%))`, color: `hsl(${hue} 45% 28%)` }}>
      {name.trim().slice(0, 2).toUpperCase()}
    </div>
  );
}
