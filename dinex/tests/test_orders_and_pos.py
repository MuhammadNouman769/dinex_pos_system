"""Order integrity, tables, catalog behaviour and POS-operator permissions."""
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.organizations.models import Location
from apps.orders.models import Order, Table
from tests.base import TenantTestCase, PASSWORD


class OrderNumbers(TenantTestCase):
    def test_each_location_gets_its_own_sequence(self):
        loc_a2 = Location.objects.create(organization=self.org_a, name="Second", address="Somewhere 123")
        first = self.new_order(self.a, self.loc_a)
        other_loc = self.new_order(self.a, loc_a2)
        other_org = self.new_order(self.b, self.loc_b)
        second = self.new_order(self.a, self.loc_a)
        self.assertTrue(first["order_number"].endswith("-0001"))
        self.assertTrue(second["order_number"].endswith("-0002"))
        self.assertTrue(other_loc["order_number"].endswith("-0001"))
        self.assertTrue(other_org["order_number"].endswith("-0001"))

    def test_deleted_order_number_is_not_reused(self):
        first = self.new_order(self.a, self.loc_a)
        self.assertEqual(self.a.delete(f"/api/v1/orders/{first['id']}/").status_code, 204)
        second = self.new_order(self.a, self.loc_a)
        self.assertNotEqual(first["order_number"], second["order_number"])


class OrderIntegrity(TenantTestCase):
    def test_order_type_is_stored_correctly(self):
        o = self.new_order(self.a, self.loc_a)
        self.assertEqual(o["order_type"], "TAKEAWAY")
        self.assertEqual(Order.objects.get(pk=o["id"]).order_type, "TAKEAWAY")

    def test_client_cannot_set_status_or_payment(self):
        o = self.new_order(self.a, self.loc_a, status="COMPLETED", payment_status="PAID")
        self.assertEqual(o["status"], "PENDING")
        self.assertEqual(o["payment_status"], "PENDING")
        r = self.a.patch(f"/api/v1/orders/{o['id']}/", {"status": "COMPLETED"}, format="json")
        self.assertEqual(Order.objects.get(pk=o["id"]).status, "PENDING")

    def test_status_endpoint_follows_state_machine(self):
        o = self.new_order(self.a, self.loc_a)
        url = f"/api/v1/orders/{o['id']}/status/"
        self.assertEqual(self.a.post(url, {"status": "COMPLETED"}, format="json").status_code, 400)
        for st in ("CONFIRMED", "PREPARING", "READY", "COMPLETED"):
            self.assertEqual(self.a.post(url, {"status": st}, format="json").status_code, 200, st)

    def test_item_price_comes_from_catalog_not_client(self):
        o = self.new_order(self.a, self.loc_a)
        r = self.a.post("/api/v1/orders/items/", {"order": o["id"], "product_variant": self.variant_a.id,
                                                  "quantity": 2, "unit_price": "0.01"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Decimal(r.json()["unit_price"]), Decimal("500.00"))
        self.assertEqual(Decimal(r.json()["total_price"]), Decimal("1000.00"))
        order = Order.objects.get(pk=o["id"])
        self.assertEqual(order.subtotal, Decimal("1000.00"))
        self.assertEqual(order.total_amount, Decimal("1100.00"))  # + 10% tax

    def test_items_blocked_on_closed_order(self):
        o = self.new_order(self.a, self.loc_a)
        Order.objects.filter(pk=o["id"]).update(status="COMPLETED")
        self.assertEqual(self.add_item(self.a, o["id"], self.variant_a).status_code, 400)

    def test_discount_never_makes_total_negative_and_recalculates(self):
        o = self.new_order(self.a, self.loc_a, discount="5000.00")
        self.add_item(self.a, o["id"], self.variant_a)
        self.assertGreaterEqual(Order.objects.get(pk=o["id"]).total_amount, 0)
        o2 = self.new_order(self.a, self.loc_a)
        self.add_item(self.a, o2["id"], self.variant_a)
        r = self.a.patch(f"/api/v1/orders/{o2['id']}/", {"discount": "50.00"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Order.objects.get(pk=o2["id"]).total_amount, Decimal("500.00"))  # 500+50-50

    def test_delete_and_stats_work(self):
        o = self.new_order(self.a, self.loc_a)
        self.assertEqual(self.a.get("/api/v1/orders/stats/").status_code, 200)
        self.assertEqual(self.a.get(f"/api/v1/orders/stats/?location={self.loc_a.id}").status_code, 200)
        self.assertEqual(self.a.delete(f"/api/v1/orders/{o['id']}/").status_code, 204)

    def test_bad_date_param_is_400(self):
        self.assertEqual(self.a.get("/api/v1/orders/?date=oops,oops").status_code, 400)


class Tables(TenantTestCase):
    def make_table(self):
        r = self.a.post("/api/v1/orders/tables/", {"location": self.loc_a.id, "table_number": "T-1", "capacity": 4}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["id"]

    def test_available_occupy_free(self):
        tid = self.make_table()
        r = self.a.get(f"/api/v1/orders/tables/available/?location={self.loc_a.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.a.post(f"/api/v1/orders/tables/{tid}/occupy/", {}, format="json").status_code, 200)
        self.assertEqual(self.a.post(f"/api/v1/orders/tables/{tid}/free/", {}, format="json").status_code, 200)

    def test_put_with_unchanged_status_is_ok(self):
        tid = self.make_table()
        r = self.a.put(f"/api/v1/orders/tables/{tid}/", {"location": self.loc_a.id, "table_number": "T-1",
                                                         "capacity": 6, "status": "AVAILABLE"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_table_number_reusable_after_delete(self):
        tid = self.make_table()
        self.assertEqual(self.a.delete(f"/api/v1/orders/tables/{tid}/").status_code, 204)
        self.make_table()

    def test_dine_in_order_occupies_then_frees_table(self):
        tid = self.make_table()
        o = self.a.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "DINE_IN", "table": tid}, format="json").json()
        self.assertEqual(Table.objects.get(pk=tid).status, "OCCUPIED")
        for st in ("CONFIRMED", "PREPARING", "READY", "COMPLETED"):
            self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": st}, format="json")
        self.assertEqual(Table.objects.get(pk=tid).status, "AVAILABLE")

    def test_patch_dine_in_order_keeps_existing_table(self):
        tid = self.make_table()
        o = self.a.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "DINE_IN", "table": tid}, format="json").json()
        r = self.a.patch(f"/api/v1/orders/{o['id']}/", {"order_type": "DINE_IN", "notes": "x"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)


class DeliveryRules(TenantTestCase):
    def test_only_delivery_goes_out_and_must_do_so_before_completing(self):
        from apps.staff.models import Employee
        rider = Employee.objects.create(organization=self.org_a, location=self.loc_a, code="E-001", name="Rider One", role="RIDER")
        take = self.new_order(self.a, self.loc_a)
        deliv = self.a.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "DELIVERY",
                                                "customer_phone": "03001112222",
                                                "delivery_address": "House 1, Street 2, Lahore"}, format="json").json()
        for o in (take, deliv):
            for st in ("CONFIRMED", "PREPARING", "READY"):
                self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": st}, format="json")
        post = lambda o, st: self.a.post(f"/api/v1/orders/{o['id']}/status/", {"status": st}, format="json").status_code
        self.assertEqual(post(take, "OUT_FOR_DELIVERY"), 400)
        self.assertEqual(post(deliv, "COMPLETED"), 400)
        self.assertEqual(post(deliv, "OUT_FOR_DELIVERY"), 400)          # no rider yet
        Order.objects.filter(pk=deliv["id"]).update(rider=rider)
        self.assertEqual(post(deliv, "OUT_FOR_DELIVERY"), 200)
        self.assertEqual(post(deliv, "COMPLETED"), 200)


class PosOperatorPermissions(TenantTestCase):
    def setUp(self):
        r = self.a.post("/api/v1/organizations/location-staff/", {
            "username": "cashier1", "email": "c1@x.com", "password": PASSWORD,
            "first_name": "C", "last_name": "One", "location_id": self.loc_a.id, "role": "POS_OPERATOR"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.cashier = self.as_user(get_user_model().objects.get(username="cashier1"))
        self.loc_a2 = Location.objects.create(organization=self.org_a, name="Second", address="Somewhere 123")

    def test_operator_can_take_orders_and_customers_at_own_location(self):
        o = self.new_order(self.cashier, self.loc_a)
        self.assertEqual(self.add_item(self.cashier, o["id"], self.variant_a).status_code, 201)
        r = self.cashier.post("/api/v1/customers/", {"location": self.loc_a.id, "first_name": "Zed", "phone": "03005550000"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)

    def test_operator_cannot_touch_other_location_even_in_same_org(self):
        r = self.cashier.post("/api/v1/orders/", {"location": self.loc_a2.id, "order_type": "TAKEAWAY"}, format="json")
        self.assertEqual(r.status_code, 404)
        other = Order.objects.create(location=self.loc_a2, order_type="TAKEAWAY", order_number="X-1")
        self.assertEqual(self.cashier.patch(f"/api/v1/orders/{other.id}/", {"notes": "hi"}, format="json").status_code, 404)
        self.assertEqual(self.cashier.get(f"/api/v1/orders/{other.id}/").status_code, 404)

    def test_operator_cannot_manage_menu_staff_or_tables(self):
        self.assertEqual(self.cashier.post("/api/v1/catalog/categories/", {"name": "X", "slug": "x"}, format="json").status_code, 403)
        self.assertEqual(self.cashier.post("/api/v1/orders/tables/", {"location": self.loc_a.id, "table_number": "T-5"}, format="json").status_code, 403)
        self.assertEqual(self.cashier.post("/api/v1/organizations/members/", {"user_id": 1, "role": "OWNER"}, format="json").status_code, 403)

    def test_deactivated_org_is_locked_out(self):
        self.org_a.is_active = False
        self.org_a.save()
        fresh = self.as_user(get_user_model().objects.get(pk=self.owner_a.pk))
        self.assertEqual(fresh.get("/api/v1/orders/").status_code, 403)
        self.org_a.is_active = True
        self.org_a.save()


class CatalogBehaviour(TenantTestCase):
    def test_invalid_variant_is_rejected_not_swallowed(self):
        cat = self.a.post("/api/v1/catalog/categories/", {"name": "C", "slug": "c"}, format="json").json()
        r = self.a.post("/api/v1/catalog/products/", {"category": cat["id"], "name": "Pizza", "slug": "pizza", "sku": "PZ",
                                                      "variants": [{"name": "Large", "base_price": "-5"}]}, format="json")
        self.assertEqual(r.status_code, 400)
        from apps.catalog.models import Product
        self.assertFalse(Product.objects.filter(organization=self.org_a, slug="pizza").exists())  # rolled back

    def test_slugs_reusable_after_soft_delete(self):
        cat = self.a.post("/api/v1/catalog/categories/", {"name": "C", "slug": "c"}, format="json").json()
        body = {"category": cat["id"], "name": "Temp", "slug": "temp", "sku": "T1"}
        p = self.a.post("/api/v1/catalog/products/", body, format="json").json()
        self.assertEqual(self.a.delete(f"/api/v1/catalog/products/{p['id']}/").status_code, 204)
        again = self.a.post("/api/v1/catalog/products/", body, format="json")
        self.assertEqual(again.status_code, 201)
        self.assertEqual(self.a.delete(f"/api/v1/catalog/products/{again.json()['id']}/").status_code, 204)
        self.assertEqual(self.a.delete(f"/api/v1/catalog/categories/{cat['id']}/").status_code, 204)
        self.assertEqual(self.a.post("/api/v1/catalog/categories/", {"name": "C", "slug": "c"}, format="json").status_code, 201)

    def test_two_variants_of_one_product_at_same_location(self):
        from apps.catalog.models import ProductVariant
        product = self.variant_a.product
        large = ProductVariant.objects.create(product=product, name="Large", base_price=700)
        for v in (self.variant_a, large):
            r = self.a.post("/api/v1/catalog/product-locations/", {"product": product.id, "product_variant": v.id,
                                                                    "location": self.loc_a.id}, format="json")
            self.assertEqual(r.status_code, 201, r.content)


class Accounts(TenantTestCase):
    def test_createsuperuser_creates_platform_user(self):
        self.assertEqual(self.platform.role, "PLATFORM")

    def test_toggle_organization_with_string_false(self):
        r = self.as_user(self.platform).post(f"/api/v1/organizations/{self.org_a.id}/toggle/", {"is_active": "false"}, format="json")
        self.assertEqual(r.json()["is_active"], False)


class MeEndpoint(TenantTestCase):
    def test_owner_sees_org_all_locations_and_full_rights(self):
        d = self.a.get("/api/v1/auth/me/").json()
        self.assertEqual(d["organization"]["name"], "Org A")
        self.assertTrue(d["is_owner"] and d["can_manage_menu"] and d["can_manage_inventory"] and d["can_operate_pos"])
        self.assertEqual([l["id"] for l in d["locations"]], [self.loc_a.id])

    def test_cashier_sees_only_own_location_and_limited_rights(self):
        self.a.post("/api/v1/organizations/location-staff/", {
            "username": "cashier9", "email": "c9@x.com", "password": PASSWORD, "first_name": "C",
            "last_name": "N", "location_id": self.loc_a.id, "role": "POS_OPERATOR"}, format="json")
        cashier = self.as_user(get_user_model().objects.get(username="cashier9"))
        d = cashier.get("/api/v1/auth/me/").json()
        self.assertFalse(d["is_owner"] or d["can_manage_menu"] or d["can_manage_inventory"])
        self.assertTrue(d["can_operate_pos"])
        self.assertEqual(d["locations"][0]["role"], "POS_OPERATOR")

    def test_platform_user_has_no_organization(self):
        d = self.as_user(self.platform).get("/api/v1/auth/me/").json()
        self.assertIsNone(d["organization"])
        self.assertEqual(d["role"], "PLATFORM")

    def test_requires_login(self):
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().get("/api/v1/auth/me/").status_code, 401)
