"""One-shot order placement used by the POS, including orders saved offline and synced later."""
import uuid
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.catalog.models import Deal, DealItem
from apps.cash.models import Payment, Shift
from apps.orders.models import Order
from tests.base import TenantTestCase

URL = "/api/v1/orders/sync/"


class _NoTax:
    def setUp(self):
        super().setUp()
        from apps.organizations.models import Location
        Location.objects.update(tax_rate=0, service_charge_rate=0)


class OrderSyncTests(_NoTax, TenantTestCase):
    def body(self, **extra):
        return {"client_uuid": str(uuid.uuid4()), "location": self.loc_a.id, "order_type": "TAKEAWAY",
                "items": [{"product_variant": self.variant_a.id, "quantity": 2}], **extra}

    def test_places_a_confirmed_order_in_one_request(self):
        r = self.a.post(URL, self.body(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        o = r.json()["order"]
        self.assertEqual((o["status"], o["subtotal"], len(o["items"])), ("CONFIRMED", "1000.00", 1))
        self.assertTrue(r.json()["created"])

    def test_same_client_uuid_never_makes_a_second_order(self):
        b = self.body()
        first = self.a.post(URL, b, format="json")
        again = self.a.post(URL, b, format="json")
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertFalse(again.json()["created"])
        self.assertEqual(first.json()["order"]["id"], again.json()["order"]["id"])
        self.assertEqual(Order.objects.filter(location=self.loc_a).count(), 1)

    def test_client_cannot_set_prices(self):
        b = self.body()
        b["items"][0]["unit_price"] = "1"
        r = self.a.post(URL, b, format="json")
        self.assertEqual(r.json()["order"]["subtotal"], "1000.00")

    def test_payment_is_recorded_when_a_shift_is_open(self):
        self.open_shift(self.a, self.loc_a)
        r = self.a.post(URL, self.body(payments=[{"method": "CASH", "amount": "1000", "tendered": "1000"}]), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["order"]["payment_status"], "PAID")
        self.assertEqual(r.json()["payment_warnings"], [])

    def test_no_shift_keeps_the_order_and_warns(self):
        r = self.a.post(URL, self.body(payments=[{"method": "CASH", "amount": "1000"}]), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["order"]["payment_status"], "PENDING")
        self.assertEqual(len(r.json()["payment_warnings"]), 1)

    def test_offline_payment_goes_to_the_shift_open_when_it_was_taken(self):
        shift = Shift.objects.create(location=self.loc_a, opened_by=self.owner_a, opening_cash=0)
        Shift.objects.filter(pk=shift.pk).update(opened_at=timezone.now() - timedelta(hours=10))
        placed = timezone.now() - timedelta(hours=8)
        self.a.post(f"/api/v1/cash/shifts/{shift.id}/close/", {"counted_cash": "0"}, format="json")
        Shift.objects.filter(pk=shift.pk).update(closed_at=timezone.now() - timedelta(hours=6))
        new_shift = self.open_shift(self.a, self.loc_a)
        r = self.a.post(URL, self.body(offline=True, placed_at=placed.isoformat(),
                                       payments=[{"method": "CASH", "amount": "1000"}]), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        pay = Payment.objects.get(order_id=r.json()["order"]["id"])
        self.assertEqual(pay.shift_id, shift.id)
        self.assertNotEqual(pay.shift_id, new_shift["id"])
        o = Order.objects.get(pk=r.json()["order"]["id"])
        self.assertTrue(o.is_offline)
        self.assertAlmostEqual(o.created_at.timestamp(), placed.timestamp(), delta=2)

    def test_future_or_ancient_placed_at_falls_back_to_server_time(self):
        for when in (timezone.now() + timedelta(days=2), timezone.now() - timedelta(days=60)):
            r = self.a.post(URL, self.body(placed_at=when.isoformat()), format="json")
            o = Order.objects.get(pk=r.json()["order"]["id"])
            self.assertLess(abs((o.created_at - timezone.now()).total_seconds()), 30)

    def test_bad_order_leaves_nothing_behind(self):
        before = Order.objects.count()
        b = self.body()
        b["items"].append({"product_variant": self.variant_b.id, "quantity": 1})   # other restaurant's product
        r = self.a.post(URL, b, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(Order.objects.count(), before)

    def test_needs_items_and_valid_type(self):
        self.assertEqual(self.a.post(URL, {"client_uuid": str(uuid.uuid4()), "location": self.loc_a.id,
                                           "order_type": "TAKEAWAY", "items": []}, format="json").status_code, 400)
        self.assertEqual(self.a.post(URL, self.body(order_type="DINE_IN"), format="json").status_code, 400)

    def test_other_restaurants_location_is_not_reachable(self):
        r = self.a.post(URL, self.body(location=self.loc_b.id), format="json")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Order.objects.filter(location=self.loc_b).count(), 0)

    def test_same_uuid_in_another_restaurant_is_independent(self):
        u = str(uuid.uuid4())
        ra = self.a.post(URL, self.body(client_uuid=u), format="json")
        rb = self.b.post(URL, {"client_uuid": u, "location": self.loc_b.id, "order_type": "TAKEAWAY",
                               "items": [{"product_variant": self.variant_b.id, "quantity": 1}]}, format="json")
        self.assertEqual((ra.status_code, rb.status_code), (201, 201))

    def test_requires_login(self):
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().post(URL, self.body(), format="json").status_code, 401)


class DealSyncTests(_NoTax, TenantTestCase):
    n = 0

    def make_deal(self, **kw):
        now = timezone.now()
        DealSyncTests.n += 1
        deal = Deal.objects.create(organization=self.org_a, name="Zinger Combo", slug=f"zinger-combo-{self.n}",
                                   discount_type=kw.get("discount_type", "FIXED"), discount_value=kw.get("value", 100),
                                   start_at=now - timedelta(days=1), end_at=now + timedelta(days=5),
                                   is_active=kw.get("active", True))
        DealItem.objects.create(deal=deal, product_variant=self.variant_a, quantity=2)
        return deal

    def place(self, deal, qty=1, **extra):
        return self.a.post(URL, {"client_uuid": str(uuid.uuid4()), "location": self.loc_a.id, "order_type": "TAKEAWAY",
                                 "deals": [{"deal": deal.id, "quantity": qty}], **extra}, format="json")

    def test_deal_expands_to_items_and_discounts(self):
        r = self.place(self.make_deal(), qty=2)
        self.assertEqual(r.status_code, 201, r.content)
        o = r.json()["order"]
        self.assertEqual(o["items"][0]["quantity"], 4)
        self.assertEqual(o["items"][0]["deal_name"], "Zinger Combo")
        self.assertEqual((o["subtotal"], o["discount"], o["total_amount"]), ("2000.00", "200.00", "1800.00"))

    def test_percentage_deal(self):
        o = self.place(self.make_deal(discount_type="PERCENTAGE", value=10)).json()["order"]
        self.assertEqual((o["subtotal"], o["total_amount"]), ("1000.00", "900.00"))

    def test_expired_inactive_or_foreign_deal_is_refused(self):
        d = self.make_deal()
        Deal.objects.filter(pk=d.pk).update(end_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(self.place(d).status_code, 400)
        d2 = self.make_deal(active=False)
        self.assertEqual(self.place(d2).status_code, 400)

    def test_deal_discount_needs_no_manager(self):
        self.assertEqual(self.place(self.make_deal()).status_code, 201)
