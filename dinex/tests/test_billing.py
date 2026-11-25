"""Phase 4: DineX Admin - restaurants, plans, subscriptions, invoices, limits, daily billing."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.billing import services
from apps.billing.models import Invoice, Plan, Subscription
from apps.cash.models import AuditLog
from apps.organizations.models import Location
from tests.base import TenantTestCase, PASSWORD

User = get_user_model()


def restaurant_body(n=1, **extra):
    return {"organization": {"name": f"Test Cafe {n}"},
            "owner": {"username": f"cafe{n}", "email": f"cafe{n}@x.com", "password": PASSWORD, "first_name": "Cafe", "last_name": str(n)},
            "location": {"name": "Main", "address": "Some address 123, Lahore"}, **extra}


class BillingBase(TenantTestCase):
    @property
    def admin(self):
        return self.as_user(self.platform)

    def sub(self, org=None):
        return Subscription.objects.get(organization=org or self.org_a)

    def expire_trial(self, org=None):
        Subscription.objects.filter(organization=org or self.org_a).update(trial_ends_at=timezone.now() - timedelta(days=1))

    def act(self, org, action, **data):
        return self.admin.post(f"/api/v1/platform/restaurants/{org.id}/subscription/", {"action": action, **data}, format="json")


class PlatformAccess(BillingBase):
    def test_only_platform_staff_reach_the_admin_api(self):
        for path in ("overview/", "plans/", "restaurants/", "invoices/"):
            self.assertEqual(self.a.get(f"/api/v1/platform/{path}").status_code, 403, path)
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().get("/api/v1/platform/overview/").status_code, 401)
        self.assertEqual(self.admin.get("/api/v1/platform/overview/").status_code, 200)

    def test_new_restaurants_get_a_trial_via_onboarding_and_default_plans_exist(self):
        self.assertEqual(self.sub().status, "TRIAL")
        self.assertEqual(list(Plan.objects.values_list("code", flat=True)), ["starter", "growth", "pro"])
        d = self.a.get("/api/v1/auth/me/").json()["subscription"]
        self.assertEqual((d["status"], d["plan"]["code"], d["blocked"]), ("TRIAL", "starter", False))
        self.assertEqual(d["days_left"], 14)


class RestaurantCreation(BillingBase):
    def test_admin_creates_a_restaurant_that_can_log_in(self):
        r = self.admin.post("/api/v1/platform/restaurants/", restaurant_body(1, plan="growth", trial_days=30), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()
        self.assertEqual((d["subscription"]["plan"], d["subscription"]["status"]), ("growth", "TRIAL"))
        self.assertEqual(d["owner"]["username"], "cafe1")
        owner = self.as_user(User.objects.get(username="cafe1"))
        me = owner.get("/api/v1/auth/me/").json()
        self.assertEqual(me["organization"]["name"], "Test Cafe 1")
        self.assertEqual(me["locations"][0]["name"], "Main")
        self.assertEqual(me["subscription"]["days_left"], 30)
        self.assertTrue(AuditLog.objects.filter(action="platform_restaurant_created").exists())

    def test_activate_on_create_issues_first_invoice(self):
        r = self.admin.post("/api/v1/platform/restaurants/", restaurant_body(2, plan="starter", activate=True), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["subscription"]["status"], "ACTIVE")
        inv = Invoice.objects.get(organization_id=r.json()["id"])
        self.assertEqual((inv.amount, inv.status), (Decimal("2999.00"), "DUE"))
        self.assertTrue(inv.number.startswith(f"DX-{timezone.localdate().year}-"))

    def test_validation_and_duplicates(self):
        self.assertEqual(self.admin.post("/api/v1/platform/restaurants/", restaurant_body(3, plan="nope"), format="json").status_code, 400)
        body = restaurant_body(4); body["organization"]["name"] = "Org A"
        self.assertEqual(self.admin.post("/api/v1/platform/restaurants/", body, format="json").status_code, 400)
        self.assertEqual(self.a.post("/api/v1/platform/restaurants/", restaurant_body(5), format="json").status_code, 403)
        self.assertFalse(User.objects.filter(username="cafe3").exists())       # nothing half-created

    def test_list_search_filter_and_detail(self):
        self.act(self.org_b, "suspend", reason="Test")
        rows = self.admin.get("/api/v1/platform/restaurants/").json()
        self.assertEqual(rows["count"], 2)
        self.assertEqual([r["name"] for r in self.admin.get("/api/v1/platform/restaurants/?search=ownerA").json()["results"]], ["Org A"])
        self.assertEqual([r["name"] for r in self.admin.get("/api/v1/platform/restaurants/?status=SUSPENDED").json()["results"]], ["Org B"])
        d = self.admin.get(f"/api/v1/platform/restaurants/{self.org_a.id}/").json()
        self.assertEqual(d["users"][0]["username"], "ownerA")
        self.assertEqual(d["locations"][0]["name"], "Loc A")
        self.assertIn("usage", d)


class AccessControl(BillingBase):
    def post_order(self, client=None):
        return (client or self.a).post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "TAKEAWAY"}, format="json")

    def test_expired_trial_is_read_only(self):
        self.assertEqual(self.post_order().status_code, 201)
        self.expire_trial()
        r = self.post_order()
        self.assertEqual(r.status_code, 402)
        self.assertIn("trial", r.json()["detail"].lower())
        self.assertEqual(self.a.get("/api/v1/orders/").status_code, 200)               # can still look
        info = self.a.get("/api/v1/auth/me/").json()["subscription"]
        self.assertTrue(info["blocked"])
        self.assertIn("Open Billing", info["message"])

    def test_suspend_blocks_changes_and_reactivate_restores_them(self):
        self.assertEqual(self.act(self.org_a, "suspend", reason="").status_code, 400)       # reason needed
        self.assertEqual(self.act(self.org_a, "suspend", reason="Unpaid since August").status_code, 200)
        r = self.post_order()
        self.assertEqual(r.status_code, 402)
        self.assertIn("Unpaid since August", r.json()["detail"])
        self.assertEqual(self.a.get("/api/v1/inventory/stock/").status_code, 200)
        # the other restaurant is unaffected
        self.assertEqual(self.b.post("/api/v1/orders/", {"location": self.loc_b.id, "order_type": "TAKEAWAY"}, format="json").status_code, 201)
        self.assertEqual(self.act(self.org_a, "reactivate").status_code, 200)
        self.assertEqual(self.post_order().status_code, 201)

    def test_extend_trial_unblocks(self):
        self.expire_trial()
        self.assertEqual(self.post_order().status_code, 402)
        self.assertEqual(self.act(self.org_a, "extend_trial", days=10).status_code, 200)
        self.assertEqual(self.post_order().status_code, 201)
        self.assertEqual(self.act(self.org_a, "extend_trial", days=500).status_code, 400)

    def test_cancelled_is_blocked_and_platform_staff_never_are(self):
        self.act(self.org_a, "cancel")
        self.assertEqual(self.post_order().status_code, 402)
        self.assertEqual(self.act(self.org_a, "reactivate").status_code, 200)   # admin can still act on a blocked tenant

    def test_restaurant_without_subscription_is_not_blocked(self):
        Subscription.objects.filter(organization=self.org_a).delete()
        self.assertEqual(self.post_order().status_code, 201)
        self.assertIsNone(self.a.get("/api/v1/auth/me/").json()["subscription"])

    def test_disabling_an_account(self):
        r = self.admin.patch(f"/api/v1/platform/restaurants/{self.org_a.id}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.a.get("/api/v1/orders/").status_code, 403)


class PlanLimits(BillingBase):
    def test_branch_limit_and_upgrade(self):
        r = self.a.post("/api/v1/organizations/locations/", {"name": "Second", "address": "Another address 456"}, format="json")
        self.assertEqual(r.status_code, 402, r.content)
        self.assertIn("1 branches", r.json()["detail"])
        self.assertEqual(self.act(self.org_a, "change_plan", plan="growth").status_code, 200)
        r = self.a.post("/api/v1/organizations/locations/", {"name": "Second", "address": "Another address 456"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)

    def test_staff_limit(self):
        Plan.objects.filter(code="starter").update(max_users=2)
        def staff(n):
            return self.a.post("/api/v1/organizations/location-staff/", {
                "username": f"s{n}", "email": f"s{n}@x.com", "password": PASSWORD, "first_name": "S", "last_name": "T",
                "location_id": self.loc_a.id, "role": "POS_OPERATOR"}, format="json")
        self.assertEqual(staff(1).status_code, 201)          # owner + 1 = 2
        r = staff(2)
        self.assertEqual(r.status_code, 402, r.content)
        self.assertFalse(User.objects.filter(username="s2").exists())

    def test_cannot_downgrade_below_current_usage(self):
        self.act(self.org_a, "change_plan", plan="growth")
        for i in range(2):
            Location.objects.create(organization=self.org_a, name=f"X{i}", address="Somewhere 123456")
        Plan.objects.filter(code="starter").update(max_locations=1)
        self.assertEqual(self.act(self.org_a, "change_plan", plan="starter").status_code, 400)

    def test_plan_management(self):
        r = self.admin.post("/api/v1/platform/plans/", {"code": "mini", "name": "Mini", "price_monthly": "1999", "max_locations": 1, "max_users": 2, "features": ["POS"]}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.admin.post("/api/v1/platform/plans/", {"code": "mini", "name": "Dup", "price_monthly": "1"}, format="json").status_code, 400)
        self.assertEqual(self.admin.post("/api/v1/platform/plans/", {"name": "NoCode"}, format="json").status_code, 400)
        r = self.admin.patch(f"/api/v1/platform/plans/{r.json()['id']}/", {"price_monthly": "2499"}, format="json")
        self.assertEqual(Decimal(r.json()["price_monthly"]), Decimal("2499"))
        self.assertEqual(self.a.post("/api/v1/platform/plans/", {"code": "x", "name": "X", "price_monthly": "1"}, format="json").status_code, 403)


class Invoices(BillingBase):
    def test_activate_pay_and_period(self):
        self.assertEqual(self.act(self.org_a, "activate").status_code, 200)
        sub = self.sub()
        self.assertEqual(sub.status, "ACTIVE")
        inv = Invoice.objects.get(organization=self.org_a)
        r = self.admin.post(f"/api/v1/platform/invoices/{inv.id}/pay/", {"method": "JazzCash", "reference": "TX123"}, format="json")
        self.assertEqual((r.status_code, r.json()["status"]), (200, "PAID"))
        self.assertEqual(self.admin.post(f"/api/v1/platform/invoices/{inv.id}/pay/", {}, format="json").status_code, 400)
        self.assertEqual(self.act(self.org_a, "activate").status_code, 400)

    def test_set_price_override_changes_next_invoice_amount(self):
        self.act(self.org_a, "set_price", price="3500")
        self.act(self.org_a, "activate")
        self.assertEqual(Invoice.objects.get(organization=self.org_a).amount, Decimal("3500.00"))

    def test_manual_invoice_void_and_listing(self):
        self.act(self.org_a, "activate")
        r = self.admin.post(f"/api/v1/platform/restaurants/{self.org_a.id}/invoices/", {"amount": "1200", "note": "Setup fee"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        inv_id = r.json()["id"]
        self.assertEqual(self.admin.post(f"/api/v1/platform/invoices/{inv_id}/void/", {}, format="json").json()["status"], "VOID")
        self.assertEqual(self.admin.post(f"/api/v1/platform/invoices/{inv_id}/void/", {}, format="json").status_code, 400)
        self.assertEqual(self.admin.get("/api/v1/platform/invoices/?status=VOID").json()["count"], 1)
        self.assertEqual(self.admin.get("/api/v1/platform/invoices/?search=Org A").json()["count"], 2)
        self.assertEqual(self.admin.post(f"/api/v1/platform/restaurants/{self.org_a.id}/invoices/", {"amount": "-5"}, format="json").status_code, 400)

    def test_invoice_numbers_are_unique_and_sequential(self):
        self.act(self.org_a, "activate"); self.act(self.org_b, "activate")
        nums = sorted(Invoice.objects.values_list("number", flat=True))
        self.assertEqual(nums[1].rsplit("-", 1)[1], "0002")

    def test_restaurant_sees_only_its_own_billing_and_only_the_owner(self):
        self.act(self.org_a, "activate"); self.act(self.org_b, "activate")
        d = self.a.get("/api/v1/platform/billing/me/").json()
        self.assertEqual(len(d["invoices"]), 1)
        self.assertEqual(d["invoices"][0]["organization_name"], "Org A")
        cashier = self.a.post("/api/v1/organizations/location-staff/", {
            "username": "cb1", "email": "cb1@x.com", "password": PASSWORD, "first_name": "C", "last_name": "B",
            "location_id": self.loc_a.id, "role": "POS_OPERATOR"}, format="json")
        self.assertEqual(self.as_user(User.objects.get(username="cb1")).get("/api/v1/platform/billing/me/").status_code, 403)


class DailyBilling(BillingBase):
    def active(self):
        self.act(self.org_a, "activate")
        inv = Invoice.objects.get(organization=self.org_a)
        services.mark_paid(inv, self.platform, "cash")
        return self.sub()

    def test_next_invoice_is_issued_once_when_the_period_ends(self):
        sub = self.active()
        self.assertEqual(services.run_billing(today=sub.current_period_end - timedelta(days=1))["invoiced"], 0)
        self.assertEqual(services.run_billing(today=sub.current_period_end)["invoiced"], 1)
        self.assertEqual(services.run_billing(today=sub.current_period_end)["invoiced"], 0)     # idempotent
        self.assertEqual(Invoice.objects.filter(organization=self.org_a, status="DUE").count(), 1)

    def test_overdue_then_suspended_then_paid_reactivates(self):
        sub = self.active()
        end = sub.current_period_end
        services.run_billing(today=end)
        due = Invoice.objects.get(organization=self.org_a, status="DUE")
        r = services.run_billing(today=due.due_date + timedelta(days=1))
        self.assertEqual(r["past_due"], 1)
        self.assertEqual(self.sub().status, "PAST_DUE")
        self.assertEqual(self.a.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "TAKEAWAY"}, format="json").status_code, 201)   # warning only
        self.assertTrue(self.a.get("/api/v1/auth/me/").json()["subscription"]["message"])
        r = services.run_billing(today=due.due_date + timedelta(days=30))
        self.assertEqual(r["suspended"], 1)
        self.assertEqual(self.sub().status, "SUSPENDED")
        self.assertEqual(self.a.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "TAKEAWAY"}, format="json").status_code, 402)
        self.assertTrue(AuditLog.objects.filter(action="platform_auto_suspended").exists())
        services.mark_paid(due, self.platform, "bank")
        self.assertEqual(self.sub().status, "ACTIVE")
        self.assertEqual(self.a.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "TAKEAWAY"}, format="json").status_code, 201)

    def test_command_runs(self):
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("run_billing", stdout=out)
        self.assertIn("invoiced=", out.getvalue())


class SupportTools(BillingBase):
    def test_overview_numbers(self):
        self.act(self.org_a, "activate")                       # ACTIVE starter 2999
        self.act(self.org_b, "change_plan", plan="growth"); self.act(self.org_b, "activate")   # ACTIVE growth 4999
        d = self.admin.get("/api/v1/platform/overview/").json()
        self.assertEqual(d["restaurants"], 2)
        self.assertEqual(d["by_status"]["ACTIVE"], 2)
        self.assertEqual(Decimal(d["mrr"]), Decimal("7998.00"))
        Invoice.objects.update(due_date=timezone.localdate() - timedelta(days=3))
        d = self.admin.get("/api/v1/platform/overview/").json()
        self.assertEqual((d["overdue"]["count"], Decimal(d["overdue"]["amount"])), (2, Decimal("7998.00")))

    def test_trials_ending_soon_are_listed(self):
        Subscription.objects.filter(organization=self.org_a).update(trial_ends_at=timezone.now() + timedelta(days=3))
        d = self.admin.get("/api/v1/platform/overview/").json()
        self.assertEqual([t["name"] for t in d["trials_ending"]], ["Org A"])

    def test_reset_owner_password(self):
        url = f"/api/v1/platform/restaurants/{self.org_a.id}/reset-password/"
        self.assertEqual(self.admin.post(url, {"password": "123"}, format="json").status_code, 400)
        self.assertEqual(self.admin.post(url, {"password": "N3w-Strong-Pass!"}, format="json").status_code, 200)
        from rest_framework.test import APIClient
        c = APIClient()
        self.assertEqual(c.post("/api/v1/auth/token/", {"username": "ownerA", "password": "N3w-Strong-Pass!"}, format="json").status_code, 200)
        self.assertEqual(self.a.post(url, {"password": "N3w-Strong-Pass!"}, format="json").status_code, 403)
        self.assertTrue(AuditLog.objects.filter(action="platform_owner_password_reset").exists())

    def test_platform_actions_are_audited_and_shown_on_the_detail_page(self):
        self.act(self.org_a, "suspend", reason="Chargeback")
        d = self.admin.get(f"/api/v1/platform/restaurants/{self.org_a.id}/").json()
        self.assertEqual(d["activity"][0]["action"], "platform_suspended")
        self.assertEqual(d["subscription"]["suspended_reason"], "Chargeback")
