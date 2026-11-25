"""One restaurant must never see or touch another restaurant's data."""
from apps.customers.models import Customer
from apps.orders.models import Order, OrderItem
from tests.base import TenantTestCase


class CustomerIsolation(TenantTestCase):
    def test_search_with_foreign_location_returns_nothing(self):
        self.a.post("/api/v1/customers/", {"location": self.loc_a.id, "first_name": "Ali",
                                           "phone": "03001234567"}, format="json")
        r = self.b.get(f"/api/v1/customers/?search=Ali&location={self.loc_a.id}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["results"], [])

    def test_patch_cannot_move_customer_to_other_org(self):
        c = self.a.post("/api/v1/customers/", {"location": self.loc_a.id, "first_name": "Ali",
                                               "phone": "03001234567"}, format="json").json()
        r = self.a.patch(f"/api/v1/customers/{c['id']}/", {"location": self.loc_b.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Customer.objects.get(pk=c["id"]).location_id, self.loc_a.id)

    def test_same_phone_allowed_in_two_restaurants(self):
        body = {"first_name": "Ali", "phone": "03001234567"}
        self.assertEqual(self.a.post("/api/v1/customers/", {**body, "location": self.loc_a.id}, format="json").status_code, 201)
        self.assertEqual(self.b.post("/api/v1/customers/", {**body, "location": self.loc_b.id}, format="json").status_code, 201)

    def test_bad_location_param_is_400_not_500(self):
        self.assertEqual(self.a.get("/api/v1/customers/?location=abc").status_code, 400)


class OrderIsolation(TenantTestCase):
    def test_search_and_date_with_foreign_location_return_nothing(self):
        Order.objects.create(location=self.loc_b, order_type="TAKEAWAY", order_number="B-1",
                             customer_name="Bob Secret", customer_phone="03339998888")
        for qs in (f"search=Bob&location={self.loc_b.id}",
                   f"date=2020-01-01,2035-01-01&location={self.loc_b.id}",
                   f"location={self.loc_b.id}"):
            r = self.a.get(f"/api/v1/orders/?{qs}")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["results"], [], qs)

    def test_stats_for_foreign_location_is_404(self):
        self.assertEqual(self.a.get(f"/api/v1/orders/stats/?location={self.loc_b.id}").status_code, 404)

    def test_patch_order_cannot_move_to_other_org(self):
        order = self.new_order(self.a, self.loc_a)
        r = self.a.patch(f"/api/v1/orders/{order['id']}/", {"location": self.loc_b.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Order.objects.get(pk=order["id"]).location_id, self.loc_a.id)

    def test_order_cannot_reference_foreign_customer_or_table(self):
        foreign = Customer.objects.create(location=self.loc_b, first_name="X", phone="03000000001")
        r = self.a.post("/api/v1/orders/", {"location": self.loc_a.id, "order_type": "TAKEAWAY",
                                            "customer": foreign.id}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_item_cannot_use_foreign_variant_or_move_orders(self):
        order = self.new_order(self.a, self.loc_a)
        self.assertEqual(self.add_item(self.a, order["id"], self.variant_b).status_code, 400)
        item = self.add_item(self.a, order["id"], self.variant_a).json()
        other_org_order = Order.objects.create(location=self.loc_b, order_type="TAKEAWAY", order_number="B-2")
        r = self.a.patch(f"/api/v1/orders/items/{item['id']}/", {"order": other_org_order.id}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(OrderItem.objects.get(pk=item["id"]).order_id, order["id"])


class CatalogIsolation(TenantTestCase):
    def test_product_cannot_use_foreign_category_or_tags(self):
        cat_b = self.b.post("/api/v1/catalog/categories/", {"name": "Secret", "slug": "secret"}, format="json").json()
        tag_b = self.b.post("/api/v1/catalog/dietary-tags/", {"name": "SecretTag", "slug": "st"}, format="json").json()
        r = self.a.post("/api/v1/catalog/products/", {"category": cat_b["id"], "name": "P", "slug": "p", "sku": "P"}, format="json")
        self.assertEqual(r.status_code, 400)
        cat_a = self.a.post("/api/v1/catalog/categories/", {"name": "Mine", "slug": "mine"}, format="json").json()
        r = self.a.post("/api/v1/catalog/products/", {"category": cat_a["id"], "name": "P", "slug": "p", "sku": "P",
                                                      "dietary_tags": [tag_b["id"]]}, format="json")
        self.assertEqual(r.status_code, 400)


class MembershipIsolation(TenantTestCase):
    def test_cannot_attach_user_of_another_restaurant(self):
        for target in (self.owner_b, self.platform):
            r = self.a.post("/api/v1/organizations/members/", {"user_id": target.id, "role": "OWNER"}, format="json")
            self.assertEqual(r.status_code, 400)
            self.assertNotIn(target.email, r.content.decode())

    def test_removed_member_can_be_readded(self):
        r = self.a.post("/api/v1/organizations/location-staff/", {
            "username": "cashier1", "email": "c1@x.com", "password": "Str0ng-Pass!word",
            "first_name": "C", "last_name": "One", "location_id": self.loc_a.id, "role": "POS_OPERATOR"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        from apps.organizations.models import OrganizationMembership
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.get(username="cashier1")
        m = OrganizationMembership.objects.get(user=user)
        self.assertEqual(self.a.delete(f"/api/v1/organizations/members/{m.id}/").status_code, 204)
        r = self.a.post("/api/v1/organizations/location-staff/", {
            "user_id": user.id, "location_id": self.loc_a.id, "role": "POS_OPERATOR"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
