"use client";
import { Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, ArrowRight, BookOpen, Check, Layers, Package, PackageCheck, Store, UtensilsCrossed } from "lucide-react";
import { PlatformNotice } from "@/components/AppShell";
import { Button, EmptyState, PageHeader, Spinner, cn } from "@/components/ui";
import { RestaurantStep } from "@/components/setup/RestaurantStep";
import { FloorsStep } from "@/components/setup/FloorsStep";
import { MenuStep } from "@/components/setup/MenuStep";
import { IngredientsStep } from "@/components/setup/IngredientsStep";
import { RecipesStep } from "@/components/setup/RecipesStep";
import { StockStep } from "@/components/setup/StockStep";
import { useAuth } from "@/lib/auth";

const STEPS = [
  { id: "restaurant", label: "Restaurant", hint: "Tax, service charge, stock rules", icon: Store, view: RestaurantStep },
  { id: "floors", label: "Floors & tables", hint: "Basement, ground floor, tables", icon: Layers, view: FloorsStep },
  { id: "menu", label: "Menu", hint: "Categories, dishes and prices", icon: UtensilsCrossed, view: MenuStep },
  { id: "ingredients", label: "Ingredients", hint: "Chicken, buns, sauces…", icon: Package, view: IngredientsStep },
  { id: "recipes", label: "Recipes", hint: "What each dish uses", icon: BookOpen, view: RecipesStep },
  { id: "stock", label: "Opening stock", hint: "What is on the shelf today", icon: PackageCheck, view: StockStep },
] as const;

function Wizard() {
  const { me, location } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const idx = Math.max(0, STEPS.findIndex((s) => s.id === params.get("step")));
  const step = STEPS[idx];
  const go = (i: number) => router.push(`/setup?step=${STEPS[i].id}`);

  if (me && !me.organization) return <PlatformNotice />;
  if (!me?.is_owner) return <EmptyState title="Owner access only" hint="Only the restaurant owner can change the setup." />;
  if (!location) return <Spinner />;
  const View = step.view;

  return (
    <>
      <PageHeader title="Set up your restaurant" subtitle={`${location.name} · work through the steps in order, or jump to any one`} />
      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <nav aria-label="Setup steps" className="scroll-thin flex gap-2 overflow-x-auto pb-2 lg:block lg:space-y-1.5 lg:overflow-visible lg:pb-0">
          {STEPS.map((s, i) => {
            const active = i === idx; const past = i < idx; const Icon = s.icon;
            return (
              <Link key={s.id} href={`/setup?step=${s.id}`} aria-current={active ? "step" : undefined}
                className={cn("flex shrink-0 items-center gap-3 rounded-xl border px-3.5 py-3 transition lg:w-full", active ? "border-brand bg-brand-soft" : "border-transparent hover:bg-sunken")}>
                <span className={cn("grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm font-bold", active ? "bg-brand text-white" : past ? "bg-good text-white" : "bg-sunken text-muted")}>
                  {past ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                </span>
                <span className="hidden min-w-0 sm:block"><span className={cn("block text-sm font-semibold", active && "text-brand")}>{s.label}</span><span className="hidden text-xs text-muted lg:block">{s.hint}</span></span>
                <span className="text-sm font-semibold sm:hidden">{s.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="min-w-0">
          <div className="mb-5"><p className="text-[13px] font-semibold text-brand">Step {idx + 1} of {STEPS.length}</p><h2 className="text-xl font-bold">{step.label}</h2></div>
          <View />
          <div className="mt-8 flex items-center justify-between border-t border-line pt-5">
            <Button variant="ghost" disabled={idx === 0} onClick={() => go(idx - 1)}><ArrowLeft className="h-4 w-4" />Back</Button>
            {idx < STEPS.length - 1
              ? <Button onClick={() => go(idx + 1)}>Next: {STEPS[idx + 1].label}<ArrowRight className="h-4 w-4" /></Button>
              : <Button onClick={() => router.push("/pos")}>Open the POS<ArrowRight className="h-4 w-4" /></Button>}
          </div>
        </div>
      </div>
    </>
  );
}

export default function SetupPage() {
  return <Suspense fallback={<Spinner />}><Wizard /></Suspense>;
}
