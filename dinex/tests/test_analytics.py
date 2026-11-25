"""Phase 5.4: analytics for restaurants (overview, menu, staff, inventory, customers) and for XverLabs (platform)."""
from calendar import monthrange
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.analytics import services
from apps.cash.models import Payment
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.organizations.models import Location
from apps.payroll.models import PayrollRun, Payslip
from apps.staff.models import Employee, RiderSettlement
from tests.base import TenantTestCase, PASSWORD

User = get_user_model()
D = lambda x: Decimal(str(x))


class AnBase(TenantTestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.shift = self.open_shift(self.a, self.loc_a, "10000")

    def get(self, name, client=None, loc=None, **q):
        q.setdefault("from", self.today.isoformat()); q.setdefault("to", self.today.isoformat())
        if loc is not False:
            q.setdefault("location", (loc or self.loc_a).id)
        qs = "&".join(f"{k}={v}" for k, v in q.items())
        return (client or self.a).get(f"/api/v1/analytics/{name}/?{qs}")

    def sale(self, qty=1, method="CASH", variant=None, client=None, loc=None, **extra):
        """A paid order (qty items) taken today. Returns the order json."""
        client = client or self.a
        o = self.new_order(client, loc or self.loc_a, **extra)
        r = self.add_item(client, o["id"], variant or self.variant_a, qty)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.pay(client, o["id"], method).status_code, 201)
        return o

    def staff(self, role, username, loc=None):
        r = self.a.post("/api/v1/organizations/location-staff/", {"username": username, "email": f"{username}@x.com", "password": PASSWORD, "first_name": "S", "last_name": "T",
                                                                  "location_id": (loc or self.loc_a).id, "role": role}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return self.as_user(User.objects.get(username=username))

    def hire(self, name, role="WAITER", **extra):
        r = self.a.post("/api/v1/staff/employees/", {"name": name, "role": role, "location": self.loc_a.id, "joining_date": "2026-01-01", **extra}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["id"]

    def recipe(self, variant, lines):
        """lines: [(ingredient_id, qty, unit)]"""
        r = self.a.put(f"/api/v1/inventory/recipes/variant/{variant.id}/", {"lines": [{"ingredient": i, "quantity": q, "unit": u} for i, q, u in lines]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def ingredient(self, name, unit, cost=0, **extra):
        r = self.a.post("/api/v1/inventory/ingredients/", {"name": name, "base_unit": unit, "cost_per_unit": str(cost), **extra}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["id"]


class Overview(AnBase):
    def test_every_number_adds_up(self):
        bun = self.ingredient("Bun", "PCS", 30)
        self.recipe(self.variant_a, [(bun, 1, "pcs")])                                           # food cost Rs 30 per burger
        table = self.a.post("/api/v1/orders/tables/", {"location": self.loc_a.id, "table_number": "T-1", "capacity": 4}, format="json").json()["id"]
        self.sale(2, "CASH", order_type="DINE_IN", table=table)                                   # 1100
        takeaway = self.sale(1, "CARD")                                                           # 550
        cancelled = self.new_order(self.a, self.loc_a)
        self.a.post(f"/api/v1/orders/{cancelled['id']}/status/", {"status": "CANCELLED", "reason": "customer left"}, format="json")
        self.assertEqual(self.a.post(f"/api/v1/cash/orders/{takeaway['id']}/refund/", {"method": "CARD", "amount": 50, "reason": "cold"}, format="json").status_code, 201)
        r = self.get("overview")
        self.assertEqual(r.status_code, 200, r.content)
        k = r.json()["kpis"]
        self.assertEqual((D(k["net_sales"]["value"]), k["orders"]["value"], D(k["average_order"]["value"])), (D(1600), 2, D(800)))
        self.assertEqual((D(k["food_cost"]["value"]), D(k["food_profit"]["value"]), D(k["refunds"]["value"])), (D(90), D(1410), D(50)))     # profit = 1500 subtotal - 90
        self.assertEqual((k["cancel_rate"]["count"], k["cancel_rate"]["of"], k["cancel_rate"]["value"]), (1, 3, 33.3))
        ch = r.json()["channels"]
        self.assertEqual((ch["DINE_IN"]["orders"], D(ch["DINE_IN"]["sales"]), ch["TAKEAWAY"]["orders"], D(ch["TAKEAWAY"]["sales"]), ch["DELIVERY"]["orders"]), (1, D(1100), 1, D(550), 0))
        self.assertEqual({m: D(v) for m, v in r.json()["by_method"].items() if D(v)}, {"CASH": D(1100), "CARD": D(500)})
        self.assertEqual(sum(sum(row) for row in r.json()["heatmap"]), 2)                         # cancelled orders are not "busy"
        self.assertEqual(sum(r.json()["weekday_orders"]), 2)
        self.assertEqual(r.json()["busiest"]["orders"], 2)
        self.assertEqual(len(r.json()["series"]), 1)

    def test_comparison_with_the_period_before(self):
        self.sale(2)                                                                              # 1100 today
        old = self.sale(1)                                                                        # 550, moved to yesterday
        Payment.objects.filter(order_id=old["id"]).update(created_at=timezone.now() - timedelta(days=1))
        k = self.get("overview").json()["kpis"]["net_sales"]
        self.assertEqual((D(k["value"]), D(k["previous"]), k["change"]), (D(1100), D(550), 100.0))
        self.assertEqual(self.get("overview", **{"from": (self.today - timedelta(days=1)).isoformat()}).json()["previous"]["to"], (self.today - timedelta(days=2)).isoformat())

    def test_nothing_sold_means_zeros_and_no_division_errors(self):
        r = self.get("overview").json()
        self.assertEqual((D(r["kpis"]["net_sales"]["value"]), r["kpis"]["net_sales"]["change"], r["kpis"]["cancel_rate"]["value"]), (D(0), None, 0.0))
        self.assertIsNone(r["kpis"]["food_cost_pct"]["value"])
        self.assertIsNone(r["busiest"]["hour"])

    def test_series_has_a_point_for_every_day(self):
        self.sale(1)
        r = self.get("overview", **{"from": (self.today - timedelta(days=2)).isoformat()}).json()
        self.assertEqual([p["date"] for p in r["series"]], [(self.today - timedelta(days=i)).isoformat() for i in (2, 1, 0)])
        self.assertEqual([D(p["net"]) for p in r["series"]], [D(0), D(0), D(550)])
        self.assertEqual(len(r["previous_series"]), 3)

    def test_dates_and_scope_rules(self):
        self.assertEqual(self.get("overview", **{"from": "2026-02-01", "to": "2026-01-01"}).status_code, 400)
        self.assertEqual(self.get("overview", **{"from": "2020-01-01"}).status_code, 400)
        self.assertEqual(self.get("overview", **{"from": "nope"}).status_code, 400)
        self.assertEqual(self.get("overview", loc=False, location="abc").status_code, 400)
        future = self.get("overview", to=(self.today + timedelta(days=30)).isoformat())
        self.assertEqual((future.status_code, future.json()["to"]), (200, self.today.isoformat()))     # the future is clamped to today
        self.assertEqual(self.get("overview", client=self.b).status_code, 404)                          # not my branch
        self.assertEqual(self.get("overview", client=self.b, loc=self.loc_b).status_code, 200)

    def test_all_branches_when_none_is_chosen(self):
        second = Location.objects.create(organization=self.org_a, name="Second", address="Somewhere 123456")
        self.sale(1)
        self.assertEqual(D(self.get("overview", loc=False).json()["kpis"]["net_sales"]["value"]), D(550))

    def test_who_may_look(self):
        self.assertEqual(self.get("overview", client=self.staff("MANAGER", "mgr_an")).status_code, 200)
        cashier = self.staff("POS_OPERATOR", "cash_an")
        for name in ("overview", "menu", "staff", "inventory", "customers"):
            self.assertEqual(self.get(name, client=cashier).status_code, 403, name)
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().get("/api/v1/analytics/overview/").status_code, 401)


class MenuEngineering(AnBase):
    def test_classification_rules(self):
        items = [{"qty": 50, "unit_profit": 300}, {"qty": 40, "unit_profit": 100}, {"qty": 5, "unit_profit": 400}, {"qty": 5, "unit_profit": 50}]
        self.assertEqual(services.classify(items), ["STAR", "PLOWHORSE", "PUZZLE", "DOG"])
        self.assertEqual(services.classify([]), [])
        self.assertEqual(services.classify([{"qty": 3, "unit_profit": 10}]), ["STAR"])             # the only dish is popular and average

    def test_items_with_costs_and_without(self):
        bun = self.ingredient("Bun", "PCS", 30)
        self.recipe(self.variant_a, [(bun, 1, "pcs")])
        from apps.catalog.models import ProductVariant
        water = ProductVariant.objects.create(product=self.variant_a.product, name="Water", base_price=100)        # no recipe
        ProductVariant.objects.create(product=self.variant_a.product, name="Never Sold", base_price=100)
        self.sale(3)
        self.sale(2, variant=water)
        m = self.get("menu").json()
        by = {i["name"]: i for i in m["items"]}
        burger = by["Burger"]
        self.assertEqual((burger["qty"], D(burger["revenue"]), D(burger["cost"]), D(burger["profit"]), burger["margin"]), (3, D(1500), D(90), D(1410), 94.0))
        self.assertEqual((D(burger["unit_price"]), D(burger["unit_profit"])), (D(500), D(470)))
        self.assertEqual((by["Burger · Water"]["klass"], by["Burger · Water"]["cost"], m["unknown"]), ("UNKNOWN", None, 1))
        self.assertEqual(burger["klass"], "STAR")
        self.assertIn("Burger · Never Sold", m["not_selling"])
        self.assertEqual(m["categories"][0]["name"], "Main")
        self.assertEqual(round(sum(i["share"] for i in m["items"])), 100)
        self.assertEqual(self.get("menu", client=self.b, loc=self.loc_b).json()["items"], [])      # nothing of mine leaks to another restaurant

    def test_cancelled_orders_do_not_count(self):
        o = self.sale(2)
        self.a.post(f"/api/v1/cash/orders/{o['id']}/refund/", {"method": "CASH", "amount": 1100, "reason": "all back"}, format="json")
        self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": "CANCELLED", "reason": "after refund"}, format="json")
        self.assertEqual(self.get("menu").json()["items"], [])


class StaffAnalytics(AnBase):
    def test_waiter_leaderboard(self):
        w1, w2 = self.hire("Ali Waiter"), self.hire("Bilal Waiter")
        self.sale(2, waiter=w1); self.sale(1, waiter=w1); self.sale(3, waiter=w2)
        cancel = self.new_order(self.a, self.loc_a, waiter=w2)
        self.a.post(f"/api/v1/orders/{cancel['id']}/status/", {"status": "CANCELLED", "reason": "left"}, format="json")
        rows = {w["name"]: w for w in self.get("staff").json()["waiters"]}
        self.assertEqual((rows["Ali Waiter"]["orders"], D(rows["Ali Waiter"]["sales"]), D(rows["Ali Waiter"]["average_bill"])), (2, D(1650), D(825)))
        self.assertEqual((rows["Bilal Waiter"]["orders"], D(rows["Bilal Waiter"]["sales"])), (1, D(1650)))      # the cancelled one is left out
        self.assertEqual([w["name"] for w in self.get("staff").json()["waiters"]], ["Ali Waiter", "Bilal Waiter"] if D(1650) == D(1650) else [])

    def test_rider_performance_and_cash_shortage(self):
        rider = self.hire("Rider Ali", "RIDER", delivery_commission="40")
        for i in range(3):
            o = self.new_order(self.a, self.loc_a, order_type="DELIVERY", customer_phone="03001112222", delivery_address="House 1, Street 2, Gulberg, Lahore")
            self.add_item(self.a, o["id"], self.variant_a, 1)
            self.a.post(f"/api/v1/staff/orders/{o['id']}/assign-rider/", {"rider": rider}, format="json")
            for st in ("CONFIRMED", "PREPARING", "READY", "OUT_FOR_DELIVERY", "COMPLETED"):
                self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": st}, format="json")
            now = timezone.now()
            Order.objects.filter(pk=o["id"]).update(dispatched_at=now - timedelta(minutes=20 + 10 * i), delivered_at=now)       # 20, 30, 40 minutes
        self.a.post(f"/api/v1/staff/riders/{rider}/settle/", {"handed": 1500}, format="json")                               # owes 1650: Rs 150 short
        r = self.get("staff").json()["riders"][0]
        self.assertEqual((r["deliveries"], r["avg_minutes"], r["slowest_minutes"], D(r["commission"]), D(r["cash_shortage"])), (3, 30.0, 40.0, D(120), D(150)))

    def test_attendance_numbers(self):
        from apps.staff.models import AttendanceRecord
        from apps.staff import attendance as att
        e = self.hire("Ali Waiter")
        self.a.put(f"/api/v1/staff/employees/{e}/schedule/", {"start_time": "00:00", "end_time": "23:59", "weekly_off": [], "grace_minutes": 10, "min_overtime_minutes": 30, "overtime_multiplier": 1.5}, format="json")
        emp = Employee.objects.select_related("schedule").get(pk=e)
        yesterday = self.today - timedelta(days=1)
        for day, status, cin in ((yesterday - timedelta(days=1), "PRESENT", "00:00"), (yesterday, "ABSENT", None)):
            rec = AttendanceRecord(employee=emp, date=day, status=status)
            if status == "PRESENT":
                rec.check_in = timezone.make_aware(timezone.datetime(day.year, day.month, day.day, 0, 0)); rec.check_out = rec.check_in + timedelta(hours=23, minutes=59)
            att.recalc(rec, emp.schedule); rec.save()
        r = self.get("staff", **{"from": (self.today - timedelta(days=2)).isoformat(), "to": (self.today - timedelta(days=1)).isoformat()}).json()["attendance"]
        self.assertEqual((r["scheduled_days"], r["attendance_rate"], r["absent_days"]), (2, 50.0, 1))
        self.assertEqual(r["most_absent"][0]["name"], "Ali Waiter")

    def test_labor_cost_is_for_the_owner_only(self):
        e = self.hire("Ali Waiter")
        first = self.today.replace(day=1)
        run = PayrollRun.objects.create(location=self.loc_a, month=first)
        Payslip.objects.create(run=run, employee_id=e, pay_type="MONTHLY", base_amount=31000, gross=31000, net=31000)
        self.sale(2)                                                                              # net sales Rs 1100 today
        days = monthrange(self.today.year, self.today.month)[1]
        owner = self.get("staff", **{"from": first.isoformat()}).json()
        expected = (D(31000) * self.today.day / days).quantize(Decimal("0.01"))
        self.assertEqual(D(owner["labor"]["cost"]), expected)
        self.assertIsNotNone(owner["labor"]["pct_of_sales"])
        manager = self.get("staff", client=self.staff("MANAGER", "mgr_labor"), **{"from": first.isoformat()}).json()
        self.assertIsNone(manager["labor"])                                                        # payroll stays private
        self.assertIn("attendance", manager)


class InventoryAnalytics(AnBase):
    def test_usage_wastage_and_days_of_cover(self):
        chicken = self.ingredient("Chicken", "G", "0.9")
        sauce = self.ingredient("Sauce", "ML", "0.4")
        self.recipe(self.variant_a, [(chicken, 200, "g"), (sauce, 80, "ml")])
        for ing, qty, unit in ((chicken, 10, "kg"), (sauce, 500, "ml")):
            self.a.post("/api/v1/inventory/stock/movements/", {"location": self.loc_a.id, "ingredient": ing, "movement_type": "OPENING", "quantity": qty, "unit": unit}, format="json")
        o = self.new_order(self.a, self.loc_a)
        self.add_item(self.a, o["id"], self.variant_a, 5)
        self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": "CONFIRMED"}, format="json")             # uses 1000 g chicken and 400 ml sauce
        self.a.post("/api/v1/inventory/stock/movements/", {"location": self.loc_a.id, "ingredient": chicken, "movement_type": "WASTAGE", "quantity": 100, "unit": "g"}, format="json")
        self.a.post("/api/v1/inventory/stock/movements/", {"location": self.loc_a.id, "ingredient": chicken, "movement_type": "ADJUSTMENT", "quantity": -50, "unit": "g"}, format="json")
        r = self.get("inventory").json()
        t = r["totals"]
        self.assertEqual((D(t["used_value"]), D(t["wastage_value"]), D(t["count_losses"])), (D("1060.00"), D("90.00"), D("45.00")))     # 1000x0.9 + 400x0.4 ; 100x0.9 ; 50x0.9
        self.assertEqual(t["wastage_pct"], 8.5)
        self.assertEqual(D(t["stock_value"]), D("7965.00") + D("40.00"))                                         # 8850 g chicken + 100 ml sauce
        self.assertEqual([x["name"] for x in r["top_used"]], ["Chicken", "Sauce"])
        self.assertEqual(r["top_wasted"][0]["name"], "Chicken")
        cover = {c["name"]: c["days_left"] for c in r["cover"]}
        self.assertEqual((cover["Chicken"], cover["Sauce"]), (8.9, 0.3))                                       # stock / one day's use
        self.assertEqual([c["name"] for c in r["running_out"]], ["Sauce"])

    def test_nothing_moved(self):
        r = self.get("inventory").json()
        self.assertEqual((r["top_used"], r["top_wasted"], r["totals"]["wastage_pct"]), ([], [], None))


class CustomerAnalytics(AnBase):
    def test_new_versus_returning(self):
        new = Customer.objects.create(location=self.loc_a, first_name="New", last_name="Customer", phone="03001110001")
        regular = Customer.objects.create(location=self.loc_a, first_name="Regular", last_name="Customer", phone="03001110002")
        old = self.sale(1, customer=regular.id)
        Order.objects.filter(pk=old["id"]).update(created_at=timezone.now() - timedelta(days=5))       # a visit last week
        Payment.objects.filter(order_id=old["id"]).update(created_at=timezone.now() - timedelta(days=5))
        self.sale(2, customer=new.id); self.sale(1, customer=regular.id); self.sale(1)                  # + a walk-in
        r = self.get("customers").json()
        self.assertEqual((r["active"], r["new"], r["returning"], r["repeat_rate"]), (2, 1, 1, 50.0))
        self.assertEqual((r["orders_with_customer"], r["orders_total"], r["identified_pct"]), (2, 3, 66.7))
        self.assertEqual([(t["name"], t["orders"], D(t["spent"])) for t in r["top"]], [("New Customer", 1, D(1100)), ("Regular Customer", 1, D(550))])

    def test_empty(self):
        r = self.get("customers").json()
        self.assertEqual((r["active"], r["repeat_rate"], r["top"]), (0, None, []))


class PlatformAnalytics(AnBase):
    def admin(self):
        return self.as_user(self.platform)

    def action(self, org, name, **extra):
        return self.admin().post(f"/api/v1/platform/restaurants/{org.id}/subscription/", {"action": name, **extra}, format="json")

    def test_access(self):
        self.assertEqual(self.a.get("/api/v1/analytics/platform/").status_code, 403)
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().get("/api/v1/analytics/platform/").status_code, 401)
        self.assertEqual(self.admin().get("/api/v1/analytics/platform/").status_code, 200)

    def test_revenue_funnel_plans_and_aging(self):
        self.assertEqual(self.action(self.org_a, "activate").status_code, 200)                    # Starter, Rs 2,999
        r = self.admin().get("/api/v1/analytics/platform/").json()
        self.assertEqual((D(r["mrr"]), D(r["arr"]), r["paying"], D(r["arpu"]), r["restaurants"]), (D(2999), D(35988), 1, D(2999), 2))
        self.assertEqual((r["funnel"]["started"], r["funnel"]["converted"], r["funnel"]["conversion_pct"], r["funnel"]["churned"]), (2, 1, 50.0, 0))
        this = [m for m in r["revenue_by_month"] if m["month"] == self.today.replace(day=1).isoformat()][0]
        self.assertEqual((D(this["billed"]), D(this["collected"])), (D(2999), D(0)))
        self.assertEqual(len(r["revenue_by_month"]), 12)
        self.assertEqual((r["growth"][-1]["new"], r["growth"][-1]["total"]), (2, 2))
        self.assertEqual([(p["plan"], D(p["mrr"]), p["share"]) for p in r["by_plan"]], [("Starter", D(2999), 100.0)])
        from apps.billing.models import Invoice
        Invoice.objects.update(due_date=self.today - timedelta(days=3))
        aging = {a["bucket"]: a for a in self.admin().get("/api/v1/analytics/platform/").json()["aging"]}
        self.assertEqual((aging["1-7 days"]["invoices"], D(aging["1-7 days"]["amount"]), aging["31+ days"]["invoices"]), (1, D(2999), 0))
        self.action(self.org_b, "suspend", reason="Unpaid")
        r = self.admin().get("/api/v1/analytics/platform/").json()
        self.assertEqual((r["funnel"]["churned"], r["funnel"]["churn_pct"]), (1, 50.0))

    def test_health_scores_and_at_risk(self):
        for _ in range(3):
            self.sale(1)                                                                          # A is busy today
        r = self.admin().get("/api/v1/analytics/platform/").json()
        health = {h["name"]: h for h in r["health"]}
        a, b = health["Org A"], health["Org B"]
        self.assertEqual((a["orders_7d"], a["days_since_order"]), (3, 0))
        self.assertGreaterEqual(a["score"], 40 + 15)                                              # recent, and no earlier week to compare with
        self.assertEqual((b["health"], b["orders_7d"]), ("AT_RISK", 0))
        self.assertIn("Has never taken an order", b["reasons"])
        self.assertEqual([h["name"] for h in r["at_risk"]], ["Org B"])
        self.assertEqual(r["health"][0]["name"], "Org B")                                          # worst first
        self.assertEqual(r["top_by_sales"][0]["name"], "Org A")
        self.assertEqual(D(r["sales_30d"]), D(1650))

    def test_a_week_of_decline_shows_up(self):
        for _ in range(2):
            o = self.sale(1)
            Order.objects.filter(pk=o["id"]).update(created_at=timezone.now() - timedelta(days=10))      # last-but-one week
        self.sale(1)                                                                                      # this week: half as many
        h = {x["name"]: x for x in self.admin().get("/api/v1/analytics/platform/").json()["health"]}["Org A"]
        self.assertEqual((h["orders_7d"], h["orders_prev_7d"], h["trend"]), (1, 2, -50.0))

    def test_feature_adoption(self):
        bun = self.ingredient("Bun", "PCS", 30)
        self.recipe(self.variant_a, [(bun, 1, "pcs")])                                           # A uses recipes and has an open cash shift
        r = self.admin().get("/api/v1/analytics/platform/").json()
        ad = {x["key"]: x for x in r["adoption"]}
        self.assertEqual((ad["recipes"]["restaurants"], ad["recipes"]["pct"]), (1, 50))
        self.assertEqual((ad["cash_shifts"]["restaurants"], ad["payroll"]["restaurants"]), (1, 0))
