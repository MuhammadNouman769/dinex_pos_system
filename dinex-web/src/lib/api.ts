import { idb } from "./offline/idb";
import { markReachable } from "./offline/status";
import type { Paginated } from "./types";

// Production: "/api/v1" (same domain, the proxy forwards it). Development: set NEXT_PUBLIC_API_URL in .env.local.
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";
const ACCESS = "dinex_access";
const REFRESH = "dinex_refresh";

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, message: string, data: unknown) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export const tokens = {
  get access() { return typeof window === "undefined" ? null : localStorage.getItem(ACCESS); },
  get refresh() { return typeof window === "undefined" ? null : localStorage.getItem(REFRESH); },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS, access);
    if (refresh) localStorage.setItem(REFRESH, refresh);
  },
  clear() { localStorage.removeItem(ACCESS); localStorage.removeItem(REFRESH); void idb.clear("kv"); },
};

/** Turn any DRF error body into one readable sentence. */
export function messageFrom(data: unknown, fallback = "Something went wrong."): string {
  if (!data) return fallback;
  if (typeof data === "string") return data.length < 300 ? data : fallback;
  if (Array.isArray(data)) return data.map((d) => messageFrom(d, "")).filter(Boolean).join(" ") || fallback;
  if (typeof data === "object") {
    const o = data as Record<string, unknown>;
    if (typeof o.error === "string") return o.error;
    if (typeof o.detail === "string") return o.detail;
    const parts = Object.entries(o).map(([k, v]) => {
      const m = messageFrom(v, "");
      if (!m) return "";
      return k === "non_field_errors" || k === "error" || k === "detail" || m.length > 30 ? m : `${k.replace(/_/g, " ")}: ${m}`;
    });
    return parts.filter(Boolean).join(" · ") || fallback;
  }
  return fallback;
}

/** "ok" = new token, "denied" = the server refused it (log out), "network" = could not reach the server (stay logged in). */
type Refresh = "ok" | "denied" | "network";
let refreshing: Promise<Refresh> | null = null;
/** Refresh tokens are single-use (the server rotates them). Two tabs of the same browser share one login, so only one tab may renew at a time. */
function exclusive<T>(fn: () => Promise<T>): Promise<T> {
  const locks = typeof navigator !== "undefined" ? (navigator as Navigator & { locks?: LockManager }).locks : undefined;
  return locks ? (locks.request("dinex-refresh", fn) as unknown as Promise<T>) : fn();
}
async function refreshAccess(): Promise<Refresh> {
  const wanted = tokens.refresh;
  if (!wanted) return "denied";
  refreshing ??= exclusive<Refresh>(async () => {
    const sent = tokens.refresh;
    if (!sent) return "denied";
    if (sent !== wanted) return "ok";                 // another tab already renewed while we waited
    try {
      const r = await fetch(`${BASE}/auth/token/refresh/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh: sent }) });
      if (r.status >= 500) return "network";
      if (!r.ok) return tokens.refresh && tokens.refresh !== sent ? "ok" : "denied";   // refused, but another tab may have just saved a new one
      const d = await r.json();
      tokens.set(d.access, d.refresh);
      return "ok";
    } catch { return "network"; }
  }).finally(() => { refreshing = null; });
  return refreshing;
}

type Query = Record<string, string | number | boolean | null | undefined>;

export interface Opts { timeoutMs?: number; noCache?: boolean }

/** GET responses are kept on the device so screens still open without internet (last known data). */
const cacheKey = (path: string, qs: string) => `GET ${path}${qs}`;
const NEVER_CACHE = ["/auth/token"];

async function request<T>(method: string, path: string, body?: unknown, query?: Query, retry = true, opts: Opts = {}): Promise<T> {
  const qs = query
    ? "?" + new URLSearchParams(Object.entries(query).filter(([, v]) => v !== undefined && v !== null && v !== "").map(([k, v]) => [k, String(v)])).toString()
    : "";
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  const headers: Record<string, string> = isForm ? {} : { "Content-Type": "application/json" };
  if (tokens.access) headers.Authorization = `Bearer ${tokens.access}`;

  const qstr = qs === "?" ? "" : qs;
  const key = cacheKey(path, qstr);
  const cacheable = method === "GET" && !opts.noCache && !NEVER_CACHE.some((p) => path.startsWith(p));
  const fromCache = async (): Promise<T | undefined> => (cacheable ? (await idb.get<{ data: T }>("kv", key))?.data : undefined);

  let res: Response;
  const ctl = opts.timeoutMs ? new AbortController() : null;
  const timer = ctl ? setTimeout(() => ctl.abort(), opts.timeoutMs) : null;
  try {
    res = await fetch(`${BASE}${path}${qstr}`, { method, headers, signal: ctl?.signal, body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body) });
  } catch {
    markReachable(false);
    const cached = await fromCache();
    if (cached !== undefined) return cached;
    throw new ApiError(0, "Cannot reach the server. Check your internet connection.", null);
  } finally { if (timer) clearTimeout(timer); }
  markReachable(true);

  if (res.status === 401 && retry && !path.startsWith("/auth/token")) {
    const r = await refreshAccess();
    if (r === "ok") return request<T>(method, path, body, query, false, opts);
    if (r === "network") {                       // cannot renew the token without internet: keep the user signed in
      const cached = await fromCache();
      if (cached !== undefined) return cached;
      throw new ApiError(0, "Cannot reach the server. Check your internet connection.", null);
    }
    tokens.clear();
    if (typeof window !== "undefined") window.dispatchEvent(new Event("dinex:logout"));
  }
  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let data: unknown = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const fallback = res.status >= 500 ? "Server error. Please try again." : res.status === 403 ? "You do not have permission to do this." : "Request failed.";
    throw new ApiError(res.status, messageFrom(data, fallback), data);
  }
  if (cacheable) void idb.put("kv", { data, at: Date.now() }, key);
  return data as T;
}

export const api = {
  get: <T>(path: string, query?: Query, opts?: Opts) => request<T>("GET", path, undefined, query, true, opts),
  post: <T>(path: string, body?: unknown, opts?: Opts) => request<T>("POST", path, body ?? {}, undefined, true, opts),
  /** Multipart upload (pictures). The browser sets the Content-Type boundary itself. */
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, form),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body ?? {}),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body ?? {}),
  del: <T = void>(path: string) => request<T>("DELETE", path),
  /** Fetch a paginated endpoint and return just the rows (up to 100). */
  async list<T>(path: string, query?: Query): Promise<T[]> {
    const page = await request<Paginated<T>>("GET", path, undefined, { page_size: 100, ...query });
    return page.results;
  },
};

export const money = (v: string | number | null | undefined, currency = "PKR") => {
  const n = Number(v ?? 0);
  return `${currency} ${n.toLocaleString("en-PK", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
};

/** Picture URL for <img>. In production the proxy serves /media on the same domain, so use a relative path (works behind any host). */
export function imgUrl(u: string | null | undefined): string | null {
  if (!u) return null;
  if (BASE.startsWith("/")) { try { return new URL(u, "http://x").pathname; } catch { return u; } }
  return u;
}
