import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { AuthProvider } from "@/lib/auth";
import { ServiceWorker } from "@/components/ServiceWorker";
import { ToastProvider } from "@/components/ui";
import { COMPANY, GOOGLE_VERIFICATION, SITE_DESCRIPTION, SITE_NAME, SITE_TAGLINE, SITE_URL } from "@/lib/site";
import "@fontsource-variable/inter";
import "@fontsource-variable/plus-jakarta-sans";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: `${SITE_NAME} · ${SITE_TAGLINE}`, template: `%s · ${SITE_NAME}` },
  description: SITE_DESCRIPTION,
  applicationName: SITE_NAME,
  authors: [{ name: COMPANY }],
  creator: COMPANY,
  publisher: COMPANY,
  keywords: ["restaurant POS", "POS software Pakistan", "restaurant billing software", "kitchen order system", "offline POS", "restaurant inventory", "restaurant payroll", "loyalty points", "DineX", "XverLabs"],
  alternates: { canonical: "/" },
  openGraph: { type: "website", siteName: SITE_NAME, title: `${SITE_NAME} · ${SITE_TAGLINE}`, description: SITE_DESCRIPTION, url: "/", locale: "en_PK" },
  twitter: { card: "summary_large_image", title: `${SITE_NAME} · ${SITE_TAGLINE}`, description: SITE_DESCRIPTION },
  robots: { index: true, follow: true, googleBot: { index: true, follow: true, "max-image-preview": "large", "max-snippet": -1 } },
  ...(GOOGLE_VERIFICATION ? { verification: { google: GOOGLE_VERIFICATION } } : {}),
  appleWebApp: { capable: true, title: "DineX", statusBarStyle: "default" },
  formatDetection: { telephone: false },
};
export const viewport: Viewport = { themeColor: "#0D7A62", width: "device-width", initialScale: 1, viewportFit: "cover" };

const themeScript = `try{var t=localStorage.getItem('dinex_theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.classList.add('dark')}catch(e){}`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body>
        <ServiceWorker />
        <AuthProvider><ToastProvider>{children}</ToastProvider></AuthProvider>
      </body>
    </html>
  );
}
