"""Upload / remove the picture of a dish, a deal or a category (multipart, one file called `image`)."""
from django.shortcuts import get_object_or_404
from PIL import Image, UnidentifiedImageError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Deal, Product, ProductCategory
from apps.catalog.utils import get_user_organization_id
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly

MAX_BYTES = 3 * 1024 * 1024
MAX_PIXELS = 25_000_000
ALLOWED = {"JPEG", "PNG", "WEBP"}
MODELS = {"product": Product, "deal": Deal, "category": ProductCategory}


def check_image(upload):
    if upload is None:
        raise ValidationError({"image": "Choose a picture."})
    if upload.size > MAX_BYTES:
        raise ValidationError({"image": "The picture is too big (max 3 MB)."})
    try:
        img = Image.open(upload)
        fmt, pixels = img.format, img.width * img.height
        img.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise ValidationError({"image": "This file is not a valid picture."})
    if fmt not in ALLOWED:
        raise ValidationError({"image": "Use a JPG, PNG or WebP picture."})
    if pixels > MAX_PIXELS:
        raise ValidationError({"image": "The picture is too large (max 25 megapixels)."})
    upload.seek(0)


class CatalogImageView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def _target(self, request, kind, pk):
        model = MODELS.get(kind)
        org_id = get_user_organization_id(request)
        if model is None or not org_id:
            return None
        return get_object_or_404(model, pk=pk, organization_id=org_id)

    def post(self, request, kind, pk):
        obj = self._target(request, kind, pk)
        if obj is None:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        upload = request.FILES.get("image")
        check_image(upload)
        if obj.image:
            obj.image.delete(save=False)
        obj.image = upload
        obj.save(update_fields=["image", "updated_at"])
        return Response({"image": request.build_absolute_uri(obj.image.url)}, status=status.HTTP_200_OK)

    def delete(self, request, kind, pk):
        obj = self._target(request, kind, pk)
        if obj is None:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if obj.image:
            obj.image.delete(save=False)
            obj.image = None
            obj.save(update_fields=["image", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)
