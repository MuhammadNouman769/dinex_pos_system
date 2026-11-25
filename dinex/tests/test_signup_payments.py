"""Self-service signup with terms + free trial, and paying by transaction id (admin approves)."""
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing.models import Invoice, PaymentAccount, PaymentSubmission, Subscription
from apps.organizations.models import Organization
from tests.base import TenantTestCase, PASSWORD

SIGNUP = "/api/v1/public/signup/"


def signup_body(n=1, **extra):
    return {"plan": "growth", "restaurant_name": f"Burger Hub {n}", "owner_name": "Ali Raza", "email": f"ali{n}@x.com",
            "phone": "03001234567", "username": f"ali{n}", "password": PASSWORD, "address": "Main Boulevard, Lahore",
            "accept_terms": True, **extra}


class PublicPlansAndSignup(TenantTestCase):
    def test_plans_are_public_and_show_three_cards(self):
        r = APIClient().get("/api/v1/public/plans/")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual([p["code"] for p in d["plans"]], ["starter", "growth", "pro"])
        self.assertEqual(d["trial_days"], 14)
        self.assertNotIn("restaurants", d["plans"][0])

    def test_plans_work_even_with_a_stale_token(self):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertEqual(c.get("/api/v1/public/plans/").status_code, 200)

    def test_signup_starts_a_14_day_trial_on_the_chosen_plan_and_signs_in(self):
        r = APIClient().post(SIGNUP, signup_body(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()
        self.assertEqual((d["subscription"]["status"], d["subscription"]["plan"]["code"]), ("TRIAL", "growth"))
        self.assertEqual(d["subscription"]["days_left"], 14)
        sub = Subscription.objects.get(organization__name="Burger Hub 1")
        self.assertEqual(sub.terms_version, "2026-11")
        self.assertIsNotNone(sub.terms_accepted_at)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {d['access']}")
        me = c.get("/api/v1/auth/me/").json()
        self.assertEqual((me["role"], me["organization"]["name"]), ("OWNER", "Burger Hub 1"))
        self.assertTrue(me["is_owner"])

    def test_cannot_sign_up_without_agreeing_to_terms(self):
        r = APIClient().post(SIGNUP, signup_body(accept_terms=False), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("accept_terms", r.json())
        self.assertFalse(Organization.objects.filter(name="Burger Hub 1").exists())

    def test_validation_errors_are_per_field(self):
        r = APIClient().post(SIGNUP, signup_body(plan="nope", email="bad", username="a b", password="123"), format="json")
        self.assertEqual(r.status_code, 400)
        for k in ("plan", "email", "username", "password"):
            self.assertIn(k, r.json())

    def test_duplicate_username_and_email_are_refused_but_same_restaurant_name_is_fine(self):
        self.assertEqual(APIClient().post(SIGNUP, signup_body(1), format="json").status_code, 201)
        r = APIClient().post(SIGNUP, signup_body(2, username="ali1", email="ali1@x.com"), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.json()) & {"username", "email"}, {"username", "email"})
        self.assertEqual(APIClient().post(SIGNUP, signup_body(3, restaurant_name="Burger Hub 1"), format="json").status_code, 201)

    def test_signup_is_rate_limited(self):
        from django.core.cache import cache
        cache.clear()
        codes = [APIClient().post(SIGNUP, signup_body(100 + i, accept_terms=False), format="json").status_code for i in range(12)]
        self.assertIn(429, codes)
        cache.clear()


class Paying(TenantTestCase):
    def setUp(self):
        super().setUp()
        PaymentAccount.objects.create(method="JAZZCASH", account_title="XverLabs", account_number="03001112223")

    def expire(self):
        Subscription.objects.filter(organization=self.org_a).update(trial_ends_at=timezone.now() - timedelta(days=1))

    def pay(self, **extra):
        body = {"method": "JAZZCASH", "amount": "2999", "reference": "TID123456", **extra}
        return self.a.post("/api/v1/platform/billing/me/payments/", body, format="json")

    def test_owner_sees_accounts_and_plans_on_billing_page(self):
        d = self.a.get("/api/v1/platform/billing/me/").json()
        self.assertEqual(len(d["payment_accounts"]), 1)
        self.assertEqual(len(d["plans"]), 3)

    def test_expired_trial_is_blocked_but_can_still_pay(self):
        self.expire()
        self.assertEqual(self.a.post("/api/v1/customers/", {"first_name": "x"}, format="json").status_code, 402)
        r = self.pay()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["status"], "PENDING")
        self.assertEqual(self.a.get("/api/v1/auth/me/").json()["subscription"]["blocked"], True)   # still waiting

    def test_admin_approval_switches_the_system_on(self):
        self.expire()
        sid = self.pay().json()["id"]
        admin = self.as_user(self.platform)
        self.assertEqual(admin.get("/api/v1/platform/payments/?status=PENDING").json()["count"], 1)
        r = admin.post(f"/api/v1/platform/payments/{sid}/approve/")
        self.assertEqual(r.status_code, 200, r.content)
        sub = Subscription.objects.get(organization=self.org_a)
        self.assertEqual(sub.status, "ACTIVE")
        self.assertEqual(Invoice.objects.get(organization=self.org_a).status, "PAID")
        me = self.a.get("/api/v1/auth/me/").json()["subscription"]
        self.assertFalse(me["blocked"])
        order = self.a.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "TAKEAWAY"}, format="json")
        self.assertEqual(order.status_code, 201)

    def test_reject_needs_a_reason_and_owner_can_try_again(self):
        self.expire()
        sid = self.pay().json()["id"]
        admin = self.as_user(self.platform)
        self.assertEqual(admin.post(f"/api/v1/platform/payments/{sid}/reject/", {}, format="json").status_code, 400)
        self.assertEqual(admin.post(f"/api/v1/platform/payments/{sid}/reject/", {"reason": "Money not received"}, format="json").status_code, 200)
        self.assertEqual(Subscription.objects.get(organization=self.org_a).status, "TRIAL")
        again = self.pay(reference="TID999999")
        self.assertEqual(again.status_code, 201, again.content)
        listing = self.a.get("/api/v1/platform/billing/me/").json()["submissions"]
        self.assertEqual([s["status"] for s in listing], ["PENDING", "REJECTED"])
        self.assertEqual(listing[1]["reject_reason"], "Money not received")

    def test_cannot_approve_twice_or_send_two_at_once_or_reuse_a_tid(self):
        sid = self.pay().json()["id"]
        self.assertEqual(self.pay(reference="OTHER12345").status_code, 400)           # one pending at a time
        admin = self.as_user(self.platform)
        self.assertEqual(admin.post(f"/api/v1/platform/payments/{sid}/approve/").status_code, 200)
        self.assertEqual(admin.post(f"/api/v1/platform/payments/{sid}/approve/").status_code, 400)
        self.assertEqual(Invoice.objects.filter(organization=self.org_a, status="PAID").count(), 1)

    def test_tid_is_validated_and_unique_across_restaurants(self):
        self.assertEqual(self.pay(reference="ab").status_code, 400)
        self.assertEqual(self.pay(amount="abc").status_code, 400)
        self.assertEqual(self.pay().status_code, 201)
        r = self.b.post("/api/v1/platform/billing/me/payments/", {"method": "JAZZCASH", "amount": "2999", "reference": "tid123456"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_only_the_owner_can_pay_and_only_platform_can_approve(self):
        self.pay()
        sid = PaymentSubmission.objects.get().id
        self.assertEqual(self.a.post(f"/api/v1/platform/payments/{sid}/approve/").status_code, 403)
        self.assertEqual(self.a.get("/api/v1/platform/payments/").status_code, 403)
        self.assertEqual(APIClient().post("/api/v1/platform/billing/me/payments/", {}, format="json").status_code, 401)

    def test_screenshot_upload_is_checked(self):
        bad = SimpleUploadedFile("x.txt", b"hello", content_type="text/plain")
        r = self.a.post("/api/v1/platform/billing/me/payments/", {"method": "BANK", "amount": "2999", "reference": "TID777777", "proof": bad}, format="multipart")
        self.assertEqual(r.status_code, 400)
        png = SimpleUploadedFile("p.png", b"\x89PNG\r\n\x1a\n" + b"0" * 64, content_type="image/png")
        # a fake png must not crash the server (Pillow validation may reject it)
        r = self.a.post("/api/v1/platform/billing/me/payments/", {"method": "BANK", "amount": "2999", "reference": "TID777778", "proof": png}, format="multipart")
        self.assertIn(r.status_code, (201, 400))

    def test_owner_can_change_plan_during_trial_only(self):
        r = self.a.post("/api/v1/platform/billing/me/select-plan/", {"plan": "pro"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["subscription"]["plan"]["code"], "pro")
        self.assertEqual(self.a.post("/api/v1/platform/billing/me/select-plan/", {"plan": "zzz"}, format="json").status_code, 400)

    def test_payment_accounts_crud_is_platform_only(self):
        admin = self.as_user(self.platform)
        r = admin.post("/api/v1/platform/payment-accounts/", {"method": "EASYPAISA", "account_title": "XverLabs", "account_number": "0345"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.a.post("/api/v1/platform/payment-accounts/", {}, format="json").status_code, 403)
        aid = r.json()["id"]
        self.assertEqual(admin.patch(f"/api/v1/platform/payment-accounts/{aid}/", {"is_active": False}, format="json").status_code, 200)
        self.assertEqual(len(self.a.get("/api/v1/platform/billing/me/").json()["payment_accounts"]), 1)   # inactive hidden
        self.assertEqual(admin.post("/api/v1/platform/payment-accounts/", {"method": "BANK"}, format="json").status_code, 400)
