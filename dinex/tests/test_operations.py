"""Reservations, suppliers/purchases, expenses and the end-of-day report."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.inventory.models import Ingredient, IngredientStock
from apps.orders.models import Table
from tests.base import PASSWORD, TenantTestCase

OPS = "/api/v1/operations/"


class Base(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.t1 = Table.objects.create(location=self.loc_a, table_number="T-1", capacity=4)
        self.t2 = Table.objects.create(location=self.loc_a, table_number="T-2", capacity=2)

    def staff(self, role, username):
        r = self.a.post("/api/v1/organizations/location-staff/", {
            "username": username, "email": f"{username}@x.com", "password": PASSWORD, "first_name": "S", "last_name": "T",
            "location_id": self.loc_a.id, "role": role}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return self.as_user(get_user_model().objects.get(username=username))

    def when(self, hours=3):
        return (timezone.now() + timedelta(hours=hours)).isoformat()

    def book(self, client=None, table=None, party=2, hours=3, **kw):
        return (client or self.a).post(OPS + "reservations/", {
            "location": self.loc_a.id, "table": (table or self.t1).id, "guest_name": "Ahmed", "phone": "0300",
            "party_size": party, "starts_at": self.when(hours), **kw}, format="json")


class Reservations(Base):
    def test_book_and_list(self):
        r = self.book()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["table_number"], "T-1")
        self.assertEqual(len(self.a.get(OPS + "reservations/?upcoming=1").json()["results"]), 1)

    def test_party_larger_than_table_is_rejected(self):
        self.assertEqual(self.book(table=self.t2, party=3).status_code, 400)

    def test_double_booking_same_table_overlap_rejected_but_back_to_back_ok(self):
        self.assertEqual(self.book(hours=3).status_code, 201)
        self.assertEqual(self.book(hours=4).status_code, 400)            # overlaps (90 min)
        self.assertEqual(self.book(hours=5).status_code, 201)            # starts after the first ends
        self.assertEqual(self.book(table=self.t2, hours=3).status_code, 201)

    def test_past_time_rejected(self):
        self.assertEqual(self.book(hours=-5).status_code, 400)

    def test_cancel_frees_the_slot(self):
        rid = self.book().json()["id"]
        self.assertEqual(self.a.post(f"{OPS}reservations/{rid}/cancel/").status_code, 200)
        self.assertEqual(self.book().status_code, 201)

    def test_seat_marks_table_occupied_and_complete_after(self):
        rid = self.book().json()["id"]
        self.assertEqual(self.a.post(f"{OPS}reservations/{rid}/seat/").status_code, 200)
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.status, "OCCUPIED")
        self.assertEqual(self.a.post(f"{OPS}reservations/{rid}/cancel/").status_code, 400)   # already seated
        self.assertEqual(self.a.post(f"{OPS}reservations/{rid}/complete/").status_code, 200)

    def test_cannot_seat_on_a_busy_table(self):
        rid = self.book().json()["id"]
        Table.objects.filter(pk=self.t1.pk).update(status="OCCUPIED")
        self.assertEqual(self.a.post(f"{OPS}reservations/{rid}/seat/").status_code, 400)

    def test_edit_time_rechecks_conflicts(self):
        a = self.book(hours=3).json()["id"]
        self.book(hours=6)
        r = self.a.patch(f"{OPS}reservations/{a}/", {"starts_at": self.when(6)}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_cashier_can_book_and_other_restaurant_cannot_see(self):
        cashier = self.staff("POS_OPERATOR", "resv1")
        self.assertEqual(self.book(client=cashier).status_code, 201)
        self.assertEqual(self.b.get(OPS + "reservations/").json()["results"], [])
        self.assertEqual(self.b.post(OPS + "reservations/", {"location": self.loc_a.id, "guest_name": "X", "party_size": 2,
                                                              "starts_at": self.when()}, format="json").status_code, 400)


class SuppliersAndPurchases(Base):
    def setUp(self):
        super().setUp()
        self.chicken = Ingredient.objects.create(organization=self.org_a, name="Chicken", base_unit="G")
        self.sup = self.a.post(OPS + "suppliers/", {"name": "Al-Madina Traders", "phone": "0311"}, format="json").json()

    def buy(self, client=None, **kw):
        body = {"location": self.loc_a.id, "supplier": self.sup["id"], "paid": "1000", "invoice_no": "INV-9",
                "lines": [{"ingredient": self.chicken.id, "quantity": "5", "unit": "kg", "unit_cost": "600"}], **kw}
        return (client or self.a).post(OPS + "purchases/", body, format="json")

    def test_purchase_stocks_in_and_tracks_dues(self):
        r = self.buy()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Decimal(r.json()["total"]), Decimal("3000.00"))
        self.assertEqual(Decimal(r.json()["due"]), Decimal("2000.00"))
        self.assertEqual(IngredientStock.objects.get(ingredient=self.chicken, location=self.loc_a).quantity, Decimal("5000"))
        self.chicken.refresh_from_db()
        self.assertEqual(self.chicken.cost_per_unit, Decimal("0.6000"))          # 600 per kg = 0.6 per g
        sup = self.a.get(OPS + "suppliers/").json()["results"][0]
        self.assertEqual(Decimal(sup["balance"]), Decimal("2000.00"))

    def test_pay_off_the_balance(self):
        pid = self.buy().json()["id"]
        self.assertEqual(self.a.post(f"{OPS}purchases/{pid}/pay/", {"amount": "2500"}, format="json").status_code, 400)
        r = self.a.post(f"{OPS}purchases/{pid}/pay/", {"amount": "2000"}, format="json")
        self.assertEqual(Decimal(r.json()["due"]), 0)

    def test_overpaying_the_bill_is_rejected(self):
        self.assertEqual(self.buy(paid="9999").status_code, 400)

    def test_foreign_ingredient_and_supplier_are_rejected(self):
        theirs = Ingredient.objects.create(organization=self.org_b, name="Beef", base_unit="G")
        r = self.buy(lines=[{"ingredient": theirs.id, "quantity": "1", "unit": "kg", "unit_cost": "1"}])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.b.post(OPS + "purchases/", {"location": self.loc_b.id, "supplier": self.sup["id"], "lines": [
            {"ingredient": Ingredient.objects.create(organization=self.org_b, name="Oil", base_unit="ML").id,
             "quantity": "1", "unit": "l", "unit_cost": "400"}]}, format="json").status_code, 404)

    def test_duplicate_supplier_name_and_cashier_blocked(self):
        self.assertEqual(self.a.post(OPS + "suppliers/", {"name": "al-madina traders"}, format="json").status_code, 400)
        cashier = self.staff("POS_OPERATOR", "buyer1")
        self.assertEqual(cashier.get(OPS + "suppliers/").status_code, 403)
        self.assertEqual(self.buy(client=cashier).status_code, 403)


class ExpensesAndDayReport(Base):
    def test_expense_from_drawer_needs_shift_and_hits_cash_count(self):
        body = {"location": self.loc_a.id, "category": "Gas", "amount": "400", "description": "cylinder", "source": "DRAWER"}
        self.assertEqual(self.a.post(OPS + "expenses/", body, format="json").status_code, 400)   # no shift
        sh = self.open_shift(self.a, self.loc_a, "1000")
        self.assertEqual(self.a.post(OPS + "expenses/", body, format="json").status_code, 201)
        s = self.a.get(f"/api/v1/cash/shifts/{sh['id']}/").json()
        self.assertEqual(Decimal(str(s["expected_cash"])), Decimal("600"))

    def test_expense_outside_till_does_not_touch_cash_and_can_be_deleted(self):
        sh = self.open_shift(self.a, self.loc_a, "1000")
        r = self.a.post(OPS + "expenses/", {"location": self.loc_a.id, "category": "Rent", "amount": "50000"}, format="json")
        self.assertEqual(r.status_code, 201)
        s = self.a.get(f"/api/v1/cash/shifts/{sh['id']}/").json()
        self.assertEqual(Decimal(str(s["expected_cash"])), Decimal("1000"))
        self.assertEqual(self.a.delete(f"{OPS}expenses/{r.json()['id']}/").status_code, 204)

    def test_drawer_expense_cannot_be_deleted(self):
        self.open_shift(self.a, self.loc_a)
        r = self.a.post(OPS + "expenses/", {"location": self.loc_a.id, "category": "Gas", "amount": "100", "source": "DRAWER",
                                            "description": "gas"}, format="json").json()
        self.assertEqual(self.a.delete(f"{OPS}expenses/{r['id']}/").status_code, 400)

    def test_future_and_zero_expenses_rejected(self):
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.assertEqual(self.a.post(OPS + "expenses/", {"location": self.loc_a.id, "category": "X", "amount": "5", "date": tomorrow}, format="json").status_code, 400)
        self.assertEqual(self.a.post(OPS + "expenses/", {"location": self.loc_a.id, "category": "X", "amount": "0"}, format="json").status_code, 400)

    def test_day_report_adds_everything_up(self):
        self.open_shift(self.a, self.loc_a, "1000")
        o = self.new_order(self.a, self.loc_a)
        self.add_item(self.a, o["id"], self.variant_a, 2)
        total = Decimal(str(self.a.get(f"/api/v1/orders/{o['id']}/").json()["total_amount"]))
        self.assertEqual(self.pay(self.a, o["id"], "CASH", total).status_code, 201)
        self.a.post(OPS + "expenses/", {"location": self.loc_a.id, "category": "Gas", "amount": "300", "source": "DRAWER", "description": "gas"}, format="json")
        self.a.post(OPS + "expenses/", {"location": self.loc_a.id, "category": "Rent", "amount": "200"}, format="json")
        ing = Ingredient.objects.create(organization=self.org_a, name="Oil", base_unit="ML")
        self.a.post(OPS + "purchases/", {"location": self.loc_a.id, "paid": "100", "lines": [
            {"ingredient": ing.id, "quantity": "1", "unit": "l", "unit_cost": "400"}]}, format="json")
        r = self.a.get(OPS + "reports/day/").json()
        self.assertEqual(Decimal(str(r["sales"]["net_sales"])), total)
        self.assertEqual(Decimal(str(r["expenses"]["total"])), Decimal("500"))
        self.assertEqual({c["category"] for c in r["expenses"]["by_category"]}, {"Gas", "Rent"})
        self.assertEqual(Decimal(str(r["purchases"]["total"])), Decimal("400"))
        self.assertEqual(Decimal(str(r["purchases"]["unpaid"])), Decimal("300"))
        self.assertEqual(Decimal(str(r["net_after_costs"])), total - 500 - 100)
        self.assertEqual(r["open_shifts"], 1)

    def test_day_report_counts_cash_desk_expenses_once(self):
        sh = self.open_shift(self.a, self.loc_a)
        self.a.post(f"/api/v1/cash/shifts/{sh['id']}/movements/", {"kind": "EXPENSE", "amount": "250", "reason": "vegetables"}, format="json")
        self.a.post(OPS + "expenses/", {"location": self.loc_a.id, "category": "Gas", "amount": "100", "source": "DRAWER", "description": "gas"}, format="json")
        r = self.a.get(OPS + "reports/day/").json()
        self.assertEqual(Decimal(str(r["expenses"]["total"])), Decimal("350"))

    def test_money_screens_are_owner_manager_only_and_tenant_safe(self):
        cashier = self.staff("POS_OPERATOR", "cashq")
        for url in ("expenses/", "reports/day/", "purchases/"):
            self.assertEqual(cashier.get(OPS + url).status_code, 403, url)
        self.a.post(OPS + "expenses/", {"location": self.loc_a.id, "category": "Gas", "amount": "5"}, format="json")
        self.assertEqual(self.b.get(OPS + "expenses/").json()["results"], [])
        self.assertEqual(self.b.post(OPS + "expenses/", {"location": self.loc_a.id, "category": "Gas", "amount": "5"}, format="json").status_code, 400)


class TableLayout(Base):
    def test_position_can_be_saved_and_reset_and_is_bounded(self):
        r = self.a.patch(f"/api/v1/orders/tables/{self.t1.id}/", {"pos_x": 120, "pos_y": 260}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()["pos_x"], r.json()["pos_y"]), (120, 260))
        self.assertEqual(self.a.patch(f"/api/v1/orders/tables/{self.t1.id}/", {"pos_x": 99999}, format="json").status_code, 400)
        r = self.a.patch(f"/api/v1/orders/tables/{self.t1.id}/", {"pos_x": None, "pos_y": None}, format="json")
        self.assertIsNone(r.json()["pos_x"])

    def test_other_restaurant_cannot_move_my_table(self):
        self.assertEqual(self.b.patch(f"/api/v1/orders/tables/{self.t1.id}/", {"pos_x": 5}, format="json").status_code, 404)


class ChangePassword(Base):
    URL = "/api/v1/auth/change-password/"

    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()  # login throttle is shared across the whole suite

    def test_requires_the_current_password_and_a_strong_new_one(self):
        c = self.a
        self.assertEqual(c.post(self.URL, {"current_password": "wrong", "new_password": "Brand-New-Pass-77"}, format="json").status_code, 400)
        self.assertEqual(c.post(self.URL, {"current_password": PASSWORD, "new_password": PASSWORD}, format="json").status_code, 400)
        self.assertEqual(c.post(self.URL, {"current_password": PASSWORD, "new_password": "12345678"}, format="json").status_code, 400)
        self.assertEqual(c.post(self.URL, {"current_password": PASSWORD, "new_password": "Brand-New-Pass-77"}, format="json").status_code, 200)

    def test_new_password_works_for_login_and_old_does_not(self):
        self.a.post(self.URL, {"current_password": PASSWORD, "new_password": "Brand-New-Pass-77"}, format="json")
        from rest_framework.test import APIClient
        who = self.org_a.memberships.filter(role="OWNER").first().user.username
        anon = APIClient()
        self.assertEqual(anon.post("/api/v1/auth/token/", {"username": who, "password": PASSWORD}, format="json").status_code, 401)
        self.assertEqual(anon.post("/api/v1/auth/token/", {"username": who, "password": "Brand-New-Pass-77"}, format="json").status_code, 200)

    def test_anonymous_is_rejected(self):
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().post(self.URL, {}, format="json").status_code, 401)
