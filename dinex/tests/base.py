from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.organizations.models import Organization, Location
from apps.catalog.models import ProductCategory, Product, ProductVariant

User = get_user_model()
PASSWORD = "Str0ng-Pass!word"


class TenantTestCase(APITestCase):
    """Two independent restaurants (A and B) with one location and one owner each."""

    @classmethod
    def setUpTestData(cls):
        cls.platform = User.objects.create_superuser("root", "root@x.com", PASSWORD)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(cls.platform)}")
        for key in ("A", "B"):
            r = client.post("/api/v1/onboarding/restaurant/", {
                "organization": {"name": f"Org {key}"},
                "owner": {"username": f"owner{key}", "email": f"o{key}@x.com",
                          "password": PASSWORD, "first_name": "Own", "last_name": key},
                "location": {"name": f"Loc {key}", "address": "Some address 123"},
            }, format="json")
            assert r.status_code == 201, r.content
        cls.org_a = Organization.objects.get(name="Org A")
        cls.org_b = Organization.objects.get(name="Org B")
        cls.loc_a = Location.objects.get(organization=cls.org_a)
        cls.loc_b = Location.objects.get(organization=cls.org_b)
        cls.owner_a = User.objects.get(username="ownerA")
        cls.owner_b = User.objects.get(username="ownerB")
        cls.variant_a = cls.make_variant(cls.org_a, "Burger", 500)
        cls.variant_b = cls.make_variant(cls.org_b, "Burger", 500)

    @staticmethod
    def make_variant(org, name, price):
        cat = ProductCategory.objects.create(organization=org, name="Main", slug="main")
        product = Product.objects.create(organization=org, category=cat, name=name,
                                         slug=name.lower(), sku=name.upper())
        return ProductVariant.objects.create(product=product, name="Regular", base_price=price)

    def as_user(self, user):
        """A client that logs in with a real JWT, so the whole authentication path (incl. the
        subscription gate) is exercised, not bypassed."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
        return client

    @property
    def a(self):
        return self.as_user(self.owner_a)

    @property
    def b(self):
        return self.as_user(self.owner_b)

    def new_order(self, client, location, **extra):
        r = client.post("/api/v1/orders/", {"location": location.id,
                                            "order_type": "TAKEAWAY", **extra}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def add_item(self, client, order_id, variant, quantity=1):
        return client.post("/api/v1/orders/items/", {
            "order": order_id, "product_variant": variant.id, "quantity": quantity}, format="json")

    # ---- cash helpers ----
    def open_shift(self, client, location, cash="1000"):
        r = client.post("/api/v1/cash/shifts/open/", {"location": location.id, "opening_cash": cash}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def pay(self, client, order_id, method="CASH", amount=None, **extra):
        body = {"method": method, **({"amount": str(amount)} if amount is not None else {}), **extra}
        return client.post(f"/api/v1/cash/orders/{order_id}/payments/", body, format="json")
