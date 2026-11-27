"""
python manage.py seed_demo [--reset] [--days 28] [--seed 7]

Builds a believable demo: XverLabs admin + 6 restaurants in different subscription states, with
staff, floors/tables, menu, recipes, ingredients, stock, customers, and weeks of orders, payments,
shifts, refunds, cancellations and expenses. Everything is created through the real services, so
stock, cash and reports are consistent. Time is simulated so the history is dated correctly.
"""
import math
import random
import time as _time
from datetime import datetime, time, timedelta
from decimal import Decimal
from importlib import import_module

from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.billing import services as billing
from apps.billing.models import Invoice, Plan, Subscription
from apps.cash import services as cash
from apps.catalog.models import Product, ProductCategory, ProductVariant
from apps.customers.models import Customer
from apps.inventory import services as inv
from apps.inventory.models import Ingredient, IngredientStock, MovementType, Recipe, RecipeLine
from apps.onboarding.services import create_restaurant
from apps.orders.models import Floor, Order, OrderItem, Table
from apps.orders.utils import generate_order_number
from apps.organizations.management.commands import demo_data as D
from apps.organizations.models import Location, LocationMembership, OrganizationMembership
from apps.payroll import services as payroll
from apps.payroll.models import Advance, PayProfile
from apps.staff import attendance as att
from apps.staff import services as staff_services
from apps.staff.models import AttendanceRecord, Employee, WorkSchedule

User = get_user_model()
PHOTOS = Path(__file__).parent / "demo_images"
PASSWORD = "Demo@12345"
ADMIN = ("xverlabs", "DineX@2026")
WEEKDAY = [0.8, 0.85, 0.9, 1.0, 1.35, 1.5, 1.25]          # Mon..Sun


# ───────────────────────── simulated clock ─────────────────────────
class Clock:
    def __init__(self):
        self.real, self.value = timezone.now, None

    def __call__(self):
        return self.value or self.real()

    def at(self, dt):
        self.value = dt

    def install(self):
        timezone.now = self

    def uninstall(self):
        timezone.now = self.real


clock = Clock()


def at(day, hour):
    return timezone.make_aware(datetime.combine(day, time(int(hour), int((hour % 1) * 60), random.randint(0, 59))))


RESTAURANTS = [
    dict(slug="karachigrill", name="Karachi Grill", owner=("Ayesha", "Khan"), plan="growth", state="active", months=3, span=1.0, cats=None, price=1.0,
         locations=[
             dict(key="dha", name="DHA Phase 6", address="Plot 14-C, Khayaban-e-Shamsheer, DHA Phase 6, Karachi", tax=13, service=5, policy="WARN", base=30, today=True,
                  floors=[("Basement", -1, 4), ("Ground Floor", 0, 10), ("First Floor", 1, 8)], customers=45),
             dict(key="clifton", name="Clifton", address="Block 4, Seaview Road, Clifton, Karachi", tax=13, service=5, policy="WARN", base=19, today=False,
                  floors=[("Ground Floor", 0, 8), ("Rooftop", 3, 6)], customers=30)]),
    dict(slug="lahoretikka", name="Lahore Tikka House", owner=("Usman", "Sheikh"), plan="starter", state="active", months=2, span=0.75, cats=None, price=0.95,
         locations=[dict(key="gulberg", name="Gulberg", address="MM Alam Road, Gulberg III, Lahore", tax=16, service=0, policy="ALLOW", base=21, today=False,
                         floors=[("Ground Floor", 0, 8), ("First Floor", 1, 6)], customers=30)]),
    dict(slug="pizzacorner", name="Pizza Corner", owner=("Sana", "Malik"), plan="growth", state="past_due", months=2, span=0.5,
         cats=["Pizza", "Sides", "Drinks", "Desserts", "Burgers"], price=1.05,
         locations=[dict(key="f7", name="F-7 Markaz", address="Shop 12, Jinnah Super Market, F-7 Markaz, Islamabad", tax=16, service=0, policy="ALLOW", base=14, today=False,
                         floors=[("Ground Floor", 0, 8)], customers=22)]),
    dict(slug="desidhaba", name="Desi Dhaba", owner=("Imran", "Chaudhry"), plan="starter", state="trial_ending", months=0, span=0.2,
         cats=["BBQ", "Karahi", "Rice & Bread", "Drinks"], price=0.9,
         locations=[dict(key="main", name="Susan Road", address="Susan Road, Madina Town, Faisalabad", tax=16, service=0, policy="ALLOW", base=11, today=False,
                         floors=[("Ground Floor", 0, 6)], customers=12)]),
    dict(slug="burgerhub", name="Burger Hub", owner=("Hamza", "Raza"), plan="starter", state="trial_new", months=0, span=0, cats=[], price=1.0,
         locations=[dict(key="main", name="Johar Town", address="Block R, Johar Town, Lahore", tax=16, service=0, policy="ALLOW", base=0, today=False, floors=[], customers=0)]),
    dict(slug="chaiwala", name="Cafe Chai Wala", owner=("Rabia", "Qureshi"), plan="pro", state="suspended", months=2, span=0.6, end_offset=18,
         cats=["Drinks", "Desserts", "Sides", "Burgers"], price=0.9,
         locations=[dict(key="main", name="Cantt", address="Cantt Area, Nishtar Road, Multan", tax=16, service=0, policy="ALLOW", base=10, today=False,
                         floors=[("Ground Floor", 0, 6)], customers=14)]),
]


class Command(BaseCommand):
    help = "Create demo restaurants, staff, menu, recipes, stock, customers and weeks of orders/payments/shifts."

    def add_arguments(self, p):
        p.add_argument("--reset", action="store_true", help="WIPE the whole database first, then seed.")
        p.add_argument("--days", type=int, default=28, help="Days of history for the busiest restaurant (default 28).")
        p.add_argument("--seed", type=int, default=7)

    def handle(self, *a, **o):
        if User.objects.filter(username=ADMIN[0]).exists() and not o["reset"]:
            raise CommandError("Demo data already exists. Use --reset to wipe the database and seed again.")
        random.seed(o["seed"])
        if o["reset"]:
            self.stdout.write("Wiping the database…")
            call_command("flush", interactive=False, verbosity=0)
        for p in import_module("apps.billing.migrations.0002_default_plans").PLANS:
            Plan.objects.get_or_create(code=p["code"], defaults=p)

        self.anchor = timezone.now()          # ONE fixed 'now' for the whole run (immune to clock jumps)
        clock.at(self.anchor)
        clock.install()
        try:
            with transaction.atomic():
                admin = User.objects.create_superuser(ADMIN[0], "admin@xverlabs.demo", ADMIN[1], first_name="XverLabs", last_name="Admin", role="PLATFORM")
                for spec in RESTAURANTS:
                    clock.at(self.anchor)
                    self.build(spec, o["days"], admin)
        finally:
            clock.uninstall()
        self.report()

    # ───────────────────────── a restaurant ─────────────────────────
    def build(self, spec, days, admin):
        t0 = _time.monotonic()
        today = timezone.localtime(self.anchor).date()
        clock.value = at(today - timedelta(days=days + 5), 9)
        loc0 = spec["locations"][0]
        owner, org, first_loc = create_restaurant(
            {"name": spec["name"], "currency": "PKR", "timezone": "Asia/Karachi"},
            {"username": spec["slug"], "email": f"{spec['slug']}@demo.dinex", "password": PASSWORD, "first_name": spec["owner"][0], "last_name": spec["owner"][1]},
            {"name": loc0["name"], "address": loc0["address"], "phone": f"021-3{random.randint(1000000, 9999999)}", "is_primary": True})
        locations = [first_loc]
        for extra in spec["locations"][1:]:
            locations.append(Location.objects.create(organization=org, name=extra["name"], address=extra["address"], is_primary=False))
        for loc, ls in zip(locations, spec["locations"]):
            loc.tax_rate, loc.service_charge_rate, loc.inventory_policy = ls["tax"], ls["service"], ls["policy"]
            loc.save()

        plan = Plan.objects.get(code=spec["plan"])
        catalog = self.make_catalog(org, spec) if spec["cats"] != [] else None
        n_orders = 0
        multi = len(locations) > 1
        for loc, ls in zip(locations, spec["locations"]):
            ctx = self.make_location(org, loc, ls, spec, multi, catalog)
            span = int(days * spec["span"])
            if ctx and span > 0 and catalog:
                n_orders += self.simulate(ctx, span, spec.get("end_offset", 0), ls["today"])
        clock.at(self.anchor)
        self.make_subscription(org, plan, spec, admin)
        self.stdout.write(f"  {spec['name']:<22} {plan.name:<8} {spec['state']:<13} locations={len(locations)} orders={n_orders} ({int(_time.monotonic() - t0)}s)")

    # ───────────────────────── people, floors, customers ─────────────────────────
    def user(self, username, first, last):
        return User.objects.create_user(username=username, email=f"{username}@demo.dinex", password=PASSWORD, first_name=first, last_name=last, role="OWNER")

    def staff(self, org, loc, username, first, last, role):
        u = self.user(username, first, last)
        om = OrganizationMembership.objects.create(user=u, organization=org, role=OrganizationMembership.Role.STAFF, is_active=True)
        LocationMembership.objects.create(organization_membership=om, location=loc, role=role, is_active=True)
        return u

    def make_location(self, org, loc, ls, spec, multi, catalog):
        prefix = spec["slug"] + (f"_{ls['key']}" if multi else "")
        ctx = {"org": org, "loc": loc, "ls": ls, "catalog": catalog, "spec": spec}
        ctx["owner"] = User.objects.get(username=spec["slug"])
        if ls["base"] == 0:
            return None
        names = random.sample(FIRST_POOL, 3)
        ctx["mgr"] = self.staff(org, loc, f"{prefix}_mgr", names[0], random.choice(D.LAST), LocationMembership.Role.MANAGER)
        ctx["c1"] = self.staff(org, loc, f"{prefix}_c1", names[1], random.choice(D.LAST), LocationMembership.Role.POS_OPERATOR)
        ctx["c2"] = self.staff(org, loc, f"{prefix}_c2", names[2], random.choice(D.LAST), LocationMembership.Role.POS_OPERATOR)
        self.make_team(ctx, spec)
        ctx["tables"] = []
        for name, level, count in ls["floors"]:
            floor = Floor.objects.create(location=loc, name=name, level=level)
            for _ in range(count):
                ctx["tables"].append(Table.objects.create(location=loc, floor=floor, table_number=f"T-{len(ctx['tables']) + 1}", capacity=random.choice([2, 4, 4, 4, 6, 8])))
        ctx["customers"] = []
        used = set()
        for _ in range(ls["customers"]):
            while True:
                phone = random.choice(["0300", "0301", "0312", "0321", "0333", "0345", "0302"]) + str(random.randint(1000000, 9999999))
                if phone not in used:
                    used.add(phone); break
            ctx["customers"].append(Customer.objects.create(
                location=loc, first_name=random.choice(D.FIRST), last_name=random.choice(D.LAST), phone=phone,
                address=f"House {random.randint(1, 400)}, Street {random.randint(1, 40)}, {random.choice(D.AREAS)}"))
        return ctx

    def make_team(self, ctx, spec):
        org, loc, ls, today = ctx["org"], ctx["loc"], ctx["ls"], timezone.localtime(self.anchor).date()
        big = ls["base"] >= 20
        plan = [("MANAGER", 1), ("CASHIER", 2), ("WAITER", 6 if big else 3), ("RIDER", 3 if big else 2), ("CHEF", 3 if big else 2), ("HELPER", 2)]
        linked = {"MANAGER": [ctx["mgr"]], "CASHIER": [ctx["c1"], ctx["c2"]]}
        ctx["waiters"], ctx["riders"] = [], []
        used = set()
        for role, n in plan:
            for i in range(n):
                while True:
                    name = f"{random.choice(D.FIRST)} {random.choice(D.LAST)}"
                    if name not in used:
                        used.add(name); break
                user = linked.get(role, [None] * n)[i] if role in linked else None
                if user is not None:
                    name = user.get_full_name()
                emp = Employee.objects.create(
                    organization=org, location=loc, code=staff_services.next_code(org), name=name, role=role, user=user,
                    phone=f"03{random.randint(0, 4)}{random.randint(0, 9)}{random.randint(1000000, 9999999)}",
                    cnic=f"{random.randint(1, 7)}{random.randint(1000, 9999)}-{random.randint(1000000, 9999999)}-{random.randint(1, 9)}",
                    address=f"House {random.randint(1, 300)}, {random.choice(D.AREAS)}",
                    joining_date=today - timedelta(days=random.randint(20, 900)),
                    vehicle=f"Honda CD-70 · {random.choice(['LEB', 'KHI', 'ISB'])}-{random.randint(1000, 9999)}" if role == "RIDER" else "",
                    delivery_commission=random.choice([30, 40, 50]) if role == "RIDER" else 0)
                if role == "WAITER":
                    ctx["waiters"].append(emp)
                elif role == "RIDER":
                    ctx["riders"].append(emp)
                self.give_duty(ctx, emp, role, i, n)
                self.give_pay(emp, role, i)

    DUTY = {"MANAGER": ("10:00", "22:00"), "RIDER": ("12:00", "23:00"), "CHEF": ("11:00", "22:00"), "HELPER": ("10:00", "20:00")}

    def give_duty(self, ctx, emp, role, i, n):
        """Duty hours, a weekly off and an attendance PIN. Demo PINs: manager 1111, day cashier 2222, evening cashier 3333, others 4001, 4002…"""
        if role == "CASHIER":
            hours = [("10:00", "17:00"), ("17:00", "23:30")][i]
        elif role == "WAITER":
            hours = ("12:00", "21:00") if i < n - 2 else (("16:00", "01:00") if i == n - 1 else ("17:00", "23:30"))   # the last waiter works past midnight
        else:
            hours = self.DUTY[role]
        ctx["pin_no"] = ctx.get("pin_no", 4000) + (0 if role in ("MANAGER", "CASHIER") else 1)
        off = [0] if role == "MANAGER" else [random.choice([0, 1, 2, 3])]
        h = lambda x: time(int(x[:2]), int(x[3:]))
        WorkSchedule.objects.create(employee=emp, start_time=h(hours[0]), end_time=h(hours[1]), weekly_off=off,
                                    grace_minutes=10, min_overtime_minutes=30, overtime_multiplier=Decimal("1.5"))
        pin = "1111" if role == "MANAGER" else ("2222" if i == 0 else "3333") if role == "CASHIER" else str(ctx["pin_no"])
        att.set_pin(emp, pin)

    def give_pay(self, emp, role, i):
        """A pay profile: mostly monthly salaries, with some daily-wage and hourly staff so every type shows up."""
        monthly = dict(base=random.choice(range(28000, 38000, 1000)), type="MONTHLY")
        spec = {
            "MANAGER": dict(base=random.choice([75000, 80000, 90000]), type="MONTHLY", allowance=5000),
            "CASHIER": dict(base=random.choice([38000, 42000, 46000]), type="MONTHLY", late="MINUTES"),
            "CHEF": dict(base=random.choice([55000, 65000, 85000]) if i else 90000, type="MONTHLY", allowance=3000),
            "HELPER": dict(base=random.choice([1200, 1300, 1400]), type="DAILY"),
            "RIDER": dict(base=random.choice([22000, 25000, 28000]), type="MONTHLY", allowance=2000),
            "WAITER": [monthly, monthly, dict(base=200, type="HOURLY"), dict(base=1500, type="DAILY")][i % 4],
        }[role]
        PayProfile.objects.create(
            employee=emp, pay_type=spec["type"], base_amount=Decimal(spec["base"]), month_basis=random.choice(["30", "30", "26"]) if spec["type"] == "MONTHLY" else "30",
            fixed_allowance=Decimal(spec.get("allowance", 0)), fixed_deduction=Decimal(500 if role in ("CHEF", "MANAGER") else 0),
            absent_penalty_days=Decimal(1), pay_paid_leave=True, pay_weekly_off=False,
            late_rule=spec.get("late") or ("COUNT" if role == "WAITER" and spec["type"] == "MONTHLY" else "NONE"), late_every=3, late_deduct_days=Decimal("0.5"))

    def make_advances(self, ctx):
        today = timezone.localtime(self.anchor).date()
        pool = list(Employee.objects.filter(location=ctx["loc"], role__in=["WAITER", "RIDER", "HELPER", "CHEF"]))
        for emp in random.sample(pool, max(2, len(pool) // 5)):
            amount = random.choice([6000, 10000, 15000, 20000])
            Advance.objects.create(employee=emp, amount=Decimal(amount), installment=Decimal(random.choice([2000, 2500, 4000, 5000])),
                                   given_on=today - timedelta(days=random.randint(12, 55)), reason=random.choice(["Medical", "House rent", "Family function", "School fees", "Motorbike repair"]), given_by=ctx["owner"])

    def make_payroll(self, ctx, with_today):
        """Last month: finalized (and paid, except at the first branch so 'Pay all' can be tried). This month: a live draft."""
        today = timezone.localtime(self.anchor).date()
        this_month = today.replace(day=1)
        last_month = (this_month - timedelta(days=1)).replace(day=1)
        loc, owner = ctx["loc"], ctx["owner"]
        try:
            run = payroll.generate_run(loc, last_month, owner)
            payroll.finalize_run(run, owner)
            if not with_today:
                clock.at(at(this_month + timedelta(days=random.randint(1, 3)), 11))
                payroll.pay_all(run, owner, random.choice(["BANK", "JAZZCASH", "BANK"]), f"PAY-{last_month:%Y%m}-{random.randint(100, 999)}")
                clock.at(self.anchor)
            run2 = payroll.generate_run(loc, this_month, owner)
            if with_today:
                for slip in list(run2.slips.select_related("employee"))[:2]:
                    payroll.add_adjustment(slip, "BONUS", "Best waiter of the week", Decimal(2000), owner)
        except payroll.PayrollError as e:
            self.stdout.write(self.style.WARNING(f"    payroll for {loc.name}: {e.detail}"))

    def make_attendance(self, ctx, days, with_today):
        """Weeks of check-ins/outs with a believable mix: on time, late, left early, overtime, off-day work, absent, leave."""
        today = timezone.localtime(self.anchor).date()
        now = timezone.localtime(self.anchor)
        rows = []
        for emp in Employee.objects.filter(location=ctx["loc"]).select_related("schedule"):
            sched = emp.schedule
            for day in days:
                if emp.joining_date and day < emp.joining_date:
                    continue
                start, end = att.window(sched, day)
                off = day.weekday() in sched.weekly_off
                rec = AttendanceRecord(employee=emp, date=day, source="KIOSK")
                r = random.random()
                if day == today:
                    if off or start > now:
                        continue
                    if r < 0.04:
                        rec.status, rec.source, rec.note = "ABSENT", "MANAGER", "Called in sick"
                    elif r < 0.14 and (now - start).total_seconds() > 1800:
                        continue                                              # has not arrived yet: shows up as "Not in yet"
                    else:
                        late = random.random() < 0.12
                        rec.check_in = start + timedelta(minutes=random.randint(14, 40) if late else random.randint(-12, 7))
                        rec.check_out = None if now < end else end + timedelta(minutes=random.randint(-4, 10))
                    att.recalc(rec, sched); rows.append(rec); continue
                if off:
                    if r < 0.08:                                             # came in on the day off: all of it is overtime
                        rec.check_in = start + timedelta(minutes=random.randint(-10, 5)); rec.check_out = end + timedelta(minutes=random.randint(-5, 15))
                        rec.source = "MANAGER"; rec.note = "Came in to cover"
                        att.recalc(rec, sched); rows.append(rec)
                    continue
                if r < 0.035:
                    rec.status, rec.source, rec.note = "ABSENT", "MANAGER", random.choice(["No call, no show", "Family emergency", "Not well"])
                elif r < 0.06:
                    rec.status, rec.source, rec.paid_leave, rec.note = "LEAVE", "MANAGER", True, random.choice(["Annual leave", "Sick leave", "Wedding"])
                elif r < 0.07:
                    rec.status, rec.source, rec.paid_leave, rec.note = "LEAVE", "MANAGER", False, "Personal work"
                else:
                    late = random.random() < 0.12
                    rec.check_in = start + timedelta(minutes=random.randint(14, 55) if late else random.randint(-14, 8))
                    x = random.random()
                    if x < 0.015:
                        rec.check_out, rec.auto_closed = end, True            # forgot to check out
                    elif x < 0.07:
                        rec.check_out = end - timedelta(minutes=random.randint(20, 75))     # left early
                    elif x < 0.32:
                        rec.check_out = end + timedelta(minutes=random.randint(25, 160))    # stayed late
                    else:
                        rec.check_out = end + timedelta(minutes=random.randint(-4, 14))
                    if random.random() < 0.15:
                        rec.source = "MANAGER"
                att.recalc(rec, sched); rows.append(rec)
        AttendanceRecord.objects.bulk_create(rows)
        return len(rows)

    # ───────────────────────── menu, ingredients, recipes ─────────────────────────
    def make_catalog(self, org, spec):
        ings, prepared = {}, {}
        for key, (name, unit, cost, par) in D.INGREDIENTS.items():
            ings[key] = Ingredient.objects.create(organization=org, name=name, base_unit=unit, cost_per_unit=Decimal(str(cost)), reorder_level=Decimal(par * 0.25))
        for key, (name, parts) in D.PREPARED.items():
            p = Ingredient.objects.create(organization=org, name=name, base_unit="PCS", is_prepared=True)
            recipe = Recipe.objects.create(ingredient=p, output_quantity=1)
            for k, q in parts.items():
                RecipeLine.objects.create(recipe=recipe, ingredient=ings[k], quantity=q)
            prepared[key] = p
        lookup = {**ings, **prepared}
        cats, dishes = {}, []
        for cat, dish, weight, variants in D.MENU:
            if spec["cats"] is not None and cat not in spec["cats"]:
                continue
            if cat not in cats:
                cats[cat] = ProductCategory.objects.create(organization=org, name=cat, slug=cat.lower().replace(" & ", "-").replace(" ", "-"))
            product = Product.objects.create(organization=org, category=cats[cat], name=dish, slug=dish.lower().replace(" ", "-").replace("(", "").replace(")", ""),
                                             sku=dish.upper().replace(" ", "")[:14] + str(random.randint(100, 999)))
            photo = PHOTOS / D.photo_for(dish)
            if photo.exists():
                product.image.save(photo.name, ContentFile(photo.read_bytes()), save=True)
            vs = []
            for vname, price, recipe in variants:
                v = ProductVariant.objects.create(product=product, name=vname, base_price=Decimal(round(price * spec["price"] / 10) * 10))
                if recipe:
                    r = Recipe.objects.create(product_variant=v, output_quantity=1)
                    for k, q in recipe.items():
                        RecipeLine.objects.create(recipe=r, ingredient=lookup[k], quantity=q)
                vs.append(v)
            dishes.append({"variants": vs, "weight": weight, "name": dish})
        return {"ings": ings, "dishes": dishes}

    # ───────────────────────── subscription ─────────────────────────
    def make_subscription(self, org, plan, spec, admin):
        state = spec["state"]
        today = timezone.localtime(self.anchor).date()
        sub = billing.subscription_of(org)
        if sub:
            sub.delete()
        if state in ("trial_ending", "trial_new"):
            days = 2 if state == "trial_ending" else 12
            sub = Subscription.objects.create(organization=org, plan=plan, status="TRIAL", trial_ends_at=timezone.now() + timedelta(days=days, hours=3))
            return
        months = spec["months"]
        first = billing.add_months(today, -months) + timedelta(days=12)
        sub = Subscription.objects.create(organization=org, plan=plan, status="ACTIVE", trial_ends_at=at(first - timedelta(days=14), 9))
        methods = ["Bank transfer", "JazzCash", "Cash", "Easypaisa"]
        for k in range(months):
            start, end = billing.add_months(first, k), billing.add_months(first, k + 1)
            clock.at(at(start, 10))
            inv = billing.create_invoice(sub, start, end, due_date=start + timedelta(days=7), note="Monthly subscription")
            last = k == months - 1
            if last and state in ("past_due", "suspended"):
                overdue_by = 4 if state == "past_due" else 25
                Invoice.objects.filter(pk=inv.pk).update(due_date=today - timedelta(days=overdue_by))
                sub.current_period_start, sub.current_period_end = billing.add_months(first, k - 1), start
                sub.status = "PAST_DUE" if state == "past_due" else "SUSPENDED"
                sub.suspended_reason = f"Invoice {inv.number} is unpaid." if state == "suspended" else ""
            else:
                clock.at(at(start + timedelta(days=random.randint(0, 3)), 12))
                billing.mark_paid(inv, admin, random.choice(methods), f"TX{random.randint(100000, 999999)}")
        sub.save()
        clock.at(self.anchor)

    # ───────────────────────── simulation ─────────────────────────
    def procure(self, ctx, day):
        clock.at(at(day, 9.3))
        for key, ing in ctx["catalog"]["ings"].items():
            par = D.INGREDIENTS[key][3]
            row = IngredientStock.objects.filter(ingredient=ing, location=ctx["loc"]).first()
            have = row.quantity if row else Decimal(0)
            scale = ctx["ls"]["base"] / 30
            target = Decimal(par * max(scale, 0.45))
            if have < target * Decimal("0.45"):
                cost = ing.cost_per_unit * Decimal(random.uniform(0.95, 1.08))
                inv.purchase(ctx["loc"], ing, (target - have).quantize(Decimal("1")), cost.quantize(Decimal("0.0001")), user=ctx["mgr"], note="Daily purchase")

    def simulate(self, ctx, span, end_offset, with_today):
        today = timezone.localtime(self.anchor).date()
        days = [today - timedelta(days=i) for i in range(span + end_offset, end_offset - 1, -1) if i > 0 or with_today]
        total = 0
        for i, day in enumerate(days):
            is_today = day == today
            self.procure(ctx, day)
            n = int(ctx["ls"]["base"] * WEEKDAY[day.weekday()] * (1 + 0.006 * i) * random.uniform(0.85, 1.15))
            total += self.run_day(ctx, day, n, is_today, bad_day=(i == len(days) // 2))
        today_d = timezone.localtime(self.anchor).date()
        first = (today_d.replace(day=1) - timedelta(days=1)).replace(day=1)
        last = today_d - timedelta(days=end_offset + (0 if with_today else 1))
        att_days = [first + timedelta(days=k) for k in range((last - first).days + 1)]
        self.make_attendance(ctx, att_days, with_today)
        self.make_advances(ctx)
        if ctx["spec"]["state"] in ("active", "past_due"):
            self.make_payroll(ctx, with_today)
        if with_today:
            self.low_stock(ctx)
        return total

    def cashier_for(self, ctx, hour, today_cashier=None):
        return today_cashier or (ctx["c1"] if hour < 17 else ctx["c2"])

    def run_day(self, ctx, day, n, is_today, bad_day):
        loc, mgr, c1, c2 = ctx["loc"], ctx["mgr"], ctx["c1"], ctx["c2"]
        now_local = timezone.localtime(self.anchor) if is_today else None
        now_h = (now_local.hour + now_local.minute / 60) if is_today else 24
        today_cashier = (c1 if now_h < 17 else c2) if is_today else None

        # shifts
        shifts = {}
        clock.at(at(day, 9.9 if not is_today else max(8.0, min(10.0, now_h - 1.5))))
        shifts["mgr"] = cash.open_shift(mgr, loc, 5000)   # the manager keeps a float for cash refunds
        if is_today:
            shifts["cash"] = cash.open_shift(today_cashier, loc, 5000)
        else:
            shifts["c1"] = cash.open_shift(c1, loc, 5000)
            clock.at(at(day, 16.95))
            shifts["c2"] = cash.open_shift(c2, loc, 4000)

        # order times (kept inside opening hours and before the shift ends)
        times = sorted(min(max(random.gauss(13.6, 1.0) if r < .35 else random.gauss(20.4, 1.3) if r < .9 else random.uniform(11.5, 22.5), 11.5), 22.3)
                       for r in (random.random() for _ in range(n)))
        placed = 0
        for h in times:
            if is_today and h > now_h - 0.7:
                continue
            self.place_order(ctx, day, h, today_cashier)
            placed += 1
        if is_today:
            self.settle_riders(ctx, today_cashier, day, max(now_h - 0.4, 9), at(day, max(now_h - 1.5, 9)))   # the latest deliveries stay with the riders
            self.active_orders(ctx, day, now_h, today_cashier)
            return placed

        # expenses & cash movements
        for who, lo, hi in (("c1", 11, 16.5), ("c2", 17.5, 22.5)):
            for _ in range(random.choice([0, 1, 1, 2])):
                cat, why, (a, b) = random.choice(D.EXPENSES)
                clock.at(at(day, random.uniform(lo, hi)))
                cash.add_movement(shifts[who], ctx[who], "EXPENSE", random.randint(a // 50, b // 50) * 50, why, cat)
        if random.random() < 0.08:
            clock.at(at(day, 14))
            cash.add_movement(shifts["c1"], c1, "CASH_IN", 3000, "Float top-up", "")

        self.settle_riders(ctx, c1, day, 16.7, at(day, 16.7))        # riders bring in the cash before the day cashier leaves
        self.settle_riders(ctx, c2, day, 23.7, at(day, 23.76))
        diffs = [0] * 9 + [-50, -100, 20, -200, 100]
        for key, user, hour in (("c1", c1, 17.0), ("c2", c2, 23.85), ("mgr", mgr, 23.9)):
            clock.at(at(day, hour))
            expected = cash.shift_summary(shifts[key])["expected_cash"]
            if key == "c2" and expected > 25000:
                cash.add_movement(shifts[key], user, "SAFE_DROP", Decimal(math.floor(float(expected) * 0.55 / 1000) * 1000), "Cash moved to safe", "")
                expected = cash.shift_summary(shifts[key])["expected_cash"]
            diff = 0 if key == "mgr" else (-500 if (bad_day and key == "c2" and ctx["spec"]["slug"] == "karachigrill") else random.choice(diffs))
            cash.close_shift(shifts[key], user, max(Decimal(0), expected + Decimal(diff)), "Counted at close" if diff == 0 else ("Short: will check" if diff < 0 else "Slightly over"))
        return placed

    def pick_items(self, ctx):
        dishes = ctx["catalog"]["dishes"]
        picked = {}
        for _ in range(random.choices([1, 2, 3, 4, 5], [15, 30, 28, 17, 10])[0]):
            d = random.choices(dishes, [x["weight"] for x in dishes])[0]
            v = d["variants"][0] if random.random() < 0.65 else random.choice(d["variants"])
            picked[v.id] = (v, random.choices([1, 2, 3], [60, 30, 10])[0])
        return list(picked.values())

    def make_order(self, ctx, t, kind, cashier, items):
        loc = ctx["loc"]
        clock.at(t)
        customer = None
        phone = name = address = ""
        if (kind == "DELIVERY" or random.random() < (0.35 if kind == "DINE_IN" else 0.5)) and ctx["customers"]:
            customer = random.choice(ctx["customers"])
            name, phone, address = customer.full_name, customer.phone, customer.address if kind == "DELIVERY" else ""
        elif kind == "DELIVERY":
            phone, address = "03" + str(random.randint(100000000, 499999999)), f"House {random.randint(1, 300)}, {random.choice(D.AREAS)}"
        order = Order.objects.create(
            location=loc, order_type=kind, order_number=generate_order_number(loc.id), table=random.choice(ctx["tables"]) if kind == "DINE_IN" else None,
            customer=customer, customer_name=name, customer_phone=phone, delivery_address=address, created_by=cashier,
            waiter=random.choice(ctx["waiters"]) if kind == "DINE_IN" and ctx["waiters"] and random.random() < 0.92 else None,
            notes=random.choice(["", "", "", "No onions", "Extra spicy", "Less oil", "Pack separately", "No ice"]))
        for v, q in items:
            OrderItem.objects.create(order=order, product_variant=v, product_name=v.product.name, variant_name=v.name, quantity=q, unit_price=v.base_price)
        if random.random() < 0.04:                                  # manager gives a discount
            order.discount = (sum(i.total_price for i in order.items.all()) * Decimal(random.choice([5, 10, 15])) / 100).quantize(Decimal("1"))
            order.save(update_fields=["discount"])
            cash.audit(ctx["mgr"], loc, "discount", order, order_number=order.order_number, discount=order.discount)
        order.calculate_totals()
        return order

    def pay(self, ctx, order, t, hour, today_cashier, kind, noncash=False):
        user = self.cashier_for(ctx, hour, today_cashier)
        clock.at(t)
        due = cash.amount_due(order)
        if due <= 0:
            return
        weights = {"CASH": 60, "WALLET": 30, "CARD": 10} if kind == "DELIVERY" else {"CASH": 52, "CARD": 22, "WALLET": 20, "BANK": 6}
        if noncash:
            weights = {"WALLET": 60, "CARD": 40}
        def one(method, amount, last=False):
            tendered = None
            if method == "CASH":
                r = random.random()
                tendered = amount if r < 0.35 else Decimal(math.ceil(float(amount) / 100) * 100) if r < 0.75 else Decimal(math.ceil(float(amount) / 500) * 500)
            cash.take_payment(order, user, method, amount, tendered=tendered, reference="" if method == "CASH" else f"REF{random.randint(10000, 99999)}")
        if random.random() < 0.08 and due > 600:                     # split bill
            part = (due * Decimal(random.choice([40, 50, 60])) / 100).quantize(Decimal("1"))
            one("CASH", part)
            one(random.choice(["CARD", "WALLET"]), cash.amount_due(order))
        else:
            one(random.choices(list(weights), list(weights.values()))[0], due)

    def place_order(self, ctx, day, h, today_cashier):
        kind = random.choices(["DINE_IN", "TAKEAWAY", "DELIVERY"], [50, 25, 25] if ctx["tables"] else [0, 50, 50])[0]
        cashier = self.cashier_for(ctx, h, today_cashier)
        order = self.make_order(ctx, at(day, h), kind, cashier, self.pick_items(ctx))
        minutes = lambda m: at(day, h) + timedelta(minutes=m)
        r = random.random()

        if r < 0.025:                                              # cancelled before it reached the kitchen
            clock.at(minutes(2))
            order.update_status("CANCELLED", user=cashier, reason=random.choice(D.CANCEL_REASONS))
            return
        clock.at(minutes(1)); order.update_status("CONFIRMED", user=cashier)
        if r < 0.04:                                               # manager cancels after confirmation
            clock.at(minutes(6)); order.update_status("CANCELLED", user=ctx["mgr"], reason=random.choice(D.CANCEL_REASONS))
            return
        prep = random.randint(10, 26)
        prepaid = kind == "DELIVERY" and random.random() < 0.3            # paid online; the rest is cash on delivery
        if kind == "TAKEAWAY":
            self.pay(ctx, order, minutes(2), h, today_cashier, kind)
        if prepaid:
            self.pay(ctx, order, minutes(2), h, today_cashier, kind, noncash=True)
        clock.at(minutes(4)); order.update_status("PREPARING", user=cashier)
        clock.at(minutes(4 + prep)); order.update_status("READY", user=cashier)
        if kind == "DELIVERY":
            clock.at(minutes(6 + prep))
            order.rider = random.choice(ctx["riders"]); order.save(update_fields=["rider"])
            clock.at(minutes(7 + prep)); order.update_status("OUT_FOR_DELIVERY", user=cashier)
            done = 7 + prep + random.randint(15, 38)
        else:
            done = 4 + prep + (random.randint(8, 35) if kind == "DINE_IN" else 3)
        if kind == "DINE_IN":
            self.pay(ctx, order, minutes(done), h + done / 60, today_cashier, kind)
        clock.at(minutes(done + 1)); order.update_status("COMPLETED", user=cashier)

        paid = order.payments.filter(kind="PAYMENT").first()
        if paid and random.random() < 0.012:                       # a refund, approved by the manager
            amount = (paid.amount * Decimal(random.choice([20, 30, 50])) / 100).quantize(Decimal("1"))
            clock.at(minutes(done + 20))
            cash.refund_payment(order, ctx["mgr"], paid.method, amount, random.choice(D.REFUND_REASONS))

    def settle_riders(self, ctx, cashier, day, hour, delivered_before):
        """Riders hand the cash of their delivered orders to the cashier. Now and then a rider comes up a little short."""
        for rider in ctx["riders"]:
            rows = [(o, d) for o, d in staff_services.unsettled_orders(rider)
                    if timezone.localtime(o.delivered_at) < delivered_before]
            if not rows:
                continue
            expected = sum(d for _, d in rows)
            handed = expected
            if random.random() < 0.12:
                handed = max(Decimal(0), expected - Decimal(random.choice([50, 100, 150, 250])))
            clock.at(at(day, hour))
            staff_services.settle(rider, cashier, handed, [o.id for o, _ in rows],
                                  "Short, will bring tomorrow" if handed < expected else "Cash received")

    def active_orders(self, ctx, day, now_h, cashier):
        """A few live orders so the kitchen board, the cash desk and the riders have something on them."""
        steps = ["PENDING", "CONFIRMED", "PREPARING", "READY_UNPAID", "READY_PAID", "PREPARING", "DELIVERY_ROAD", "DELIVERY_NO_RIDER"]
        for i, state in enumerate(steps):
            h = max(now_h - 0.6 + i * 0.07, 8)
            kind = "DELIVERY" if state.startswith("DELIVERY") else ("DINE_IN" if ctx["tables"] and i not in (4,) else "TAKEAWAY")
            order = self.make_order(ctx, at(day, h), kind, cashier, self.pick_items(ctx))
            if kind == "DINE_IN" and order.table:
                Table.objects.filter(pk=order.table_id).update(status="OCCUPIED")
            if state == "PENDING":
                continue
            clock.at(at(day, h) + timedelta(minutes=1)); order.update_status("CONFIRMED", user=cashier)
            if state == "CONFIRMED":
                continue
            clock.at(at(day, h) + timedelta(minutes=3)); order.update_status("PREPARING", user=cashier)
            if state == "PREPARING":
                continue
            clock.at(at(day, h) + timedelta(minutes=12)); order.update_status("READY", user=cashier)
            if state == "READY_PAID":
                self.pay(ctx, order, at(day, h) + timedelta(minutes=13), h, cashier, kind)
            if state == "DELIVERY_ROAD":
                order.rider = random.choice(ctx["riders"]); order.save(update_fields=["rider"])
                clock.at(at(day, h) + timedelta(minutes=14)); order.update_status("OUT_FOR_DELIVERY", user=cashier)

    def low_stock(self, ctx):
        """Leave a few ingredients under their reorder level so the alerts have something to show."""
        clock.at(self.anchor)
        for key in ("cheese", "bun", "chicken"):
            ing = ctx["catalog"]["ings"][key]
            row = IngredientStock.objects.get(ingredient=ing, location=ctx["loc"])
            target = ing.reorder_level * Decimal("0.6")
            if row.quantity > target:
                inv.record_movement(ctx["loc"], ing, target - row.quantity, MovementType.ADJUSTMENT, user=ctx["mgr"], note="Stock count: found less than expected")

    # ───────────────────────── summary ─────────────────────────
    def report(self):
        from apps.cash.models import Payment, Shift
        self.stdout.write(self.style.SUCCESS("\nDemo data ready"))
        self.stdout.write(f"  restaurants={Subscription.objects.count()} orders={Order.objects.count()} customers={Customer.objects.count()} "
                          f"payments={Payment.objects.count()} shifts={Shift.objects.count()} invoices={Invoice.objects.count()}")
        self.stdout.write(f"\n  DineX Admin    : {ADMIN[0]} / {ADMIN[1]}")
        self.stdout.write(f"  Owners         : karachigrill, lahoretikka, pizzacorner, desidhaba, burgerhub, chaiwala  /  {PASSWORD}")
        self.stdout.write(f"  Staff (Karachi): karachigrill_dha_mgr, karachigrill_dha_c1, karachigrill_dha_c2 (and _clifton_*)  /  {PASSWORD}")


FIRST_POOL = ["Waqas", "Noman", "Adnan", "Shahid", "Rizwan", "Tariq", "Junaid", "Danish", "Saima", "Bushra", "Nadia", "Farah", "Komal", "Anum", "Hira", "Aqsa"]
