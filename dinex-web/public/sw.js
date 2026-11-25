/* DineX service worker: makes the app open without internet.
 * - Pages and their JS/CSS are saved when the app is first opened with internet, so they load offline.
 * - Pictures (dishes, deals) are kept after they were seen once.
 * - API calls are NOT touched here: the app itself saves orders on the device and syncs them (see lib/offline).
 */
const V = new URL(self.location.href).searchParams.get("v") || "0";
const SHELL = `dinex-shell-${V}`;
const ASSETS = "dinex-assets";
const IMAGES = "dinex-images";
const ROUTES = ["/", "/login", "/plans", "/signup", "/terms", "/dashboard", "/pos", "/orders", "/cash", "/billing", "/inventory", "/staff", "/payroll", "/reports", "/setup", "/kiosk"];
const EXTRA = ["/manifest.webmanifest", "/icons/icon-192.png", "/icons/icon-512.png"];
const MAX_IMAGES = 400;

self.addEventListener("install", (event) => { event.waitUntil(precache().then(() => self.skipWaiting())); });

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith("dinex-shell-") && k !== SHELL) await caches.delete(k);
    await self.clients.claim();
  })());
});

async function precache() {
  const shell = await caches.open(SHELL);
  const assets = await caches.open(ASSETS);
  const found = new Set(EXTRA);
  await Promise.allSettled(ROUTES.map(async (r) => {
    const res = await fetch(r, { cache: "reload" });
    if (!res.ok) return;
    const html = await res.clone().text();
    await shell.put(r, res);
    for (const m of html.matchAll(/\/_next\/static\/[^"'\\\s)<>]+/g)) found.add(m[0]);
  }));
  await Promise.allSettled([...found].map(async (u) => { if (!(await assets.match(u))) { const r = await fetch(u); if (r.ok) await assets.put(u, r); } }));
}

const withTimeout = (p, ms) => new Promise((resolve, reject) => { const t = setTimeout(() => reject(new Error("timeout")), ms); p.then((v) => { clearTimeout(t); resolve(v); }, (e) => { clearTimeout(t); reject(e); }); });

async function navigation(req) {
  const url = new URL(req.url);
  const cache = await caches.open(SHELL);
  try {
    const res = await withTimeout(fetch(req), 4000);
    if (res.ok && res.headers.get("content-type")?.includes("text/html")) cache.put(url.pathname, res.clone());
    return res;
  } catch {
    return (await cache.match(url.pathname)) || (await cache.match(url.pathname.replace(/\/$/, ""))) ||
      new Response("<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><body style='font-family:system-ui;padding:2rem;text-align:center'><h2>You are offline</h2><p>This page was not saved on this device yet.</p><p><a href='/pos'>Open POS</a></p></body>", { status: 503, headers: { "content-type": "text/html; charset=utf-8" } });
  }
}

async function cacheFirst(req, name) {
  const cache = await caches.open(name);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) cache.put(req, res.clone());
  return res;
}

async function staleImage(req) {
  const cache = await caches.open(IMAGES);
  const hit = await cache.match(req);
  const net = fetch(req).then(async (res) => {
    if (res.ok || res.type === "opaque") {
      await cache.put(req, res.clone());
      const keys = await cache.keys();
      if (keys.length > MAX_IMAGES) await cache.delete(keys[0]);
    }
    return res;
  }).catch(() => undefined);
  return hit || (await net) || Response.error();
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const same = url.origin === self.location.origin;
  if (same && url.pathname.startsWith("/api/")) return;
  if (req.destination === "image" && (url.pathname.includes("/media/") || same)) { event.respondWith(staleImage(req)); return; }
  if (!same) return;
  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) { event.respondWith(cacheFirst(req, ASSETS)); return; }
  if (req.mode === "navigate") { event.respondWith(navigation(req)); return; }
});

self.addEventListener("message", (event) => { if (event.data === "precache") event.waitUntil(precache()); });
