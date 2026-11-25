/** Tiny promise wrapper around IndexedDB (no dependency). Every call fails soft: if IndexedDB is unavailable the app still works online. */
const DB = "dinex-offline";
const VERSION = 1;
export type Store = "kv" | "outbox";

let opening: Promise<IDBDatabase> | null = null;
function open(): Promise<IDBDatabase> {
  if (typeof indexedDB === "undefined") return Promise.reject(new Error("no indexedDB"));
  opening ??= new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("kv")) db.createObjectStore("kv");
      if (!db.objectStoreNames.contains("outbox")) db.createObjectStore("outbox", { keyPath: "client_uuid" });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => { opening = null; reject(req.error); };
  });
  return opening;
}

async function tx<T>(store: Store, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T> | void): Promise<T | undefined> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const t = db.transaction(store, mode);
    const r = fn(t.objectStore(store));
    t.oncomplete = () => resolve(r ? (r as IDBRequest<T>).result : undefined);
    t.onerror = () => reject(t.error);
    t.onabort = () => reject(t.error);
  });
}

export const idb = {
  get: <T>(store: Store, key: string) => tx<T>(store, "readonly", (s) => s.get(key)).catch(() => undefined),
  all: <T>(store: Store) => tx<T[]>(store, "readonly", (s) => s.getAll()).then((r) => r ?? []).catch(() => [] as T[]),
  put: (store: Store, value: unknown, key?: string) => tx(store, "readwrite", (s) => s.put(value, key)).then(() => true).catch(() => false),
  del: (store: Store, key: string) => tx(store, "readwrite", (s) => { s.delete(key); }).then(() => true).catch(() => false),
  clear: (store: Store) => tx(store, "readwrite", (s) => { s.clear(); }).then(() => true).catch(() => false),
};
