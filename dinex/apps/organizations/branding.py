"""Bill branding: logo (turned black-and-white for thermal printers), payment accounts and a payment QR."""
import base64
import io

from django.shortcuts import get_object_or_404
from PIL import Image, ImageOps
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.utils import get_user_organization_id
from apps.catalog.views.image_view import check_image
from apps.organizations.models import Organization
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly

MAX_ACCOUNTS = 6


def to_bw_datauri(upload, max_side, dither):
    """Flatten on white, grey-scale, boost contrast, shrink and reduce to pure black/white. Returns a PNG data URI."""
    img = Image.open(upload)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        bg.alpha_composite(rgba)
        img = bg
    img = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    bw = img.convert("1") if dither else img.point(lambda v: 255 if v > 140 else 0).convert("1")
    buf = io.BytesIO()
    bw.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def branding_dict(org, request=None):
    logo = None
    if org.logo:
        logo = request.build_absolute_uri(org.logo.url) if request else org.logo.url
    return {
        "logo": logo, "logo_bw": org.logo_bw, "qr_bw": org.payment_qr_bw, "qr_text": org.payment_qr_text,
        "accounts": org.payment_accounts or [], "footer": org.receipt_footer,
        "show_logo": org.bill_show_logo, "show_accounts": org.bill_show_accounts, "show_qr": org.bill_show_qr,
    }


def clean_accounts(value):
    if not isinstance(value, list):
        raise ValidationError({"accounts": "Send a list of accounts."})
    if len(value) > MAX_ACCOUNTS:
        raise ValidationError({"accounts": f"You can print at most {MAX_ACCOUNTS} accounts on a bill."})
    out = []
    for row in value:
        if not isinstance(row, dict):
            raise ValidationError({"accounts": "Each account needs a name and a number."})
        label, title, number = (str(row.get(k, "")).strip() for k in ("label", "title", "number"))
        if not label or not number:
            raise ValidationError({"accounts": "Each account needs a name (e.g. JazzCash) and an account number."})
        if len(label) > 30 or len(title) > 60 or len(number) > 60:
            raise ValidationError({"accounts": "An account entry is too long."})
        out.append({"label": label, "title": title, "number": number})
    return out


class OrgMixin:
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]

    def org(self, request):
        org_id = get_user_organization_id(request)
        if not org_id:
            raise ValidationError({"detail": "This account has no restaurant."})
        return get_object_or_404(Organization, pk=org_id)


class BrandingView(OrgMixin, APIView):
    parser_classes = [JSONParser]

    def get(self, request):
        return Response(branding_dict(self.org(request), request))

    def patch(self, request):
        org, d = self.org(request), request.data
        fields = []
        if "accounts" in d:
            org.payment_accounts = clean_accounts(d["accounts"]); fields.append("payment_accounts")
        for key, attr, limit in (("footer", "receipt_footer", 200), ("qr_text", "payment_qr_text", 255)):
            if key in d:
                v = str(d[key] or "").strip()
                if len(v) > limit:
                    raise ValidationError({key: f"Keep it under {limit} characters."})
                setattr(org, attr, v); fields.append(attr)
        for key, attr in (("show_logo", "bill_show_logo"), ("show_accounts", "bill_show_accounts"), ("show_qr", "bill_show_qr")):
            if key in d:
                if not isinstance(d[key], bool):
                    raise ValidationError({key: "Send true or false."})
                setattr(org, attr, d[key]); fields.append(attr)
        if fields:
            org.save(update_fields=fields + ["updated_at"])
        return Response(branding_dict(org, request))


class BrandingImageView(OrgMixin, APIView):
    """POST a picture (multipart `image`) as the bill logo or the payment QR; DELETE removes it."""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, kind):
        if kind not in ("logo", "qr"):
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        org = self.org(request)
        upload = request.FILES.get("image")
        check_image(upload)
        if kind == "logo":
            org.logo_bw = to_bw_datauri(upload, 420, dither=True)
            upload.seek(0)
            org.logo.save(upload.name, upload, save=False)
            org.save(update_fields=["logo", "logo_bw", "updated_at"])
        else:
            org.payment_qr_bw = to_bw_datauri(upload, 360, dither=False)
            org.save(update_fields=["payment_qr_bw", "updated_at"])
        return Response(branding_dict(org, request))

    def delete(self, request, kind):
        if kind not in ("logo", "qr"):
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        org = self.org(request)
        if kind == "logo":
            if org.logo:
                org.logo.delete(save=False)
            org.logo, org.logo_bw = None, ""
            org.save(update_fields=["logo", "logo_bw", "updated_at"])
        else:
            org.payment_qr_bw = ""
            org.save(update_fields=["payment_qr_bw", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)
