import type { Metadata } from "next";
import type { ReactNode } from "react";

// Account pages: useful to people, useless in Google results.
export const metadata: Metadata = { robots: { index: false, follow: false }, alternates: { canonical: null } };
export default function Layout({ children }: { children: ReactNode }) { return children; }
