from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import ProductVariant
from apps.catalog.utils import get_user_organization_id
from apps.organizations.models import Location
from apps.utils.helpers import location_scope, location_model_scope
from apps.utils.pagination import StandardResultsSetPagination
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly, CanManageInventory
from apps.inventory import services
from apps.inventory.models import Ingredient, IngredientStock, StockMovement, Recipe, RecipeLine
from apps.inventory.serializers import (
    IngredientSerializer, StockMovementCreateSerializer, StockMovementSerializer,
    RecipeWriteSerializer,
)

NO_ORG = Response({"error": "User has no organization assigned."}, status=status.HTTP_403_FORBIDDEN)


def _int_param(request, name):
    value = request.query_params.get(name)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Invalid {name}.")


# ───────────────────────── ingredients ─────────────────────────
class IngredientListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]

    def get(self, request):
        org = get_user_organization_id(request)
        if not org:
            return NO_ORG
        qs = Ingredient.objects.filter(organization_id=org)
        if request.query_params.get("active", "true").lower() == "true":
            qs = qs.filter(is_active=True)
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(sku__icontains=search))
        if request.query_params.get("prepared") in ("true", "false"):
            qs = qs.filter(is_prepared=request.query_params["prepared"] == "true")
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            IngredientSerializer(page, many=True, context={"request": request}).data)

    def post(self, request):
        org = get_user_organization_id(request)
        if not org:
            return NO_ORG
        serializer = IngredientSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(organization_id=org)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class IngredientDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]

    def _get(self, request, pk):
        return get_object_or_404(Ingredient, pk=pk, organization_id=get_user_organization_id(request))

    def get(self, request, pk):
        return Response(IngredientSerializer(self._get(request, pk), context={"request": request}).data)

    def patch(self, request, pk):
        ingredient = self._get(request, pk)
        serializer = IngredientSerializer(ingredient, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @transaction.atomic
    def delete(self, request, pk):
        ingredient = self._get(request, pk)
        if RecipeLine.objects.filter(ingredient=ingredient, recipe__is_deleted=False).exists():
            return Response({"error": "This ingredient is used in a recipe. Remove it from recipes first."},
                            status=status.HTTP_400_BAD_REQUEST)
        if IngredientStock.objects.filter(ingredient=ingredient).exclude(quantity=0).exists():
            return Response({"error": "This ingredient still has stock. Adjust stock to zero first."},
                            status=status.HTTP_400_BAD_REQUEST)
        ingredient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ───────────────────────── stock ─────────────────────────
def _stock_rows(request, org):
    """One row per active ingredient x accessible location (0 if never stocked)."""
    location_id = _int_param(request, "location")
    locations = Location.objects.filter(**location_model_scope(request, org))
    if location_id:
        locations = locations.filter(pk=location_id)
    # prepared items (patty, sauce...) hold no stock of their own; their raw ingredients do
    ingredients = list(Ingredient.objects.filter(organization_id=org, is_active=True, is_prepared=False))
    quantities = {
        (s.ingredient_id, s.location_id): s.quantity
        for s in IngredientStock.objects.filter(location__in=locations)
    }
    rows = []
    for loc in locations:
        for ing in ingredients:
            qty = quantities.get((ing.id, loc.id), Decimal("0"))
            rows.append({
                "location": loc.id, "location_name": loc.name,
                "ingredient": ing.id, "ingredient_name": ing.name,
                "base_unit": ing.base_unit, "quantity": qty,
                "reorder_level": ing.reorder_level, "cost_per_unit": ing.cost_per_unit,
                "stock_value": (qty * ing.cost_per_unit).quantize(Decimal("0.01")),
                "is_low": ing.reorder_level > 0 and qty <= ing.reorder_level,
            })
    return rows


class StockListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = get_user_organization_id(request)
        if not org:
            return NO_ORG
        try:
            rows = _stock_rows(request, org)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if request.query_params.get("low") == "true":
            rows = [r for r in rows if r["is_low"]]
        return Response({"count": len(rows), "results": rows})


class StockMovementListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanManageInventory]

    def get(self, request):
        org = get_user_organization_id(request)
        if not org:
            return NO_ORG
        qs = StockMovement.objects.filter(**location_scope(request, org)).select_related(
            "ingredient", "location", "created_by")
        try:
            for param, field in (("location", "location_id"), ("ingredient", "ingredient_id")):
                value = _int_param(request, param)
                if value:
                    qs = qs.filter(**{field: value})
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if request.query_params.get("type"):
            qs = qs.filter(movement_type=request.query_params["type"])
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(StockMovementSerializer(page, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = StockMovementCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        movement = serializer.save(user=request.user)
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


# ───────────────────────── recipes ─────────────────────────
def _recipe_payload(recipe, price=None):
    lines = [{
        "ingredient": l.ingredient_id, "ingredient_name": l.ingredient.name,
        "base_unit": l.ingredient.base_unit, "quantity": l.quantity,
        "is_prepared": l.ingredient.is_prepared,
        "line_cost": (l.quantity * l.ingredient.cost_per_unit).quantize(Decimal("0.01")),
    } for l in recipe.lines.select_related("ingredient")]
    cost = services.recipe_cost_per_output(recipe)
    data = {"id": recipe.id, "output_quantity": recipe.output_quantity, "notes": recipe.notes,
            "lines": lines, "cost": cost.quantize(Decimal("0.01"))}
    if price is not None:
        data["price"] = price
        data["profit"] = (price - cost).quantize(Decimal("0.01"))
        data["margin_percent"] = (
            ((price - cost) / price * 100).quantize(Decimal("0.1")) if price else None)
    return data


class _RecipeBase(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]

    def target(self, request, pk, org):
        raise NotImplementedError

    def owner_field(self):
        raise NotImplementedError

    def get(self, request, pk):
        org = get_user_organization_id(request)
        if not org:
            return NO_ORG
        obj = self.target(request, pk, org)
        recipe = services._recipe_of(obj)
        if recipe is None or recipe.is_deleted:
            return Response({"error": "No recipe yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_recipe_payload(recipe, self.price_of(obj)))

    @transaction.atomic
    def put(self, request, pk):
        org = get_user_organization_id(request)
        if not org:
            return NO_ORG
        obj = self.target(request, pk, org)
        serializer = RecipeWriteSerializer(data=request.data, context={"organization_id": org})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        self.check_lines(obj, data["lines"])

        recipe = Recipe.all_objects.filter(**{self.owner_field(): obj}).first()
        if recipe is None:
            recipe = Recipe.objects.create(**{self.owner_field(): obj}, output_quantity=data["output_quantity"])
        else:
            recipe.is_deleted = False
            recipe.output_quantity = data["output_quantity"]
        recipe.notes = data.get("notes", "")
        recipe.save()
        recipe.lines.all().delete()
        RecipeLine.objects.bulk_create(
            [RecipeLine(recipe=recipe, ingredient=l["ingredient"], quantity=l["quantity"]) for l in data["lines"]])
        try:
            services.explode_recipe(recipe, Decimal("1"))  # catches loops/too-deep nesting
        except ValueError as exc:
            transaction.set_rollback(True)
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_recipe_payload(recipe, self.price_of(obj)))

    @transaction.atomic
    def delete(self, request, pk):
        org = get_user_organization_id(request)
        if not org:
            return NO_ORG
        recipe = services._recipe_of(self.target(request, pk, org))
        if recipe is None:
            return Response({"error": "No recipe yet."}, status=status.HTTP_404_NOT_FOUND)
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def price_of(self, obj):
        return None

    def check_lines(self, obj, lines):
        pass


class VariantRecipeView(_RecipeBase):
    """Recipe of one menu item variant (what one serving uses)."""
    def target(self, request, pk, org):
        return get_object_or_404(ProductVariant, pk=pk, product__organization_id=org)

    def owner_field(self):
        return "product_variant"

    def price_of(self, obj):
        return obj.base_price


class PreparedIngredientRecipeView(_RecipeBase):
    """Recipe of an in-house preparation (e.g. patty, sauce, marinated chicken)."""
    def target(self, request, pk, org):
        return get_object_or_404(Ingredient, pk=pk, organization_id=org, is_prepared=True)

    def owner_field(self):
        return "ingredient"

    def check_lines(self, obj, lines):
        from rest_framework.exceptions import ValidationError
        if services.would_create_cycle(obj, [l["ingredient"].id for l in lines]):
            raise ValidationError({"lines": "A preparation cannot (directly or indirectly) use itself."})
