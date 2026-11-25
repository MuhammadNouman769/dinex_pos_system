"""Pictures for dishes, deals and categories."""
import io
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.catalog.models import Deal, DealItem, Product
from tests.base import TenantTestCase


def picture(fmt="PNG", size=(40, 30), name="x.png", ctype="image/png"):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 60, 30)).save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=ctype)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CatalogImages(TenantTestCase):
    def url(self, kind, pk):
        return f"/api/v1/catalog/images/{kind}/{pk}/"

    def make_deal(self):
        now = timezone.now()
        d = Deal.objects.create(organization=self.org_a, name="Combo", slug="combo", discount_type="FIXED", discount_value=50,
                                start_at=now - timedelta(days=1), end_at=now + timedelta(days=30))
        DealItem.objects.create(deal=d, product_variant=self.variant_a, quantity=1)
        return d

    def test_owner_uploads_a_dish_picture_and_it_is_in_the_menu(self):
        product = Product.objects.get(pk=self.variant_a.product_id)
        r = self.a.post(self.url("product", product.id), {"image": picture()}, format="multipart")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn("/media/catalog/", r.json()["image"])
        listing = self.a.get("/api/v1/catalog/products/").json()["results"]
        self.assertTrue(any(p["image"] for p in listing if p["id"] == product.id))

    def test_deal_picture_is_returned_with_the_deal(self):
        deal = self.make_deal()
        self.assertEqual(self.a.post(self.url("deal", deal.id), {"image": picture("WEBP", name="d.webp", ctype="image/webp")}, format="multipart").status_code, 200)
        rows = self.a.get("/api/v1/catalog/deals/?active_deals=true").json()["results"]
        self.assertTrue(rows[0]["image"])
        self.assertEqual(rows[0]["items"][0]["quantity"], 1)

    def test_replace_and_remove(self):
        product = Product.objects.get(pk=self.variant_a.product_id)
        self.a.post(self.url("product", product.id), {"image": picture()}, format="multipart")
        first = Product.objects.get(pk=product.id).image.name
        self.a.post(self.url("product", product.id), {"image": picture(size=(50, 50))}, format="multipart")
        self.assertNotEqual(Product.objects.get(pk=product.id).image.name, "")
        self.assertEqual(self.a.delete(self.url("product", product.id)).status_code, 204)
        self.assertFalse(Product.objects.get(pk=product.id).image)

    def test_rejects_bad_files(self):
        product = Product.objects.get(pk=self.variant_a.product_id)
        u = self.url("product", product.id)
        self.assertEqual(self.a.post(u, {"image": SimpleUploadedFile("a.txt", b"hello", content_type="text/plain")}, format="multipart").status_code, 400)
        self.assertEqual(self.a.post(u, {"image": SimpleUploadedFile("a.png", b"not really a png", content_type="image/png")}, format="multipart").status_code, 400)
        self.assertEqual(self.a.post(u, {"image": picture("GIF", name="a.gif", ctype="image/gif")}, format="multipart").status_code, 400)
        self.assertEqual(self.a.post(u, {}, format="multipart").status_code, 400)
        big = SimpleUploadedFile("big.png", b"\x89PNG" + b"0" * (3 * 1024 * 1024 + 10), content_type="image/png")
        self.assertEqual(self.a.post(u, {"image": big}, format="multipart").status_code, 400)

    def test_other_restaurant_cannot_touch_it_and_login_is_required(self):
        product = Product.objects.get(pk=self.variant_a.product_id)
        self.assertEqual(self.b.post(self.url("product", product.id), {"image": picture()}, format="multipart").status_code, 404)
        self.assertEqual(self.b.delete(self.url("product", product.id)).status_code, 404)
        self.assertEqual(APIClient().post(self.url("product", product.id), {"image": picture()}, format="multipart").status_code, 401)
        self.assertEqual(self.a.post(self.url("bogus", 1), {"image": picture()}, format="multipart").status_code, 404)
