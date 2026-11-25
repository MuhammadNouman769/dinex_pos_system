"use client";
import { useRef, useState } from "react";
import { Camera, Trash2 } from "lucide-react";
import { FoodImage } from "@/components/FoodImage";
import { useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { compressImage } from "@/lib/image";

/** Tap the picture to choose/take a photo; it is compressed, uploaded and the owner sees it at once. */
export function ImagePicker({ kind, id, src, name, onChanged, size = "h-16 w-16" }: { kind: "product" | "deal" | "category"; id: number; src?: string | null; name: string; onChanged: (url: string | null) => void; size?: string }) {
  const toast = useToast();
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  async function pick(file?: File) {
    if (!file) return;
    setBusy(true);
    try {
      const f = await compressImage(file);
      const fd = new FormData(); fd.append("image", f);
      const r = await api.upload<{ image: string | null }>(`/catalog/images/${kind}/${id}/`, fd);
      onChanged(r.image); toast.ok("Picture saved");
    } catch (e) { toast.err((e as Error).message); } finally { setBusy(false); if (ref.current) ref.current.value = ""; }
  }
  async function clear() {
    setBusy(true);
    try { await api.del(`/catalog/images/${kind}/${id}/`); onChanged(null); } catch (e) { toast.err((e as Error).message); } finally { setBusy(false); }
  }
  return (
    <div className="relative shrink-0">
      <button type="button" aria-label={`Change picture of ${name}`} onClick={() => ref.current?.click()} className={`group relative block overflow-hidden rounded-xl border border-line ${size}`}>
        <FoodImage src={src} name={name} />
        <span className="absolute inset-0 grid place-items-center bg-black/40 text-white opacity-0 transition group-hover:opacity-100 group-focus-visible:opacity-100"><Camera className="h-5 w-5" /></span>
        {busy && <span className="absolute inset-0 grid place-items-center bg-white/70 text-xs font-semibold text-ink">…</span>}
      </button>
      {src && !busy && <button type="button" aria-label="Remove picture" onClick={clear} className="absolute -right-1.5 -top-1.5 grid h-6 w-6 place-items-center rounded-full bg-surface text-muted shadow ring-1 ring-line hover:text-bad"><Trash2 className="h-3 w-3" /></button>}
      <input ref={ref} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" data-testid={`img-${kind}-${id}`} onChange={(e) => pick(e.target.files?.[0])} />
    </div>
  );
}
