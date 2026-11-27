/** @type {import('next').NextConfig} */
const BUILD_ID = String(Date.now());
// Pages that belong to signed-in users: never show them in Google (the proxy adds the same header for /api and /django-admin).
const PRIVATE_PATHS = ["dashboard", "pos", "orders", "kitchen", "tables", "reservations", "customers", "cash", "inventory", "purchases", "expenses", "reports", "day-report", "payroll", "staff", "setup", "billing", "kiosk", "admin"];
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",          // tiny self-contained server for Docker
  poweredByHeader: false,
  env: { NEXT_PUBLIC_BUILD_ID: BUILD_ID },   // the service worker URL changes on every build, so browsers pick up the new one
  async headers() {
    const noindex = PRIVATE_PATHS.map((p) => ({ source: `/${p}/:path*`, headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] }));
    return [...noindex, { source: "/sw.js", headers: [
      { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
      { key: "Service-Worker-Allowed", value: "/" },
    ] }];
  },
};
export default nextConfig;
