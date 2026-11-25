from decimal import Decimal

from rest_framework import serializers

from apps.catalog.utils import get_user_organization_id
from apps.utils.serializers import OrganizationScopedMixin
from apps.organizations.models import Location
from apps.inventory import services
from apps.inventory.models import Ingredient, StockMovement, MovementType


class IngredientSerializer(serializers.ModelSerializer):
    base_unit_display = serializers.CharField(source="get_base_unit_display", read_only=True)

    class Meta:
        model = Ingredient
        fields = ["id", "name", "sku", "base_unit", "base_unit_display", "cost_per_unit",
                  "reorder_level", "is_prepared", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip()
        org = get_user_organization_id(self.context["request"])
        qs = Ingredient.objects.filter(organization_id=org, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An ingredient with this name already exists.")
        return value

    def validate_base_unit(self, value):
        # Changing the unit after stock/recipes exist would silently corrupt quantities
        if self.instance and value != self.instance.base_unit:
            raise serializers.ValidationError("Base unit cannot be changed once the ingredient is created.")
        return value

    def validate_cost_per_unit(self, value):
        if value < 0:
            raise serializers.ValidationError("Cost cannot be negative.")
        return value

    def validate_reorder_level(self, value):
        if value < 0:
            raise serializers.ValidationError("Reorder level cannot be negative.")
        return value


class StockMovementCreateSerializer(OrganizationScopedMixin, serializers.Serializer):
    """Purchase / wastage / opening stock / count adjustment."""
    org_scoped_fields = {"location": "organization_id", "ingredient": "organization_id"}
    location_scoped_fields = {"location": "id"}

    ALLOWED = [MovementType.OPENING, MovementType.PURCHASE, MovementType.WASTAGE, MovementType.ADJUSTMENT]

    location = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all())
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    movement_type = serializers.ChoiceField(choices=[(m.value, m.label) for m in ALLOWED])
    quantity = serializers.DecimalField(
        max_digits=14, decimal_places=3,
        help_text="OPENING/PURCHASE/WASTAGE: positive. ADJUSTMENT: signed (+ found, - lost).",
    )
    unit = serializers.CharField(required=False, allow_blank=True,
                                 help_text="g, kg, ml, l, pcs, dozen (default: the ingredient's base unit)")
    unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=4, required=False, allow_null=True,
        help_text="Price per ENTERED unit (e.g. per kg). Used for PURCHASE/OPENING.",
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, data):
        kind = data["movement_type"]
        ingredient = data["ingredient"]
        if not ingredient.is_active:
            raise serializers.ValidationError({"ingredient": "This ingredient is inactive."})
        if ingredient.is_prepared:
            raise serializers.ValidationError(
                {"ingredient": "Prepared items have no stock of their own - stock their raw ingredients."})
        qty = data["quantity"]
        if qty == 0:
            raise serializers.ValidationError({"quantity": "Quantity cannot be zero."})
        if kind != MovementType.ADJUSTMENT and qty < 0:
            raise serializers.ValidationError({"quantity": "Quantity must be positive."})
        try:
            factor = services.unit_factor(data.get("unit"), ingredient)
        except ValueError as exc:
            raise serializers.ValidationError({"unit": str(exc)})
        data["base_quantity"] = qty * factor
        cost = data.get("unit_cost")
        data["cost_per_base_unit"] = (cost / factor) if cost is not None else None
        if data["cost_per_base_unit"] is not None and data["cost_per_base_unit"] < 0:
            raise serializers.ValidationError({"unit_cost": "Cost cannot be negative."})
        return data

    def save(self, user):
        d = self.validated_data
        kind, location, ingredient = d["movement_type"], d["location"], d["ingredient"]
        note = d.get("note", "")
        if kind in (MovementType.PURCHASE, MovementType.OPENING):
            if kind == MovementType.PURCHASE:
                return services.purchase(location, ingredient, d["base_quantity"],
                                         d["cost_per_base_unit"], user=user, note=note)
            return services.record_movement(location, ingredient, d["base_quantity"], kind,
                                            user=user, note=note, unit_cost=d["cost_per_base_unit"])
        change = -d["base_quantity"] if kind == MovementType.WASTAGE else d["base_quantity"]
        return services.record_movement(location, ingredient, change, kind, user=user, note=note)


class StockMovementSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)
    base_unit = serializers.CharField(source="ingredient.base_unit", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    movement_type_display = serializers.CharField(source="get_movement_type_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)

    class Meta:
        model = StockMovement
        fields = ["id", "location", "location_name", "ingredient", "ingredient_name", "base_unit",
                  "movement_type", "movement_type_display", "quantity_change", "balance_after",
                  "unit_cost", "reference_type", "reference_id", "note", "created_by_name", "created_at"]
        read_only_fields = fields


class RecipeLineInputSerializer(serializers.Serializer):
    ingredient = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    unit = serializers.CharField(required=False, allow_blank=True)


class RecipeWriteSerializer(serializers.Serializer):
    output_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, required=False, default=Decimal("1"))
    notes = serializers.CharField(required=False, allow_blank=True)
    lines = RecipeLineInputSerializer(many=True)

    def validate_output_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Must be greater than zero.")
        return value

    def validate_lines(self, lines):
        if not lines:
            raise serializers.ValidationError("A recipe needs at least one ingredient.")
        org = self.context["organization_id"]
        ids = [l["ingredient"] for l in lines]
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Each ingredient can appear only once.")
        found = Ingredient.objects.filter(organization_id=org, id__in=ids, is_active=True).in_bulk()
        resolved = []
        for line in lines:
            ingredient = found.get(line["ingredient"])
            if ingredient is None:
                raise serializers.ValidationError(f"Ingredient {line['ingredient']} not found.")
            if line["quantity"] <= 0:
                raise serializers.ValidationError(f"Quantity for {ingredient.name} must be positive.")
            try:
                factor = services.unit_factor(line.get("unit"), ingredient)
            except ValueError as exc:
                raise serializers.ValidationError(str(exc))
            resolved.append({"ingredient": ingredient, "quantity": line["quantity"] * factor})
        return resolved
