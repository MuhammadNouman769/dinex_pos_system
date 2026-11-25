from decimal import Decimal

from rest_framework import serializers

from apps.utils.serializers import OrganizationScopedMixin
from apps.orders.models import OrderItem
from apps.orders.models.choices import OrderStatus
from apps.orders.validators import (
    validate_order_item_quantity,
    validate_order_item_notes,
)

# Items can only be added/changed while the order is still open.
EDITABLE_ORDER_STATUSES = {OrderStatus.PENDING, OrderStatus.CONFIRMED}


class OrderItemSerializer(OrganizationScopedMixin, serializers.ModelSerializer):
    """
    Order item.

    The client only chooses WHAT (order, product_variant) and HOW MANY.
    Name and price are copied from the catalog by the server, so a client
    can never set its own price. `order` and `product_variant` cannot be
    changed after the item is created (delete the item and add a new one).
    """

    org_scoped_fields = {
        "order": "location__organization_id",
        "product_variant": "product__organization_id",
    }

    product_name_display = serializers.CharField(
        source="product_variant.product.name", read_only=True, default=""
    )
    variant_name_display = serializers.CharField(
        source="product_variant.name", read_only=True, default=""
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order",
            "product_variant",
            "product_name",
            "variant_name",
            "product_name_display",
            "variant_name_display",
            "quantity",
            "unit_price",
            "total_price",
            "tax",
            "discount",
            "notes",
            "modifiers",
            "deal",
            "deal_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "product_name", "variant_name", "unit_price", "total_price",
            "tax", "discount", "modifiers", "deal", "deal_name", "created_at", "updated_at",
        ]

    def validate_quantity(self, value):
        return validate_order_item_quantity(value)

    def validate_notes(self, value):
        return validate_order_item_notes(value)

    def validate(self, data):
        if self.instance is None:
            if "order" not in data or "product_variant" not in data:
                raise serializers.ValidationError(
                    "`order` and `product_variant` are required."
                )
        else:
            for field in ("order", "product_variant"):
                if field in data and data[field] != getattr(self.instance, field):
                    raise serializers.ValidationError(
                        {field: "Cannot be changed. Delete the item and add a new one."}
                    )

        order = data.get("order") or (self.instance.order if self.instance else None)
        if order is not None and order.status not in EDITABLE_ORDER_STATUSES:
            raise serializers.ValidationError(
                f"Items cannot be changed on a {order.status} order."
            )

        variant = data.get("product_variant")
        if variant is not None:
            if not variant.is_active or not variant.product.is_active:
                raise serializers.ValidationError(
                    {"product_variant": "This product is not available."}
                )
        return data

    def create(self, validated_data):
        variant = validated_data["product_variant"]
        validated_data["product_name"] = variant.product.name
        validated_data["variant_name"] = variant.name
        validated_data["unit_price"] = variant.base_price
        validated_data["total_price"] = (
            Decimal(str(validated_data.get("quantity", 1))) * variant.base_price
        )
        return super().create(validated_data)
