"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, CloudOff, HandCoins, Minus, Plus, Printer, ChefHat, Gift, StickyNote, Search, ShoppingBag, Tag, Trash2, UtensilsCrossed } from "lucide-react";
import Link from "next/link";
import { MenuCard } from "@/components/MenuCard";
import { LocalPayModal } from "@/components/LocalPayModal";
import { TablePicker } from "@/components/TablePicker";
import { TableVisual } from "@/components/TableVisual";
import { OptionsModal, type Picked } from "@/components/OptionsModal";
import { PayModal } from "@/components/PayModal";
import { PlatformNotice } from "@/components/AppShell";
import { useOutboxFor } from "@/components/SyncPill";
import { Badge, Button, Card, EmptyState, Input, Modal, Select, Spinner, Textarea, cn, useAction, useToast } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { ApiError, api, money } from "@/lib/api";
import { localOrder } from "@/lib/offline/bill";
import { nextOfflineNumber, newOrderId, onSynced, outbox, sendOrder, type OutboxEntry, type SyncPayload } from "@/lib/offline/outbox";
import { isOnline, useOnline } from "@/lib/offline/status";
import { dealMath, dealRunning, orderTotals } from "@/lib/pricing";
import { printReceipt } from "@/lib/receipt";
import { printKot } from "@/lib/kot";
import type { Category, Deal, Employee, Order, OrderType, Paginated, Product, TableT, Variant } from "@/lib/types";

interface CartLine { key: string; kind: "item" | "deal"; id: number; name: string; variant: string; price: number; list: number; qty: number; mods?: Picked["mods"]; note?: string }
const TYPES: { id: OrderType; label: string }[] = [{ id: "DINE_IN", label: "Dine-in" }, { id: "TAKEAWAY", label: "Takeaway" }, { id: "DELIVERY", label: "Delivery" }];
type Done = { kind: "server"; order: Order; warnings: string[] } | { kind: "local"; entry: OutboxEntry };

export default function PosPage() {
  const { me, location, currency } = useAuth();
  const toast = useToast();
  const { run, busy } = useAction();
  const online = useOnline();
  const box = useOutboxFor();

  const [products, setProducts] = useState<Product[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tables, setTables] = useState<TableT[]>([]);
  const [loading, setLoading] = useState(true);
  const [catFilter, setCatFilter] = useState<number | "deals" | null>(null);
  const [search, setSearch] = useState("");

  const [cart, setCart] = useState<CartLine[]>([]);
  const [type, setType] = useState<OrderType>("TAKEAWAY");
  const [tableId, setTableId] = useState("");
  const [waiters, setWaiters] = useState<Employee[]>([]);
  const [waiterId, setWaiterId] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [known, setKnown] = useState<{ name: string; email: string; balance: number } | null>(null);
  const [address, setAddress] = useState("");
  const [notes, setNotes] = useState("");
  const [cartOpen, setCartOpen] = useState(false);
  const [done, setDone] = useState<Done | null>(null);
  const [payFor, setPayFor] = useState<Order | null>(null);
  const [localPay, setLocalPay] = useState<OutboxEntry | null>(null);
  const [pickTable, setPickTable] = useState(false);
  const [optFor, setOptFor] = useState<{ product: Product; variant: Variant } | null>(null);
  const [noteOpen, setNoteOpen] = useState<string | null>(null);
  const [autoKot, setAutoKot] = useState(false);
  useEffect(() => { try { setAutoKot(localStorage.getItem("dinex_auto_kot") === "1"); } catch {} }, []);
  const loyalty = me?.organization?.loyalty ?? { enabled: false };
  const loyaltyOn = !!loyalty.enabled;
  useEffect(() => {
    setKnown(null);
    if (!loyaltyOn || !location || phone.trim().length < 6 || typeof navigator !== "undefined" && !navigator.onLine) return;
    const t = setTimeout(() => {
      api.get<{ found: boolean; name?: string; email?: string; balance?: number }>("/loyalty/lookup/", { location: location.id, phone: phone.trim() })
        .then((r) => { if (r.found) { setKnown({ name: r.name ?? "", email: r.email ?? "", balance: r.balance ?? 0 }); setName((n) => n || r.name || ""); } })
        .catch(() => {});
    }, 400);
    return () => clearTimeout(t);
  }, [phone, loyaltyOn, location]);
  const [hasShift, setHasShift] = useState<boolean | null>(null);

  const loadTables = useCallback(async () => {
    if (!location) return;
    setTables(await api.list<TableT>("/orders/tables/", { location: location.id }).catch(() => []));
  }, [location]);

  useEffect(() => {
    if (!location) return;
    api.get<{ shift: unknown }>("/cash/shifts/current/", { location: location.id }).then((r) => setHasShift(!!r.shift)).catch(() => setHasShift(null));
  }, [location, payFor, online]);

  useEffect(() => {
    if (!location) return;
    (async () => {
      const [p, c, d] = await Promise.all([
        api.list<Product>("/catalog/products/", { is_active: "true" }), api.list<Category>("/catalog/categories/"),
        api.list<Deal>("/catalog/deals/", { active_deals: "true" }).catch(() => [] as Deal[]),
      ]);
      setProducts(p.filter((x) => x.is_active)); setCategories(c.filter((x) => x.is_active)); setDeals(d);
      await loadTables();
      setWaiters((await api.get<Paginated<Employee>>("/staff/employees/", { location: location.id, role: "WAITER", page_size: 100 }).catch(() => null))?.results ?? []);
      setLoading(false);
    })().catch((e) => { toast.err(e.message); setLoading(false); });
  }, [location, loadTables, toast]);
  useEffect(() => onSynced(() => { loadTables(); }), [loadTables]);
  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("table");
    if (t) { setType("DINE_IN"); setTableId(t); }
  }, []);

  const runningDeals = useMemo(() => deals.filter((d) => dealRunning(d, location?.id)).map((d) => ({ deal: d, math: dealMath(d, products) })).filter((x) => x.math), [deals, products, location]);

  const tiles = useMemo(() => {
    const q = search.trim().toLowerCase();
    return products
      .filter((p) => (typeof catFilter === "number" ? p.category === catFilter : true))
      .flatMap((p) => p.variants.filter((v) => v.is_active).map((v) => ({ product: p, variant: v, label: p.variants.length > 1 ? `${p.name} · ${v.name}` : p.name })))
      .filter((t) => !q || t.label.toLowerCase().includes(q));
  }, [products, catFilter, search]);
  const dealTiles = useMemo(() => {
    const q = search.trim().toLowerCase();
    return catFilter === null || catFilter === "deals" ? runningDeals.filter((x) => !q || x.deal.name.toLowerCase().includes(q)) : [];
  }, [runningDeals, catFilter, search]);

  const sigOf = (l: Pick<CartLine, "kind" | "id" | "mods" | "note">) => `${l.kind}:${l.id}:${(l.mods ?? []).map((m) => m.id).sort().join(",")}:${l.note ?? ""}`;
  const bump = (line: CartLine) => setCart((c) => {
    const i = c.findIndex((l) => sigOf(l) === sigOf(line));
    return i >= 0 ? c.map((l, j) => (j === i ? { ...l, qty: l.qty + line.qty } : l)) : [...c, line];
  });
  const addItem = (t: (typeof tiles)[number], p?: Picked) => {
    const extra = (p?.mods ?? []).reduce((a, m) => a + m.price, 0);
    const base = Number(t.variant.base_price) + extra;
    bump({ key: `v:${t.variant.id}:${Date.now()}${Math.random()}`, kind: "item", id: t.variant.id, name: t.product.name, variant: t.variant.name, price: base, list: base, qty: p?.qty ?? 1, mods: p?.mods, note: p?.note || undefined });
  };
  const tapItem = (t: (typeof tiles)[number]) => (t.product.modifier_groups?.length ? setOptFor({ product: t.product, variant: t.variant }) : addItem(t));
  const qtyOfVariant = (id: number) => cart.filter((l) => l.kind === "item" && l.id === id).reduce((a, l) => a + l.qty, 0);
  const lessVariant = (id: number) => { const last = [...cart].reverse().find((l) => l.kind === "item" && l.id === id); if (last) setQty(last.key, -1); };
  const setNote = (key: string, note: string) => setCart((c) => c.map((l) => (l.key === key ? { ...l, note: note || undefined } : l)));
  const addDeal = (x: (typeof runningDeals)[number]) => bump({ key: `d:${x.deal.id}`, kind: "deal", id: x.deal.id, name: x.deal.name, variant: "Deal", price: x.math!.price, list: x.math!.base, qty: 1 });
  const setQty = (key: string, d: number) => setCart((c) => c.map((l) => (l.key === key ? { ...l, qty: l.qty + d } : l)).filter((l) => l.qty > 0));
  const remove = (key: string) => setCart((c) => c.filter((l) => l.key !== key));

  const listTotal = cart.reduce((s, l) => s + l.list * l.qty, 0);
  const dealDiscount = cart.reduce((s, l) => s + (l.list - l.price) * l.qty, 0);
  const t = orderTotals(listTotal, dealDiscount, Number(location?.tax_rate ?? 0), Number(location?.service_charge_rate ?? 0));
  const count = cart.reduce((s, l) => s + l.qty, 0);
  const localTaken = useMemo(() => new Set(box.rows.filter((r) => r.payload.order_type === "DINE_IN" && r.payload.table).map((r) => r.payload.table as number)), [box.rows]);

  const problem =
    cart.length === 0 ? "Add at least one item." :
    type === "DINE_IN" && !tableId ? "Choose a table." :
    type === "DINE_IN" && waiters.length > 0 && !waiterId ? "Choose the waiter." :
    type === "DELIVERY" && (!phone.trim() || address.trim().length < 10) ? "Delivery needs a phone number and a full address." : "";

  function reset() { setCart([]); setTableId(""); setWaiterId(""); setName(""); setPhone(""); setEmail(""); setKnown(null); setAddress(""); setNotes(""); setCartOpen(false); }

  async function place() {
    if (!location || !me?.organization || problem) return;
    const payload: SyncPayload = {
      client_uuid: newOrderId(), location: location.id, order_type: type, table: type === "DINE_IN" ? Number(tableId) : null,
      waiter: type === "DINE_IN" && waiterId ? Number(waiterId) : null, customer_name: name.trim(), customer_phone: phone.trim(), ...(loyaltyOn && email.trim() ? { customer_email: email.trim() } : {}),
      delivery_address: type === "DELIVERY" ? address.trim() : "", notes: notes.trim(), placed_at: new Date().toISOString(), offline: false,
      items: cart.filter((l) => l.kind === "item").map((l) => ({ product_variant: l.id, quantity: l.qty, ...(l.note ? { notes: l.note } : {}), ...(l.mods?.length ? { modifiers: l.mods.map((m) => m.id) } : {}) })),
      deals: cart.filter((l) => l.kind === "deal").map((l) => ({ deal: l.id, quantity: l.qty })), payments: [],
    };
    const snapshot = { lines: cart, t, typeLabel: TYPES.find((x) => x.id === type)!.label, customer: name.trim(), table: tables.find((x) => String(x.id) === tableId) };
    const result = await run(async (): Promise<Done> => {
      if (isOnline()) {
        try {
          const r = await sendOrder(payload, 12000);
          return { kind: "server", order: r.order, warnings: [...r.stock_warnings, ...r.payment_warnings] };
        } catch (e) { if (!(e instanceof ApiError && e.status === 0)) throw e; }   // no internet: save it on this device instead
      }
      payload.offline = true;
      const entry: OutboxEntry = {
        client_uuid: payload.client_uuid, org: me.organization!.id, location: location.id, payload, status: "queued", attempts: 0, created_at: new Date().toISOString(),
        table_label: snapshot.table ? `${snapshot.table.floor_name ? snapshot.table.floor_name + " · " : ""}${snapshot.table.table_number}` : undefined,
        display: {
          number: await nextOfflineNumber(), type_label: snapshot.typeLabel, total: snapshot.t.total, subtotal: snapshot.t.subtotal, tax: snapshot.t.tax, service: snapshot.t.service, discount: snapshot.t.discount, customer: snapshot.customer,
          lines: snapshot.lines.map((l) => ({ name: l.kind === "deal" ? `Deal: ${l.name}` : l.variant && l.variant !== "Regular" ? `${l.name} (${l.variant})` : l.name, qty: l.qty, price: l.list, mods: l.mods?.map((m) => m.name), notes: l.note })),
        },
      };
      await outbox.add(entry);
      return { kind: "local", entry };
    });
    if (result) {
      setDone(result); reset(); loadTables();
      if (autoKot) setTimeout(() => kot(result), 50);
    }
  }

  function kot(d: Done) {
    const o = d.kind === "server" ? d.order : localOrder(d.entry);
    const label = d.kind === "server" ? tables.find((x) => x.id === d.order.table)?.table_number : d.entry.table_label;
    if (!printKot(o, { location: location!.name, tableLabel: label, temporary: d.kind === "local" })) toast.err("Allow pop-ups to print the kitchen ticket.");
  }
  const toggleAuto = () => setAutoKot((v) => { const n = !v; try { localStorage.setItem("dinex_auto_kot", n ? "1" : "0"); } catch {} return n; });

  if (me && !me.organization) return <PlatformNotice />;
  if (!me?.can_operate_pos) return <EmptyState title="No POS access" hint="Ask the owner to assign you to a location as a cashier or manager." />;
  if (loading) return <Spinner label="Loading menu…" />;

  const cartPanel = (
    <div className="flex h-full flex-col">
      <div className="grid grid-cols-3 gap-1.5 rounded-xl bg-sunken p-1">
        {TYPES.map((x) => (
          <button key={x.id} onClick={() => setType(x.id)} className={cn("min-h-[44px] rounded-lg text-sm font-semibold transition", type === x.id ? "bg-surface text-brand shadow-sm" : "text-muted hover:text-ink")}>{x.label}</button>
        ))}
      </div>

      <div className="mt-3 space-y-3">
        {type === "DINE_IN" && (
          <button type="button" onClick={() => setPickTable(true)} data-testid="choose-table" className="flex min-h-[56px] w-full items-center gap-3 rounded-xl border border-line bg-surface px-3 text-left transition hover:border-brand">
            {(() => { const t = tables.find((x) => String(x.id) === tableId); return t ? (
              <><span className="grid h-10 w-12 shrink-0 place-items-center overflow-hidden"><TableVisual shape={t.shape ?? "SQUARE"} seats={t.capacity} scale={0.32} sub=" " /></span><span className="flex-1 text-sm"><b>{t.floor_name ? `${t.floor_name} · ` : ""}{t.table_number}</b><br /><span className="text-xs text-muted">{t.capacity} seats</span></span><span className="text-xs font-semibold text-brand">Change</span></>
            ) : <span className="flex-1 text-sm font-semibold text-muted">{tables.length ? "Choose a table…" : "No tables yet. Add them in Setup"}</span>; })()}
          </button>
        )}
        {type === "DINE_IN" && waiters.length > 0 && (
          <Select aria-label="Waiter" value={waiterId} onChange={(e) => setWaiterId(e.target.value)}>
            <option value="">Waiter…</option>{waiters.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
          </Select>
        )}
        <div className="grid grid-cols-2 gap-2">
          <Input placeholder="Customer name" value={name} onChange={(e) => setName(e.target.value)} data-testid="cust-name" />
          <Input placeholder={loyaltyOn ? "Phone (for points)" : "Phone"} inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} data-testid="cust-phone" />
        </div>
        {loyaltyOn && phone.trim().length >= 6 && (
          <div className="space-y-2">
            {known ? (
              <p className="flex items-center gap-2 rounded-xl bg-brand-soft px-3 py-2 text-sm font-medium text-brand" data-testid="cust-known"><Gift className="h-4 w-4" />{known.name} · {known.balance} points{known.balance >= (loyalty.min_redeem ?? 100) ? " · can use them at payment" : ""}</p>
            ) : (
              <p className="flex items-center gap-2 rounded-xl bg-sunken px-3 py-2 text-xs text-muted" data-testid="cust-new"><Gift className="h-4 w-4" />New customer. Points are added when the bill is paid.</p>
            )}
            {!known?.email && <Input type="email" placeholder="Email (optional, we send their points)" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="cust-email" />}
          </div>
        )}
        {type === "DELIVERY" && <Textarea rows={2} placeholder="Delivery address" value={address} onChange={(e) => setAddress(e.target.value)} />}
      </div>

      <div className="scroll-thin -mx-1 mt-3 min-h-[120px] flex-1 space-y-2 overflow-y-auto px-1">
        {cart.length === 0 ? (
          <div className="grid h-full place-items-center py-10 text-center text-sm text-muted"><div><ShoppingBag className="mx-auto mb-2 h-8 w-8 opacity-50" />Tap a dish to start the order</div></div>
        ) : cart.map((l) => (
          <div key={l.key} className="flex items-center gap-3 rounded-xl border border-line p-2.5">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">{l.kind === "deal" && <Tag className="mr-1 inline h-3.5 w-3.5 text-accent" />}{l.name}{l.kind === "item" && l.variant !== "Regular" ? ` · ${l.variant}` : ""}</p>
              {l.mods && l.mods.length > 0 && <p className="truncate text-xs text-muted">{l.mods.map((m) => m.name).join(", ")}</p>}
              <p className="num text-xs text-muted">{money(l.price, currency)}{l.kind === "deal" && <span className="ml-1 line-through opacity-60">{money(l.list, currency)}</span>}</p>
              {l.kind === "item" && (noteOpen === l.key ? (
                <input autoFocus maxLength={200} defaultValue={l.note ?? ""} placeholder="Note for kitchen" data-testid="line-note-input" onBlur={(e) => { setNote(l.key, e.target.value.trim()); setNoteOpen(null); }} onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }} className="mt-1 h-8 w-full rounded-lg border border-line bg-surface px-2 text-xs" />
              ) : (
                <button type="button" onClick={() => setNoteOpen(l.key)} data-testid="line-note" className="mt-0.5 inline-flex items-center gap-1 text-xs font-medium text-brand"><StickyNote className="h-3 w-3" />{l.note ? l.note : "Add note"}</button>
              ))}
            </div>
            <div className="flex items-center gap-1">
              <button aria-label="Less" onClick={() => setQty(l.key, -1)} className="grid h-9 w-9 place-items-center rounded-lg bg-sunken hover:bg-line"><Minus className="h-4 w-4" /></button>
              <span className="num w-7 text-center text-sm font-bold">{l.qty}</span>
              <button aria-label="More" onClick={() => setQty(l.key, 1)} className="grid h-9 w-9 place-items-center rounded-lg bg-sunken hover:bg-line"><Plus className="h-4 w-4" /></button>
            </div>
            <button aria-label="Remove" onClick={() => remove(l.key)} className="grid h-9 w-9 place-items-center text-muted hover:text-bad"><Trash2 className="h-4 w-4" /></button>
          </div>
        ))}
      </div>

      <div className="mt-3 space-y-1.5 border-t border-line pt-3 text-sm">
        <Row label="Subtotal" value={money(t.subtotal, currency)} />
        {t.service > 0 && <Row label={`Service charge (${Number(location?.service_charge_rate)}%)`} value={money(t.service, currency)} />}
        {t.tax > 0 && <Row label={`Tax (${Number(location?.tax_rate)}%)`} value={money(t.tax, currency)} />}
        {t.discount > 0 && <Row label="Deal discount" value={`− ${money(t.discount, currency)}`} />}
        <div className="flex items-center justify-between pt-1 text-lg font-bold"><span>Total</span><span className="num">{money(t.total, currency)}</span></div>
        <Input placeholder="Order note (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <label className="flex cursor-pointer items-center justify-between text-xs text-muted"><span className="flex items-center gap-1.5"><ChefHat className="h-3.5 w-3.5" />Auto-print kitchen ticket</span><input type="checkbox" checked={autoKot} onChange={toggleAuto} data-testid="auto-kot" className="h-4 w-4 accent-[rgb(var(--brand))]" /></label>
        {problem && cart.length > 0 && <p className="text-xs text-warn">{problem}</p>}
        <Button size="lg" className="w-full" disabled={!!problem} loading={busy} onClick={place}>{online ? "Send to kitchen" : "Save order"} · {money(t.total, currency)}</Button>
        {!online && <p className="flex items-center gap-1.5 text-xs text-warn"><CloudOff className="h-3.5 w-3.5" />Offline: the order is saved on this device and sent when the internet returns.</p>}
      </div>
    </div>
  );

  return (
    <>
      {hasShift === false && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-warn-soft px-4 py-3 text-sm text-warn">
          <span><b>No open shift.</b> You can take orders, but payments need an open shift.</span>
          <Link href="/cash" className="font-semibold underline">Open shift</Link>
        </div>
      )}
      <div className="grid gap-6 md:grid-cols-[1fr_340px] lg:grid-cols-[1fr_390px]">
        <section className="min-w-0">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="relative min-w-[200px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <Input aria-label="Search menu" placeholder="Search dishes…" className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
          </div>
          <div className="scroll-thin -mx-1 mb-4 flex gap-2 overflow-x-auto px-1 pb-1">
            <Chip active={catFilter === null} onClick={() => setCatFilter(null)}>All</Chip>
            {runningDeals.length > 0 && <Chip active={catFilter === "deals"} onClick={() => setCatFilter("deals")}><Tag className="mr-1 inline h-3.5 w-3.5" />Deals</Chip>}
            {categories.map((c) => <Chip key={c.id} active={catFilter === c.id} onClick={() => setCatFilter(c.id)}>{c.name}</Chip>)}
          </div>

          {dealTiles.length > 0 && (
            <div className="mb-6">
              <h2 className="mb-2 flex items-center gap-2 font-display text-base font-extrabold"><Tag className="h-4 w-4 text-accent" />Deals</h2>
              <div className="grid grid-cols-2 gap-3 sm:gap-4 sm:[grid-template-columns:repeat(auto-fill,minmax(168px,1fr))]">
                {dealTiles.map(({ deal, math }) => (
                  <MenuCard key={deal.id} deal testId={`deal-${deal.id}`} name={deal.name} image={deal.image} price={money(math!.price, currency)} strike={money(math!.base, currency)}
                    badge={`Save ${money(math!.discount, currency)}`}
                    qty={cart.find((l) => l.key === `d:${deal.id}`)?.qty ?? 0} onAdd={() => addDeal({ deal, math })} onLess={() => setQty(`d:${deal.id}`, -1)} />
                ))}
              </div>
            </div>
          )}

          {catFilter === "deals" ? null : tiles.length === 0 ? (
            <EmptyState icon={<UtensilsCrossed className="h-8 w-8" />} title={products.length === 0 ? "Your menu is empty" : "Nothing matches"}
              hint={products.length === 0 ? "Add categories and dishes in Setup → Menu, then they appear here." : "Try another category or search."} />
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:gap-4 sm:[grid-template-columns:repeat(auto-fill,minmax(168px,1fr))]">
              {tiles.map((x) => (
                <MenuCard key={x.variant.id} testId={`tile-${x.variant.id}`} name={x.label} image={x.product.image} price={money(x.variant.base_price, currency)}
                  qty={qtyOfVariant(x.variant.id)} onAdd={() => tapItem(x)} onLess={() => lessVariant(x.variant.id)} />
              ))}
            </div>
          )}
        </section>

        <aside className="hidden md:block"><Card className="sticky top-20 h-[calc(100vh-13rem)] p-4 lg:h-[calc(100vh-7rem)]">{cartPanel}</Card></aside>
      </div>

      {/* Mobile cart bar */}
      <div className="fixed inset-x-0 bottom-[calc(4.6rem+env(safe-area-inset-bottom))] z-20 px-4 md:hidden">
        {count > 0 && <Button size="lg" className="w-full shadow-pop" onClick={() => setCartOpen(true)}><ShoppingBag className="h-5 w-5" />View order · {count} item{count > 1 ? "s" : ""} · {money(t.total, currency)}</Button>}
      </div>
      <Modal open={cartOpen} onClose={() => setCartOpen(false)} title="Current order" width="max-w-md"><div className="h-[70vh]">{cartPanel}</div></Modal>

      <Modal open={!!done} onClose={() => setDone(null)} title={done?.kind === "local" ? "Saved on this device" : "Order sent to kitchen"} width="max-w-sm">
        {done?.kind === "server" && (
          <div className="text-center">
            <CheckCircle2 className="mx-auto h-14 w-14 text-good" />
            <p className="mt-3 text-2xl font-bold" data-testid="done-number">{done.order.order_number}</p>
            <p className="text-sm text-muted">{done.order.order_type_display} · {done.order.items.length} item{done.order.items.length === 1 ? "" : "s"}</p>
            <p className="num mt-3 text-3xl font-bold text-brand">{money(done.order.total_amount, currency)}</p>
            {done.warnings.length > 0 && (
              <div className="mt-4 rounded-xl bg-warn-soft p-3 text-left text-xs text-warn">
                <p className="mb-1 font-bold">Please check</p>
                {done.warnings.map((w) => <p key={w}>• {w}</p>)}
              </div>
            )}
            <Button className="mt-5 w-full" size="lg" onClick={() => { setPayFor(done.order); setDone(null); }}><HandCoins className="h-5 w-5" />Take payment · {money(done.order.total_amount, currency)}</Button>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <Button variant="secondary" onClick={() => { if (!printReceipt(done.order, { tableLabel: tables.find((x) => x.id === done.order.table)?.table_number, business: me.organization!.name, branding: me.organization!.branding, loyalty: me.organization!.loyalty, location: location!.name, address: location!.address, currency })) toast.err("Allow pop-ups to print the bill."); }}><Printer className="h-4 w-4" />Print bill</Button>
              <Button variant="ghost" onClick={() => setDone(null)}>Pay later</Button>
            </div>
            <Button variant="secondary" className="mt-2 w-full" data-testid="print-kot" onClick={() => kot(done)}><ChefHat className="h-4 w-4" />Print kitchen ticket</Button>
            <div className="mt-3"><Badge tone="good">Stock updated</Badge></div>
          </div>
        )}
        {done?.kind === "local" && (
          <div className="text-center">
            <CloudOff className="mx-auto h-14 w-14 text-warn" />
            <p className="mt-3 text-2xl font-bold" data-testid="done-number">{done.entry.display.number}</p>
            <p className="text-sm text-muted">{done.entry.display.type_label} · temporary number</p>
            <p className="num mt-3 text-3xl font-bold text-brand">{money(done.entry.display.total, currency)}</p>
            <p className="mt-3 rounded-xl bg-warn-soft p-3 text-left text-xs text-warn">Saved safely on this device. It goes to the server and the kitchen board automatically when the internet is back{done.entry.payload.payments.length ? "." : ", and you can take payment now."}</p>
            {done.entry.payload.payments.length > 0 ? <div className="mt-4"><Badge tone="good">Payment recorded</Badge></div> : hasShift ? (
              <Button className="mt-5 w-full" size="lg" onClick={() => { setLocalPay(done.entry); setDone(null); }}><HandCoins className="h-5 w-5" />Take payment · {money(done.entry.display.total, currency)}</Button>
            ) : <p className="mt-4 text-xs text-muted">To take payment, open a shift in Cash desk while online first. You can collect payment after it syncs.</p>}
            <div className="mt-2 grid grid-cols-2 gap-2">
              <Button variant="secondary" onClick={() => { if (!printReceipt(localOrder(done.entry), { tableLabel: done.entry.table_label, business: me.organization!.name, branding: me.organization!.branding, loyalty: me.organization!.loyalty, location: location!.name, address: location!.address, currency })) toast.err("Allow pop-ups to print the bill."); }}><Printer className="h-4 w-4" />Print bill</Button>
              <Button variant="ghost" onClick={() => setDone(null)}>Done</Button>
            </div>
            <Button variant="secondary" className="mt-2 w-full" data-testid="print-kot" onClick={() => kot(done)}><ChefHat className="h-4 w-4" />Print kitchen ticket</Button>
          </div>
        )}
      </Modal>
      <OptionsModal open={!!optFor} product={optFor?.product ?? null} variant={optFor?.variant ?? null} onClose={() => setOptFor(null)}
        onAdd={(p) => { if (optFor) addItem({ product: optFor.product, variant: optFor.variant, label: optFor.product.name }, p); setOptFor(null); }} />
      <TablePicker open={pickTable} onClose={() => setPickTable(false)} tables={tables} value={tableId} taken={localTaken} onPick={(t) => { setTableId(String(t.id)); setPickTable(false); }} />
      <PayModal order={payFor} open={!!payFor} onClose={() => setPayFor(null)} />
      <LocalPayModal entry={localPay} open={!!localPay} onClose={() => setLocalPay(null)} onSaved={(e) => setLocalPay(e)} />
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between text-muted"><span>{label}</span><span className="num font-medium text-ink">{value}</span></div>;
}
function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button onClick={onClick} className={cn("min-h-[44px] shrink-0 rounded-full border px-4 text-sm font-semibold transition", active ? "border-brand bg-brand text-white dark:text-[#04201a]" : "border-line bg-surface text-muted hover:text-ink")}>{children}</button>;
}
