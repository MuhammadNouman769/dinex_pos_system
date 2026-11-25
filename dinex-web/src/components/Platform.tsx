"use client";
import type { SubStatus } from "@/lib/types";
import { Badge } from "@/components/ui";

export const STATUS_LABEL: Record<SubStatus, string> = { TRIAL: "Free trial", ACTIVE: "Active", PAST_DUE: "Payment overdue", SUSPENDED: "Suspended", CANCELLED: "Cancelled" };
const TONE: Record<SubStatus, "brand" | "good" | "warn" | "bad" | "neutral"> = { TRIAL: "brand", ACTIVE: "good", PAST_DUE: "warn", SUSPENDED: "bad", CANCELLED: "neutral" };

export function StatusBadge({ status }: { status: SubStatus | undefined | null }) {
  if (!status) return <Badge>No plan</Badge>;
  return <Badge tone={TONE[status]}>{STATUS_LABEL[status]}</Badge>;
}

export const fmtDate = (s: string | null | undefined) => (s ? new Date(s).toLocaleDateString("en-PK", { day: "numeric", month: "short", year: "numeric" }) : "-");
export const fmtDateTime = (s: string | null | undefined) => (s ? new Date(s).toLocaleString("en-PK", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "-");
export const ago = (s: string | null | undefined) => {
  if (!s) return "never";
  const d = Math.floor((Date.now() - new Date(s).getTime()) / 86400000);
  return d <= 0 ? "today" : d === 1 ? "yesterday" : `${d} days ago`;
};
export function genPassword() {
  const pick = (set: string) => set[Math.floor(Math.random() * set.length)];
  const all = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const chars = [pick("ABCDEFGHJKLMNPQRSTUVWXYZ"), pick("abcdefghjkmnpqrstuvwxyz"), pick("23456789"), pick("@#$%!"), ...Array.from({ length: 8 }, () => pick(all))];
  return chars.sort(() => Math.random() - 0.5).join("");
}
