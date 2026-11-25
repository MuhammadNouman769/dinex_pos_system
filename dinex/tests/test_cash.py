"""Phase 3: shifts, payments, refunds, cash movements, cancel rules, audit, reports."""
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.cash.models import AuditLog, Payment
from apps.customers.models import Customer
from apps.orders.models import Order
from tests.base import TenantTestCase, PASSWORD


class CashBase(TenantTestCase):
    def order_total(self, client, qty=2, loc=None):
        """500 each, 10% tax default -> qty 2 = 1100."""
        o = self.new_order(client, loc or self.loc_a)
        self.assertEqual(self.add_item(client, o["id"], self.variant_a, qty).status_code, 201)
        return o

    def staff(self, role, username, loc=None):
        r = self.a.post("/api/v1/organizations/location-staff/", {
            "username": username, "email": f"{username}@x.com", "password": PASSWORD, "first_name": "S", "last_name": "T",
            "location_id": (loc or self.loc_a).id, "role": role}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return self.as_user(get_user_model().objects.get(username=username))

    def set_status(self, client, order, st, reason=""):
        return client.post(f"/api/v1/orders/{order['id']}/status/", {"status": st, "reason": reason}, format="json")


class Shifts(CashBase):
    def test_payment_requires_an_open_shift(self):
        o = self.order_total(self.a)
        r = self.pay(self.a, o["id"])
        self.assertEqual(r.status_code, 400)
        self.assertIn("shift", r.json()["detail"].lower())

    def test_one_open_shift_per_cashier_per_location(self):
        self.open_shift(self.a, self.loc_a)
        r = self.a.post("/api/v1/cash/shifts/open/", {"location": self.loc_a.id, "opening_cash": "0"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_current_shift_endpoint(self):
        self.assertIsNone(self.a.get(f"/api/v1/cash/shifts/current/?location={self.loc_a.id}").json()["shift"])
        self.open_shift(self.a, self.loc_a, "500")
        d = self.a.get(f"/api/v1/cash/shifts/current/?location={self.loc_a.id}").json()["shift"]
        self.assertEqual(Decimal(d["expected_cash"]), Decimal("500"))

    def test_expected_cash_and_difference_on_close(self):
        shift = self.open_shift(self.a, self.loc_a, "1000")
        o = self.order_total(self.a)                                   # total 1100
        self.assertEqual(self.pay(self.a, o["id"], "CASH", 600, tendered="1000").status_code, 201)
        self.assertEqual(self.pay(self.a, o["id"], "CARD", 500, reference="slip-1").status_code, 201)
        m = self.a.post(f"/api/v1/cash/shifts/{shift['id']}/movements/", {"kind": "EXPENSE", "amount": "150", "reason": "Vegetables", "category": "kitchen"}, format="json")
        self.assertEqual(m.status_code, 201, m.content)
        self.a.post(f"/api/v1/cash/shifts/{shift['id']}/movements/", {"kind": "CASH_IN", "amount": "100", "reason": "float top-up"}, format="json")
        live = self.a.get(f"/api/v1/cash/shifts/{shift['id']}/").json()
        # 1000 + 600 cash sales + 100 in - 150 expense = 1550
        self.assertEqual(Decimal(live["expected_cash"]), Decimal("1550.00"))
        self.assertEqual(Decimal(live["methods"]["CARD"]["net"]), Decimal("500.00"))
        r = self.a.post(f"/api/v1/cash/shifts/{shift['id']}/close/", {"counted_cash": "1500", "note": "short"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Decimal(r.json()["difference"]), Decimal("-50.00"))      # Rs 50 short
        self.assertEqual(r.json()["status"], "CLOSED")
        self.assertEqual(self.a.post(f"/api/v1/cash/shifts/{shift['id']}/close/", {"counted_cash": "1"}, format="json").status_code, 400)
        self.assertTrue(AuditLog.objects.filter(action="shift_closed", details__difference="-50.00").exists())

    def test_cannot_move_cash_on_closed_shift_and_expense_needs_reason(self):
        shift = self.open_shift(self.a, self.loc_a)
        r = self.a.post(f"/api/v1/cash/shifts/{shift['id']}/movements/", {"kind": "EXPENSE", "amount": "50"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.a.post(f"/api/v1/cash/shifts/{shift['id']}/close/", {"counted_cash": "1000"}, format="json")
        r = self.a.post(f"/api/v1/cash/shifts/{shift['id']}/movements/", {"kind": "CASH_IN", "amount": "50"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_only_owner_can_reopen(self):
        manager = self.staff("MANAGER", "mgr1")
        shift = self.open_shift(manager, self.loc_a)
        manager.post(f"/api/v1/cash/shifts/{shift['id']}/close/", {"counted_cash": "1000"}, format="json")
        self.assertEqual(manager.post(f"/api/v1/cash/shifts/{shift['id']}/reopen/", {"reason": "mistake"}, format="json").status_code, 403)
        self.assertEqual(self.a.post(f"/api/v1/cash/shifts/{shift['id']}/reopen/", {"reason": ""}, format="json").status_code, 400)
        r = self.a.post(f"/api/v1/cash/shifts/{shift['id']}/reopen/", {"reason": "counted wrong"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(AuditLog.objects.filter(action="shift_reopened").exists())

    def test_cashier_sees_only_own_shifts(self):
        c1, c2 = self.staff("POS_OPERATOR", "c1"), self.staff("POS_OPERATOR", "c2")
        s1 = self.open_shift(c1, self.loc_a)
        self.open_shift(c2, self.loc_a)
        self.assertEqual(c2.get(f"/api/v1/cash/shifts/{s1['id']}/").status_code, 404)
        self.assertEqual(len(c1.get("/api/v1/cash/shifts/").json()["results"]), 1)
        self.assertEqual(len(self.a.get("/api/v1/cash/shifts/").json()["results"]), 2)

    def test_other_restaurant_cannot_touch_my_shift_or_location(self):
        s = self.open_shift(self.a, self.loc_a)
        self.assertEqual(self.b.get(f"/api/v1/cash/shifts/{s['id']}/").status_code, 404)
        self.assertEqual(self.b.post("/api/v1/cash/shifts/open/", {"location": self.loc_a.id, "opening_cash": "0"}, format="json").status_code, 404)


class Payments(CashBase):
    def setUp(self):
        self.shift = self.open_shift(self.a, self.loc_a)

    def test_partial_then_full_payment_updates_status(self):
        o = self.order_total(self.a)
        r = self.pay(self.a, o["id"], "CASH", 400, tendered="500")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Decimal(r.json()["payment"]["change"]), Decimal("100.00"))
        self.assertEqual(r.json()["order"]["payment_status"], "PARTIAL")
        self.assertEqual(Decimal(r.json()["order"]["due"]), Decimal("700.00"))
        r = self.pay(self.a, o["id"], "WALLET")                       # defaults to the balance due
        self.assertEqual(r.json()["order"]["payment_status"], "PAID")
        self.assertEqual(Order.objects.get(pk=o["id"]).payment_status, "PAID")
        self.assertEqual(self.pay(self.a, o["id"], "CASH", 1).status_code, 400)   # already paid

    def test_cannot_overpay_or_underpay_cash_or_use_bad_method(self):
        o = self.order_total(self.a)
        self.assertEqual(self.pay(self.a, o["id"], "CASH", 5000).status_code, 400)
        self.assertEqual(self.pay(self.a, o["id"], "CASH", 500, tendered="100").status_code, 400)
        self.assertEqual(self.pay(self.a, o["id"], "BITCOIN", 100).status_code, 400)
        self.assertEqual(self.pay(self.a, o["id"], "CASH", 0).status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)

    def test_empty_order_has_nothing_to_pay(self):
        o = self.new_order(self.a, self.loc_a)
        self.assertEqual(self.pay(self.a, o["id"], "CASH", 10).status_code, 400)

    def test_cannot_complete_until_paid(self):
        o = self.order_total(self.a)
        for st in ("CONFIRMED", "PREPARING", "READY"):
            self.assertEqual(self.set_status(self.a, o, st).status_code, 200)
        r = self.set_status(self.a, o, "COMPLETED")
        self.assertEqual(r.status_code, 400)
        self.assertIn("payment", r.json()["error"].lower())
        self.pay(self.a, o["id"], "CARD")
        self.assertEqual(self.set_status(self.a, o, "COMPLETED").status_code, 200)

    def test_payment_status_cannot_be_forged_and_paid_order_cannot_be_deleted(self):
        o = self.order_total(self.a)
        self.a.patch(f"/api/v1/orders/{o['id']}/", {"payment_status": "PAID"}, format="json")
        self.assertEqual(Order.objects.get(pk=o["id"]).payment_status, "PENDING")
        self.pay(self.a, o["id"], "CASH", 100)
        self.assertEqual(self.a.delete(f"/api/v1/orders/{o['id']}/").status_code, 400)

    def test_adding_items_after_payment_makes_it_partial_again(self):
        o = self.order_total(self.a, 1)                               # 550
        self.pay(self.a, o["id"], "CASH")
        self.assertEqual(Order.objects.get(pk=o["id"]).payment_status, "PAID")
        self.add_item(self.a, o["id"], self.variant_a, 1)
        self.assertEqual(Order.objects.get(pk=o["id"]).payment_status, "PARTIAL")

    def test_completing_updates_customer_stats(self):
        c = Customer.objects.create(location=self.loc_a, first_name="Ali", phone="03001230000")
        o = self.new_order(self.a, self.loc_a, customer=c.id)
        self.add_item(self.a, o["id"], self.variant_a, 1)
        self.pay(self.a, o["id"], "CASH")
        for st in ("CONFIRMED", "PREPARING", "READY", "COMPLETED"):
            self.set_status(self.a, o, st)
        c.refresh_from_db()
        self.assertEqual((c.total_orders, c.total_spent), (1, Decimal("550.00")))

    def test_other_restaurant_cannot_pay_my_order(self):
        o = self.order_total(self.a)
        self.open_shift(self.b, self.loc_b)
        self.assertEqual(self.pay(self.b, o["id"], "CASH").status_code, 404)


class RefundsAndCancels(CashBase):
    def setUp(self):
        self.shift = self.open_shift(self.a, self.loc_a)
        self.order = self.order_total(self.a)                         # 1100
        self.pay(self.a, self.order["id"], "CASH", 600)
        self.pay(self.a, self.order["id"], "CARD", 500)

    def refund(self, client, **body):
        return client.post(f"/api/v1/cash/orders/{self.order['id']}/refund/", body, format="json")

    def test_refund_reduces_expected_cash_and_is_audited(self):
        r = self.refund(self.a, method="CASH", amount="200", reason="Wrong item served")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["order"]["payment_status"], "PAID" if Decimal(r.json()["order"]["due"]) == 0 else "PARTIAL")
        s = self.a.get(f"/api/v1/cash/shifts/{self.shift['id']}/").json()
        self.assertEqual(Decimal(s["expected_cash"]), Decimal("1000") + 600 - 200)
        self.assertTrue(AuditLog.objects.filter(action="refund", details__reason="Wrong item served").exists())

    def test_refund_rules(self):
        self.assertEqual(self.refund(self.a, method="CASH", amount="100", reason="").status_code, 400)           # reason
        self.assertEqual(self.refund(self.a, method="CASH", amount="700", reason="too much").status_code, 400)   # > paid by cash
        self.assertEqual(self.refund(self.a, method="WALLET", amount="10", reason="never paid").status_code, 400)

    def test_cashier_cannot_refund(self):
        cashier = self.staff("POS_OPERATOR", "cashr")
        self.assertEqual(self.refund(cashier, method="CASH", amount="10", reason="because").status_code, 403)

    def test_full_refund_marks_refunded_and_allows_cancel(self):
        self.refund(self.a, method="CASH", amount="600", reason="customer left")
        r = self.refund(self.a, method="CARD", amount="500", reason="customer left")
        self.assertEqual(r.json()["order"]["payment_status"], "REFUNDED")
        self.assertEqual(self.set_status(self.a, self.order, "CANCELLED", "customer left").status_code, 200)

    def test_cannot_cancel_a_paid_order(self):
        r = self.set_status(self.a, self.order, "CANCELLED", "no longer wanted")
        self.assertEqual(r.status_code, 400)
        self.assertIn("refund", r.json()["error"].lower())

    def test_cancel_needs_reason_and_is_audited(self):
        o = self.order_total(self.a)
        self.assertEqual(self.set_status(self.a, o, "CANCELLED").status_code, 400)
        self.assertEqual(self.set_status(self.a, o, "CANCELLED", "Customer left").status_code, 200)
        order = Order.objects.get(pk=o["id"])
        self.assertEqual((order.cancel_reason, order.cancelled_by_id), ("Customer left", self.owner_a.id))
        self.assertTrue(AuditLog.objects.filter(action="order_cancelled", object_id=o["id"]).exists())

    def test_cashier_can_cancel_unsent_order_but_not_one_in_the_kitchen(self):
        cashier = self.staff("POS_OPERATOR", "cashx")
        o = self.order_total(cashier)
        self.assertEqual(self.set_status(cashier, o, "CANCELLED", "wrong table").status_code, 200)
        o2 = self.order_total(cashier)
        self.set_status(cashier, o2, "CONFIRMED")
        self.assertEqual(self.set_status(cashier, o2, "CANCELLED", "changed mind").status_code, 403)
        self.assertEqual(self.set_status(self.a, o2, "CANCELLED", "changed mind").status_code, 200)

    def test_discount_is_manager_only_and_audited(self):
        cashier = self.staff("POS_OPERATOR", "cashd")
        o = self.order_total(cashier)
        r = cashier.patch(f"/api/v1/orders/{o['id']}/", {"discount": "50"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.a.patch(f"/api/v1/orders/{o['id']}/", {"discount": "50"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(AuditLog.objects.filter(action="discount", object_id=o["id"]).exists())
        r = cashier.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "TAKEAWAY", "discount": "10"}, format="json")
        self.assertEqual(r.status_code, 400)


class ReportsAndAudit(CashBase):
    def make_sale(self, client, qty, method="CASH"):
        o = self.order_total(client, qty)
        self.pay(client, o["id"], method)
        for st in ("CONFIRMED", "PREPARING", "READY", "COMPLETED"):
            self.set_status(client, o, st)
        return o

    def test_sales_report_totals_methods_exceptions_and_cost(self):
        # recipe for the burger: one bun (Rs 30) -> cost 30 per burger
        ing = self.a.post("/api/v1/inventory/ingredients/", {"name": "Bun", "base_unit": "PCS", "cost_per_unit": "30"}, format="json").json()["id"]
        self.a.put(f"/api/v1/inventory/recipes/variant/{self.variant_a.id}/", {"lines": [{"ingredient": ing, "quantity": "1"}]}, format="json")
        self.open_shift(self.a, self.loc_a)
        self.make_sale(self.a, 2, "CASH")                              # 1100
        o2 = self.make_sale(self.a, 1, "CARD")                         # 550
        self.refund = self.a.post(f"/api/v1/cash/orders/{o2['id']}/refund/", {"method": "CARD", "amount": "50", "reason": "cold food"}, format="json")
        x = self.order_total(self.a); self.set_status(self.a, x, "CANCELLED", "walked out")

        r = self.a.get(f"/api/v1/cash/reports/sales/?location={self.loc_a.id}")
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertEqual(Decimal(d["summary"]["gross_sales"]), Decimal("1650.00"))
        self.assertEqual(Decimal(d["summary"]["refunds"]), Decimal("50.00"))
        self.assertEqual(Decimal(d["summary"]["net_sales"]), Decimal("1600.00"))
        self.assertEqual(d["summary"]["orders"], 2)
        self.assertEqual(Decimal(d["by_method"]["CASH"]), Decimal("1100.00"))
        self.assertEqual(Decimal(d["by_method"]["CARD"]), Decimal("500.00"))
        self.assertEqual(Decimal(d["summary"]["food_cost"]), Decimal("90.00"))          # 3 burgers x 30
        self.assertEqual(Decimal(d["summary"]["food_profit"]), Decimal("1410.00"))       # 1500 subtotal - 90
        self.assertEqual(d["top_items"][0]["quantity"], 3)
        self.assertEqual(d["exceptions"]["cancelled"]["count"], 1)
        self.assertEqual(d["exceptions"]["cancelled"]["orders"][0]["reason"], "walked out")
        self.assertEqual(d["exceptions"]["refunds"]["count"], 1)
        self.assertEqual(d["cashiers"][0]["cancellations"], 1)

    def test_report_flags_items_without_recipe(self):
        self.open_shift(self.a, self.loc_a)
        self.make_sale(self.a, 1)
        d = self.a.get("/api/v1/cash/reports/sales/").json()
        self.assertEqual(d["items_without_recipe"], ["Burger"])

    def test_report_is_for_owner_and_manager_only(self):
        cashier = self.staff("POS_OPERATOR", "rc1")
        self.assertEqual(cashier.get("/api/v1/cash/reports/sales/").status_code, 403)
        manager = self.staff("MANAGER", "rm1")
        self.assertEqual(manager.get("/api/v1/cash/reports/sales/").status_code, 200)
        self.assertEqual(self.b.get(f"/api/v1/cash/reports/sales/?location={self.loc_a.id}").status_code, 403)

    def test_report_bad_dates(self):
        self.assertEqual(self.a.get("/api/v1/cash/reports/sales/?from=oops").status_code, 400)
        self.assertEqual(self.a.get("/api/v1/cash/reports/sales/?from=2026-02-01&to=2026-01-01").status_code, 400)
        self.assertEqual(self.a.get("/api/v1/cash/reports/sales/?from=2020-01-01&to=2026-01-01").status_code, 400)

    def test_report_shows_short_shifts(self):
        s = self.open_shift(self.a, self.loc_a, "1000")
        self.a.post(f"/api/v1/cash/shifts/{s['id']}/close/", {"counted_cash": "900"}, format="json")
        d = self.a.get("/api/v1/cash/reports/sales/").json()
        self.assertEqual(Decimal(d["shift_differences"][0]["difference"]), Decimal("-100.00"))

    def test_audit_log_is_owner_only_and_tenant_scoped(self):
        self.open_shift(self.a, self.loc_a)
        rows = self.a.get("/api/v1/cash/audit/").json()["results"]
        self.assertIn("shift_opened", [r["action"] for r in rows])
        self.assertEqual(self.b.get("/api/v1/cash/audit/").json()["results"], [])
        manager = self.staff("MANAGER", "am1")
        self.assertEqual(manager.get("/api/v1/cash/audit/").status_code, 403)


class StaleWrites(CashBase):
    def test_a_status_change_never_overwrites_a_payment_taken_in_between(self):
        self.open_shift(self.a, self.loc_a)
        o = self.order_total(self.a)
        stale = Order.objects.get(pk=o["id"])                # kitchen screen loaded the order earlier…
        self.assertEqual(self.pay(self.a, o["id"], "CARD").status_code, 201)   # …cashier then takes payment…
        stale.update_status("CONFIRMED", user=self.owner_a)  # …and the kitchen taps "send to kitchen"
        fresh = Order.objects.get(pk=o["id"])
        self.assertEqual((fresh.status, fresh.payment_status), ("CONFIRMED", "PAID"))

    def test_status_change_keeps_stock_flag_and_totals(self):
        o = self.order_total(self.a)
        stale = Order.objects.get(pk=o["id"])
        self.add_item(self.a, o["id"], self.variant_a, 1)    # totals change after `stale` was loaded
        stale.update_status("CONFIRMED", user=self.owner_a)
        self.assertEqual(Order.objects.get(pk=o["id"]).total_amount, Decimal("1650.00"))


class PartialRefundKeepsBillPaid(CashBase):
    def test_part_refund_does_not_reopen_the_bill(self):
        self.open_shift(self.a, self.loc_a)
        o = self.order_total(self.a)                                   # 1100
        self.pay(self.a, o["id"], "CASH")
        r = self.a.post(f"/api/v1/cash/orders/{o['id']}/refund/", {"method": "CASH", "amount": "100", "reason": "Cold food"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual((r.json()["order"]["payment_status"], Decimal(r.json()["order"]["due"])), ("PAID", Decimal("0")))
        for st in ("CONFIRMED", "PREPARING", "READY", "COMPLETED"):
            self.assertEqual(self.set_status(self.a, o, st).status_code, 200, st)    # can still be completed
        self.assertEqual(self.pay(self.a, o["id"], "CASH", 50).status_code, 400)     # nothing more to pay
