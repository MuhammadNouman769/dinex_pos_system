/** @type {import('next').NextConfig} */
const BUILD_ID = String(Date.now());
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",          // tiny self-contained server for Docker
  poweredByHeader: false,
  env: { NEXT_PUBLIC_BUILD_ID: BUILD_ID },   // the service worker URL changes on every build, so browsers pick up the new one
  async headers() {
    return [{ source: "/sw.js", headers: [
      { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
      { key: "Service-Worker-Allowed", value: "/" },
    ] }];
  },
};
export default nextConfig;
