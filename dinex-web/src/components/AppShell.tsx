"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AccountModal } from "@/components/AccountModal";
import { UsersRound, CalendarClock, FileCheck2, Receipt, Truck, Armchair, Banknote, BarChart3, Boxes, ChefHat, ClipboardList, CreditCard, FileText, HandCoins, LayoutDashboard, Layers, LogOut, MapPin, MoreHorizontal, X, Moon, ReceiptText, Settings2, Store, Sun, AlertTriangle, Users, Timer, Wallet } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { Paywall } from "@/components/Paywall";
import { OfflineBar, SyncPill } from "@/components/SyncPill";
import { pendingCount } from "@/lib/offline/outbox";
import { Logo } from "./Logo";
import { cn } from "./ui";

interface NavItem { href: string; label: string; icon: typeof Boxes; show: boolean }

function useTheme() {
  const [dark, setDark] = useState(false);
  useEffect(() => { setDark(document.documentElement.classList.contains("dark")); }, []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("dinex_theme", next ? "dark" : "light");
  };
  return { dark, toggle };
}

export function AppShell({ children }: { children: ReactNode }) {
  const { me, logout, location, setLocationId } = useAuth();
  const signOut = async () => {
    const n = await pendingCount();
    if (n > 0 && !confirm(`${n} order${n === 1 ? " is" : "s are"} saved on this device and not sent yet. They stay on this device and are sent after you sign in again with internet. Sign out anyway?`)) return;
    logout();
  };
  const pathname = usePathname();
  const [more, setMore] = useState(false);
  const [account, setAccount] = useState(false);
  useEffect(() => { setMore(false); }, [pathname]);
  const { dark, toggle } = useTheme();
  if (!me) return null;

  const platform = me.role === "PLATFORM";
  const nav: NavItem[] = platform ? [
    { href: "/admin", label: "Overview", icon: LayoutDashboard, show: true },
    { href: "/admin/restaurants", label: "Restaurants", icon: Store, show: true },
    { href: "/admin/payments", label: "Payments", icon: Banknote, show: true },
    { href: "/admin/invoices", label: "Invoices", icon: FileText, show: true },
    { href: "/admin/plans", label: "Plans", icon: Layers, show: true },
  ] : [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, show: true },
    { href: "/pos", label: "Point of Sale", icon: ReceiptText, show: me.can_operate_pos },
    { href: "/orders", label: "Orders", icon: ClipboardList, show: me.can_operate_pos },
    { href: "/customers", label: "Customers", icon: UsersRound, show: me.can_operate_pos },
    { href: "/kitchen", label: "Kitchen", icon: ChefHat, show: me.can_operate_pos },
    { href: "/tables", label: "Tables", icon: Armchair, show: me.can_operate_pos },
    { href: "/reservations", label: "Reservations", icon: CalendarClock, show: me.can_operate_pos },
    { href: "/staff", label: "Staff", icon: Users, show: me.can_view_reports },
    { href: "/kiosk", label: "Attendance", icon: Timer, show: me.can_operate_pos && !me.can_view_reports },
    { href: "/cash", label: "Cash desk", icon: HandCoins, show: me.can_operate_pos },
    { href: "/inventory", label: "Inventory", icon: Boxes, show: !!me.organization },
    { href: "/purchases", label: "Purchases", icon: Truck, show: me.can_view_reports },
    { href: "/expenses", label: "Expenses", icon: Receipt, show: me.can_view_reports },
    { href: "/reports", label: "Reports", icon: BarChart3, show: me.can_view_reports },
    { href: "/day-report", label: "End of day", icon: FileCheck2, show: me.can_view_reports },
    { href: "/payroll", label: "Payroll", icon: Wallet, show: me.is_owner },
    { href: "/setup", label: "Setup", icon: Settings2, show: me.is_owner },
    { href: "/billing", label: "Billing", icon: CreditCard, show: me.is_owner && !!me.subscription },
  ].filter((n) => n.show);

  const initials = (me.first_name?.[0] ?? me.username[0] ?? "?").toUpperCase();
  const gated = !!me.subscription?.blocked && me.role !== "PLATFORM" && !pathname.startsWith("/billing");
  const isActive = (href: string) => pathname === href || (href !== "/admin" && pathname.startsWith(href + "/"));

  return (
    <div className="flex min-h-screen">
      {/* Sidebar (desktop) */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col bg-side text-side-ink lg:flex lg:w-[4.75rem] 2xl:w-[17rem]">
        <div className="flex items-center justify-center gap-3 px-3 py-6 2xl:justify-start 2xl:px-6 2xl:py-7">
          <Logo className="h-10 w-10" />
          <div className="hidden 2xl:block">
            <p className="font-display text-xl font-extrabold leading-none tracking-tight text-white">DineX</p>
            <p className="mt-1 text-xs opacity-60">{platform ? "Admin" : "by XverLabs"}</p>
          </div>
        </div>
        <nav className="scroll-thin flex-1 space-y-0.5 overflow-y-auto px-2 pb-4 2xl:px-3">
          {nav.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href}
              aria-current={isActive(href) ? "page" : undefined} title={label} aria-label={label}
              className={cn("group relative flex min-h-[44px] items-center justify-center gap-3 rounded-xl px-0 text-sm font-medium transition 2xl:justify-start 2xl:px-3",
                isActive(href) ? "bg-side-hover text-white" : "text-side-ink/80 hover:bg-side-hover/70 hover:text-white")}>
              {isActive(href) && <span className="absolute inset-y-2 left-0 w-1 rounded-r-full bg-accent" />}
              <Icon className={cn("h-[18px] w-[18px]", isActive(href) && "text-accent")} /><span className="hidden 2xl:inline">{label}</span>
            </Link>
          ))}
        </nav>
        <div className="border-t border-white/10 p-2 2xl:p-4">
          <div className="flex flex-col items-center gap-2 2xl:flex-row 2xl:gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-full bg-brand-gradient text-sm font-bold text-white">{initials}</div>
            <div className="hidden min-w-0 flex-1 2xl:block">
              <p className="truncate text-sm font-semibold text-white">{me.first_name || me.username}</p>
              <p className="truncate text-xs opacity-60">{me.is_owner ? "Owner" : location?.role === "MANAGER" ? "Manager" : me.organization ? "Cashier" : "XverLabs"}</p>
            </div>
            <button onClick={signOut} title="Sign out" aria-label="Sign out" className="grid h-10 w-10 place-items-center rounded-xl opacity-70 hover:bg-side-hover hover:opacity-100"><LogOut className="h-4 w-4" /></button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line/70 bg-bg/80 px-4 pb-2.5 pt-[calc(0.625rem+env(safe-area-inset-top))] backdrop-blur-md md:px-8">
          <div className="flex items-center gap-3 lg:hidden"><Logo className="h-8 w-8" /><span className="hidden font-display font-extrabold min-[420px]:inline">DineX</span></div>
          <div className="hidden min-w-0 lg:block">
            <p className="truncate text-sm font-semibold">{me.organization?.name ?? "XverLabs Platform"}</p>
          </div>
          <div className="flex min-w-0 items-center gap-1.5 sm:gap-2">
            {me.organization && <SyncPill />}
            {me.locations.length > 0 && (
              <label className="flex min-h-[40px] min-w-0 items-center gap-2 rounded-xl border border-line bg-surface px-2.5 text-sm shadow-sm sm:px-3">
                <MapPin className="h-4 w-4 text-brand" />
                {me.locations.length > 1 ? (
                  <select aria-label="Location" value={location?.id} onChange={(e) => setLocationId(Number(e.target.value))}
                    className="min-w-0 max-w-[6.5rem] truncate bg-transparent pr-1 font-medium focus:outline-none sm:max-w-none">
                    {me.locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                  </select>
                ) : <span className="max-w-[5.5rem] truncate whitespace-nowrap font-medium sm:max-w-none">{location?.name}</span>}
              </label>
            )}
            <button onClick={() => setAccount(true)} aria-label="My account" data-testid="account-btn" className="grid h-10 w-10 place-items-center rounded-xl border border-line bg-surface text-sm font-bold text-brand shadow-sm hover:bg-sunken">{(me.first_name || me.username)[0]?.toUpperCase()}</button>
            <button onClick={toggle} aria-label="Toggle dark mode" className="grid h-10 w-10 place-items-center rounded-xl border border-line bg-surface text-muted shadow-sm hover:text-ink">
              {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </header>

        <AccountModal open={account} onClose={() => setAccount(false)} />
        {me.organization && <OfflineBar />}
        {me.subscription?.message && (
          <div className={cn("flex items-center gap-3 px-4 py-2.5 text-sm font-medium md:px-8", me.subscription.blocked ? "bg-bad text-white" : "bg-warn-soft text-warn")}>
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span className="flex-1">{me.subscription.message}</span>
            {me.is_owner && <Link href="/billing" className="shrink-0 underline">Billing</Link>}
          </div>
        )}
        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 pb-28 md:px-8 lg:pb-10">{gated ? <Paywall /> : children}</main>

        {/* Bottom tab bar (phones): 4 main tabs + More */}
        {(() => {
          const PRIMARY = platform ? ["/admin", "/admin/restaurants", "/admin/payments"] : ["/dashboard", "/pos", "/orders", "/cash"];
          const main = PRIMARY.map((h) => nav.find((n) => n.href === h)).filter(Boolean) as NavItem[];
          const rest = nav.filter((n) => !main.includes(n));
          const short = (l: string) => l.replace("Point of Sale", "POS").replace("Cash desk", "Cash").replace("Dashboard", "Home");
          const tab = "relative flex min-h-[56px] flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-semibold active:scale-95 transition";
          return (
            <>
              <nav aria-label="Main" className="glass fixed inset-x-0 bottom-0 z-30 flex border-t border-line pb-[env(safe-area-inset-bottom)] lg:hidden">
                {main.map(({ href, label, icon: Icon }) => (
                  <Link key={href} href={href} aria-current={isActive(href) ? "page" : undefined} className={cn(tab, isActive(href) ? "text-brand" : "text-muted")}>
                    <span className={cn("grid h-8 w-14 place-items-center rounded-full transition", isActive(href) && "bg-brand-soft")}><Icon className="h-[22px] w-[22px]" strokeWidth={isActive(href) ? 2.4 : 1.9} /></span>{short(label)}
                  </Link>
                ))}
                {rest.length > 0 && (
                  <button onClick={() => setMore(true)} aria-label="More" className={cn(tab, rest.some((r) => isActive(r.href)) ? "text-brand" : "text-muted")}>
                    <span className={cn("grid h-8 w-14 place-items-center rounded-full", rest.some((r) => isActive(r.href)) && "bg-brand-soft")}><MoreHorizontal className="h-[22px] w-[22px]" /></span>More
                  </button>
                )}
              </nav>
              {more && (
                <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="More">
                  <button aria-label="Close" className="absolute inset-0 bg-black/45" onClick={() => setMore(false)} />
                  <div className="animate-pop absolute inset-x-0 bottom-0 rounded-t-[28px] bg-surface p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] shadow-2xl">
                    <div className="mx-auto mb-4 h-1.5 w-10 rounded-full bg-line" />
                    <div className="mb-3 flex items-center justify-between"><p className="font-display text-lg font-extrabold">Menu</p><button aria-label="Close" onClick={() => setMore(false)} className="grid h-10 w-10 place-items-center rounded-full bg-sunken"><X className="h-4 w-4" /></button></div>
                    <div className="grid grid-cols-3 gap-3">
                      {rest.map(({ href, label, icon: Icon }) => (
                        <Link key={href} href={href} className={cn("flex min-h-[88px] flex-col items-center justify-center gap-2 rounded-2xl border p-3 text-center text-xs font-semibold active:scale-95 transition", isActive(href) ? "border-brand bg-brand-soft text-brand" : "border-line bg-bg")}>
                          <Icon className="h-6 w-6" />{short(label)}
                        </Link>
                      ))}
                    </div>
                    <button onClick={() => { setMore(false); signOut(); }} className="mt-4 flex min-h-[48px] w-full items-center justify-center gap-2 rounded-2xl bg-sunken text-sm font-semibold text-bad"><LogOut className="h-4 w-4" />Sign out</button>
                  </div>
                </div>
              )}
            </>
          );
        })()}
      </div>
    </div>
  );
}

export function PlatformNotice() {
  return (
    <div className="mx-auto mt-16 max-w-md rounded-2xl border border-line bg-surface p-8 text-center shadow-card">
      <ChefHat className="mx-auto mb-3 h-10 w-10 text-brand" />
      <h2 className="font-display text-xl font-extrabold">This page is for restaurants</h2>
      <p className="mt-2 text-sm text-muted">You are signed in as XverLabs staff. Manage restaurants, plans and invoices in DineX Admin.</p>
      <Link href="/admin" className="mt-5 inline-block rounded-xl bg-brand-gradient px-5 py-3 text-sm font-semibold text-white dark:text-[#06231b]">Open DineX Admin</Link>
    </div>
  );
}
