"""Bill branding (logo, accounts, QR) and table shapes."""
import base64
import io
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from apps.orders.models import Table
from tests.base import TenantTestCase

BRAND = "/api/v1/organizations/me/branding/"


def colour_png(size=(900, 600), rgba=False):
    buf = io.BytesIO()
    im = Image.new("RGBA" if rgba else "RGB", size, (30, 140, 90, 0 if rgba else 255))
    im.paste((200, 20, 20, 255) if rgba else (200, 20, 20), (100, 100, 400, 400))
    im.save(buf, "PNG")
    return SimpleUploadedFile("logo.png", buf.getvalue(), content_type="image/png")


def decode(data_uri):
    return Image.open(io.BytesIO(base64.b64decode(data_uri.split(",", 1)[1])))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class Branding(TenantTestCase):
    def test_logo_is_stored_and_a_pure_black_and_white_copy_is_made(self):
        r = self.a.post(BRAND + "logo/", {"image": colour_png()}, format="multipart")
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertTrue(d["logo"].startswith("http") and "/media/org/logos/" in d["logo"])
        bw = decode(d["logo_bw"])
        self.assertEqual(bw.mode, "1")
        self.assertLessEqual(max(bw.size), 420)

    def test_transparent_logo_is_flattened_on_white_not_black(self):
        d = self.a.post(BRAND + "logo/", {"image": colour_png(rgba=True)}, format="multipart").json()
        bw = decode(d["logo_bw"]).convert("L")
        self.assertEqual(bw.getpixel((2, 2)), 255)          # a transparent corner prints white

    def test_qr_picture_becomes_crisp_black_and_white(self):
        d = self.a.post(BRAND + "qr/", {"image": colour_png((300, 300))}, format="multipart").json()
        self.assertEqual(decode(d["qr_bw"]).mode, "1")

    def test_accounts_footer_and_switches_are_saved_and_come_back_in_me(self):
        r = self.a.patch(BRAND, {"accounts": [{"label": "JazzCash", "title": "Org A", "number": "0300 1112223"}, {"label": "Meezan", "title": "Org A", "number": "PK36MEZN0000"}],
                                 "footer": "Thank you!", "qr_text": "https://pay.example/orga", "show_qr": False}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        me = self.a.get("/api/v1/auth/me/").json()["organization"]["branding"]
        self.assertEqual([a["label"] for a in me["accounts"]], ["JazzCash", "Meezan"])
        self.assertEqual((me["footer"], me["qr_text"], me["show_qr"], me["show_accounts"]), ("Thank you!", "https://pay.example/orga", False, True))

    def test_bad_accounts_are_rejected(self):
        for bad in ([{"label": "", "number": "1"}], [{"label": "X", "number": ""}], "nope", [{"label": "X", "number": "1"}] * 7):
            self.assertEqual(self.a.patch(BRAND, {"accounts": bad}, format="json").status_code, 400)

    def test_not_a_picture_is_rejected(self):
        bad = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")
        self.assertEqual(self.a.post(BRAND + "logo/", {"image": bad}, format="multipart").status_code, 400)

    def test_remove_logo(self):
        self.a.post(BRAND + "logo/", {"image": colour_png()}, format="multipart")
        self.assertEqual(self.a.delete(BRAND + "logo/").status_code, 204)
        d = self.a.get(BRAND).json()
        self.assertEqual((d["logo"], d["logo_bw"]), (None, ""))

    def test_each_restaurant_has_its_own_branding(self):
        self.a.patch(BRAND, {"footer": "A only"}, format="json")
        self.assertEqual(self.b.get(BRAND).json()["footer"], "")

    def test_a_user_without_a_restaurant_cannot_change_branding(self):
        from django.contrib.auth import get_user_model
        u = get_user_model().objects.create_user("stranger", "s@x.com", "Str0ng-Pass!word")
        self.assertIn(self.as_user(u).patch(BRAND, {"footer": "hack"}, format="json").status_code, (400, 403))
        self.assertEqual(self.a.get(BRAND).json()["footer"], "")


class TableShapes(TenantTestCase):
    def test_table_shape_defaults_to_square_and_can_be_chosen(self):
        r = self.a.post("/api/v1/orders/tables/", {"location": self.loc_a.id, "table_number": "T-1", "capacity": 4}, format="json")
        self.assertEqual((r.status_code, r.json()["shape"]), (201, "SQUARE"))
        r = self.a.post("/api/v1/orders/tables/", {"location": self.loc_a.id, "table_number": "T-2", "capacity": 6, "shape": "WALL"}, format="json")
        self.assertEqual((r.status_code, r.json()["shape"]), (201, "WALL"))

    def test_unknown_shape_is_rejected(self):
        r = self.a.post("/api/v1/orders/tables/", {"location": self.loc_a.id, "table_number": "T-3", "capacity": 4, "shape": "TRIANGLE"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_shape_and_seats_can_be_edited_and_table_reserved(self):
        t = Table.objects.create(location=self.loc_a, table_number="T-9", capacity=2)
        r = self.a.patch(f"/api/v1/orders/tables/{t.id}/", {"shape": "ROUND", "capacity": 8}, format="json")
        self.assertEqual((r.status_code, r.json()["shape"], r.json()["capacity"]), (200, "ROUND", 8))
        r = self.a.patch(f"/api/v1/orders/tables/{t.id}/", {"status": "RESERVED"}, format="json")
        self.assertEqual((r.status_code, r.json()["status"]), (200, "RESERVED"))
