"use client";
import { useCallback, useEffect, useState } from "react";
import { Gift, Search, Users } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { Badge, Button, Card, EmptyState, Input, PageHeader, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, money } from "@/lib/api";
import { downloadCsv } from "@/lib/csv";

interface Cust { id: number; full_name: string; phone: string; email: string | null; points_balance: number; total_orders: number; total_spent: string; last_order_at: string | null }

export default function CustomersPage() {
  const { me, location, currency } = useAuth();
  const [rows, setRows] = useState<Cust[] | null>(null);
  const [q, setQ] = useState("");
  const load = useCallback(async () => {
    if (!location) return;
    setRows(await api.list<Cust>("/customers/", { location: location.id, search: q || undefined, page_size: 200 }));
  }, [location, q]);
  useEffect(() => { const t = setTimeout(() => load().catch(() => setRows([])), 250); return () => clearTimeout(t); }, [load]);
  if (me && !me.organization) return <PlatformNotice />;
  const loyaltyOn = !!me?.organization?.loyalty?.enabled;
  const points = (rows ?? []).reduce((a, c) => a + c.points_balance, 0);

  return (
    <>
      <PageHeader title="Customers" subtitle={`${location?.name} · ${rows?.length ?? 0} customers${loyaltyOn ? ` · ${points.toLocaleString()} points held` : ""}`}
        actions={<Button variant="secondary" disabled={!rows?.length} data-testid="csv-cust" onClick={() => downloadCsv("customers.csv", [["Name", "Phone", "Email", "Points", "Orders", "Spent", "Last order"], ...rows!.map((c) => [c.full_name, c.phone, c.email ?? "", c.points_balance, c.total_orders, c.total_spent, c.last_order_at ?? ""])])}>Download CSV</Button>} />
      <div className="relative mb-4 max-w-md"><Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" /><Input placeholder="Search name or phone" value={q} onChange={(e) => setQ(e.target.value)} className="pl-10" /></div>
      {rows === null ? <Spinner /> : rows.length === 0 ? <EmptyState icon={<Users className="h-8 w-8" />} title="No customers yet" hint={loyaltyOn ? "Type a customer's phone number at the POS and they appear here." : "Switch on Loyalty points in Setup so customers are saved when they order."} /> : (
        <Card className="divide-y divide-line">
          {rows.map((c) => (
            <div key={c.id} className="flex items-center gap-3 p-3.5" data-testid={`cust-${c.id}`}>
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-soft font-bold text-brand">{c.full_name[0]?.toUpperCase()}</div>
              <div className="min-w-0 flex-1"><p className="truncate font-semibold">{c.full_name}</p><p className="truncate text-xs text-muted">{c.phone}{c.email ? ` · ${c.email}` : ""}</p></div>
              <div className="hidden text-right text-xs text-muted sm:block"><p>{c.total_orders} orders</p><p className="num">{money(c.total_spent, currency)}</p></div>
              {loyaltyOn && <Badge tone={c.points_balance >= (me?.organization?.loyalty?.min_redeem ?? 100) ? "good" : "neutral"}><Gift className="mr-1 inline h-3 w-3" />{c.points_balance}</Badge>}
            </div>
          ))}
        </Card>
      )}
    </>
  );
}
