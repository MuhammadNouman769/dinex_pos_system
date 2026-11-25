"use client";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { AppShell } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function AppLayout({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  const router = useRouter();
  useEffect(() => { if (!loading && !me) router.replace("/login"); }, [loading, me, router]);
  if (loading || !me) return <div className="grid min-h-screen place-items-center"><Spinner label="Loading…" /></div>;
  return <AppShell>{children}</AppShell>;
}
