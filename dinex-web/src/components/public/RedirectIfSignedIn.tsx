"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

/** The home page is public (Google reads it), but people who are already signed in go straight to their work. */
export function RedirectIfSignedIn() {
  const { me, loading } = useAuth();
  const router = useRouter();
  useEffect(() => { if (!loading && me) router.replace(me.role === "PLATFORM" ? "/admin" : "/dashboard"); }, [me, loading, router]);
  return null;
}
