"""Loyalty points: rules set by each restaurant, earn on paid bills, use as discount, refunds, emails."""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core import mail
from django.test import override_settings
from django.utils import timezone

from apps.customers.models.customer import Customer
from tests.base import TenantTestCase

LOY = "/api/v1/loyalty/"


class Base(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.open_shift(self.a, self.loc_a, "1000")

    def rules(self, **kw):
        body = {"enabled": True, "spend_per_point": "100", "point_value": "1", "min_redeem": 100, **kw}
        r = self.a.patch(LOY + "settings/", body, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def bill(self, qty=2, phone="0300111", email="", name="Ali Khan", client=None):
        """Create an order with a customer through the real sync endpoint (500 each)."""
        import uuid
        c = client or self.a
        r = c.post("/api/v1/orders/sync/", {"client_uuid": str(uuid.uuid4()), "location": self.loc_a.id, "order_type": "TAKEAWAY",
                   "customer_name": name, "customer_phone": phone, "customer_email": email,
                   "items": [{"product_variant": self.variant_a.id, "quantity": qty}]}, format="json")
        self.assertIn(r.status_code, (200, 201), r.content)
        return r.json()["order"]

    def pay_all(self, order):
        total = Decimal(str(self.a.get(f"/api/v1/orders/{order['id']}/").json()["total_amount"]))
        r = self.pay(self.a, order["id"], "CASH", total)
        self.assertEqual(r.status_code, 201, r.content)
        return total

    def customer(self, phone="0300111"):
        return Customer.objects.get(phone=phone)


class Rules(Base):
    def test_off_by_default_and_no_points_when_off(self):
        o = self.bill()
        self.pay_all(o)
        self.assertEqual(Customer.objects.filter(phone="0300111").count(), 0)

    def test_owner_sets_rules_and_cashier_cannot(self):
        self.rules(spend_per_point="50", point_value="0.5", min_redeem=200)
        s = self.a.get(LOY + "settings/").json()
        self.assertEqual((Decimal(s["spend_per_point"]), Decimal(s["point_value"]), s["min_redeem"]), (50, Decimal("0.5"), 200))
        cashier = self.staff_user("POS_OPERATOR", "loycash")
        self.assertEqual(cashier.patch(LOY + "settings/", {"enabled": False}, format="json").status_code, 403)
        self.assertEqual(self.a.patch(LOY + "settings/", {"spend_per_point": "0"}, format="json").status_code, 400)

    def test_rules_reach_the_app_for_offline_bills(self):
        self.rules(spend_per_point="200")
        me = self.a.get("/api/v1/auth/me/").json()["organization"]["loyalty"]
        self.assertTrue(me["enabled"])
        self.assertEqual(Decimal(me["spend_per_point"]), 200)
        self.assertEqual(self.b.get("/api/v1/auth/me/").json()["organization"]["loyalty"], {"enabled": False})

    def staff_user(self, role, username):
        from django.contrib.auth import get_user_model
        from tests.base import PASSWORD
        r = self.a.post("/api/v1/organizations/location-staff/", {"username": username, "email": f"{username}@x.com", "password": PASSWORD,
                        "first_name": "S", "last_name": "T", "location_id": self.loc_a.id, "role": role}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return self.as_user(get_user_model().objects.get(username=username))


class EarnAndRedeem(Base):
    def setUp(self):
        super().setUp()
        self.rules()

    def test_points_added_only_when_fully_paid(self):
        o = self.bill(qty=2)                                   # 1000 + tax
        self.assertEqual(self.customer().points_balance, 0)
        total = Decimal(str(self.a.get(f"/api/v1/orders/{o['id']}/").json()["total_amount"]))
        self.pay(self.a, o["id"], "CASH", Decimal("100"))      # part payment
        self.assertEqual(self.customer().points_balance, 0)
        self.pay(self.a, o["id"], "CASH", total - 100)
        self.assertEqual(self.customer().points_balance, int(total // 100))

    def test_points_not_given_twice(self):
        o = self.bill()
        self.pay_all(o)
        bal = self.customer().points_balance
        from apps.cash import services
        from apps.orders.models import Order
        services.sync_payment_status(Order.objects.get(pk=o["id"]))
        self.assertEqual(self.customer().points_balance, bal)

    def test_same_phone_is_the_same_customer(self):
        self.pay_all(self.bill(name="Ali"))
        self.pay_all(self.bill(name="Ali again"))
        self.assertEqual(Customer.objects.filter(phone="0300111").count(), 1)
        self.assertGreater(self.customer().points_balance, 10)

    def test_cannot_use_points_below_minimum_then_can_above_it(self):
        self.pay_all(self.bill(qty=1))                          # ~5 points
        o = self.bill(qty=1)
        r = self.a.post(f"/api/v1/orders/{o['id']}/redeem-points/", {"points": 3}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("100", r.json()["detail"])
        Customer.objects.filter(phone="0300111").update(points_balance=250)
        o2 = self.bill(qty=2)
        r = self.a.post(f"/api/v1/orders/{o2['id']}/redeem-points/", {"points": 120}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Decimal(r.json()["discount"]), Decimal("120"))
        self.assertEqual(self.customer().points_balance, 130)
        self.assertEqual(r.json()["loyalty"]["redeemed"], 120)

    def test_redeem_guards(self):
        Customer.objects.filter(phone="0300111").delete()
        o0 = self.bill(qty=1)
        Customer.objects.filter(phone="0300111").update(points_balance=2000)
        o = self.bill(qty=1)
        post = lambda pts, oid=o["id"]: self.a.post(f"/api/v1/orders/{oid}/redeem-points/", {"points": pts}, format="json")
        self.assertEqual(post(5000).status_code, 400)           # more than balance
        self.assertEqual(post(0).status_code, 400)
        self.assertEqual(post("abc").status_code, 400)
        self.assertEqual(post(1900).status_code, 400)           # worth more than the bill itself
        self.assertEqual(post(150).status_code, 200)
        self.assertEqual(post(100).status_code, 400)            # already used on this bill
        paid = self.bill(qty=1)
        self.pay(self.a, paid["id"], "CASH", Decimal("10"))
        self.assertEqual(self.a.post(f"/api/v1/orders/{paid['id']}/redeem-points/", {"points": 100}, format="json").status_code, 400)  # payment already started

    def test_discount_bill_earns_on_what_customer_pays(self):
        Customer.objects.filter(phone="0300111").delete()
        self.bill(qty=1)
        Customer.objects.filter(phone="0300111").update(points_balance=200)
        o = self.bill(qty=2)
        self.a.post(f"/api/v1/orders/{o['id']}/redeem-points/", {"points": 200}, format="json")
        total = self.pay_all(o)
        self.assertEqual(self.customer().points_balance, int(total // 100))   # 0 left + earned on the reduced bill

    def test_refund_takes_back_earned_and_returns_used(self):
        Customer.objects.filter(phone="0300111").delete()
        self.bill(qty=1)
        Customer.objects.filter(phone="0300111").update(points_balance=150)
        o = self.bill(qty=2)
        self.a.post(f"/api/v1/orders/{o['id']}/redeem-points/", {"points": 100}, format="json")
        total = self.pay_all(o)
        earned = int(total // 100)
        self.assertEqual(self.customer().points_balance, 50 + earned)
        r = self.a.post(f"/api/v1/cash/orders/{o['id']}/refund/", {"method": "CASH", "amount": str(total), "reason": "wrong order"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.customer().points_balance, 150)                 # earned gone, used returned

    def test_other_restaurants_customer_is_separate(self):
        self.pay_all(self.bill())
        self.assertEqual(self.b.get(LOY + f"lookup/?location={self.loc_b.id}&phone=0300111").json(), {"found": False})
        self.assertEqual(self.b.get(LOY + f"lookup/?location={self.loc_a.id}&phone=0300111").status_code, 400)

    def test_lookup_returns_balance(self):
        self.pay_all(self.bill(email="ali@example.com"))
        j = self.a.get(LOY + f"lookup/?location={self.loc_a.id}&phone=0300111").json()
        self.assertTrue(j["found"])
        self.assertEqual(j["email"], "ali@example.com")
        self.assertFalse(j["can_redeem"])


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class Emails(Base):
    def setUp(self):
        super().setUp()
        self.rules()

    def test_customer_gets_points_email_when_bill_paid(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.pay_all(self.bill(email="ali@example.com"))
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.to, ["ali@example.com"])
        self.assertIn("You earned", m.subject)
        self.assertIn("Earn 1 point for every PKR 100", m.body)
        self.assertIn("1 point = PKR 1 off", m.body)

    def test_no_email_without_address_or_when_switched_off(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.pay_all(self.bill())
        self.assertEqual(len(mail.outbox), 0)
        self.rules(email_customers=False)
        with self.captureOnCommitCallbacks(execute=True):
            self.pay_all(self.bill(email="ali@example.com", phone="0300222"))
        self.assertEqual(len(mail.outbox), 0)

    def test_email_failure_never_blocks_the_sale(self):
        with mock.patch("apps.loyalty.services.send_mail", side_effect=RuntimeError("smtp down")):
            with self.captureOnCommitCallbacks(execute=True):
                self.pay_all(self.bill(email="ali@example.com"))
        self.assertGreater(self.customer().points_balance, 0)

    def test_reminders_respect_the_gap_and_the_switch(self):
        Customer.objects.all().delete()
        c = self.bill(email="ali@example.com")
        Customer.objects.filter(phone="0300111").update(points_balance=40)
        r = self.a.post(LOY + "reminders/send/", {}, format="json").json()
        self.assertEqual(r["sent"], 1)
        self.assertIn("Collect 60 more points", mail.outbox[-1].body)
        self.assertEqual(self.a.post(LOY + "reminders/send/", {}, format="json").json()["sent"], 0)   # emailed just now
        Customer.objects.filter(phone="0300111").update(last_reminder_at=timezone.now() - timedelta(days=4), points_balance=250)
        self.assertEqual(self.a.post(LOY + "reminders/send/", {}, format="json").json()["sent"], 1)
        self.assertIn("ready to use", mail.outbox[-1].body)
        self.rules(reminders=False)
        Customer.objects.filter(phone="0300111").update(last_reminder_at=None)
        self.assertEqual(self.a.post(LOY + "reminders/send/", {}, format="json").json()["sent"], 0)

    def test_only_owner_can_send_reminders(self):
        cashier = Rules.staff_user(self, "POS_OPERATOR", "loyc2")
        self.assertEqual(cashier.post(LOY + "reminders/send/", {}, format="json").status_code, 403)
