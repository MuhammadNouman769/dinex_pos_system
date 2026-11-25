from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class OrderItemCreateSchema(serializers.Serializer):
    """Schema for creating an order item"""
    order = serializers.IntegerField(help_text="Order ID")
    product_variant = serializers.IntegerField(help_text="Product variant ID")
    product_name = serializers.CharField(max_length=255, help_text="Product name (snapshot)")
    variant_name = serializers.CharField(max_length=255, help_text="Variant name (snapshot)")
    quantity = serializers.IntegerField(default=1, help_text="Quantity")
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Unit price")
    tax = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Tax")
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Discount")
    notes = serializers.CharField(required=False, allow_blank=True, help_text="Special instructions")


class OrderItemUpdateSchema(serializers.Serializer):
    """Schema for updating an order item"""
    product_variant = serializers.IntegerField(required=False, help_text="Product variant ID")
    product_name = serializers.CharField(required=False, max_length=255, help_text="Product name")
    variant_name = serializers.CharField(required=False, max_length=255, help_text="Variant name")
    quantity = serializers.IntegerField(required=False, help_text="Quantity")
    unit_price = serializers.DecimalField(required=False, max_digits=12, decimal_places=2, help_text="Unit price")
    tax = serializers.DecimalField(required=False, max_digits=12, decimal_places=2, help_text="Tax")
    discount = serializers.DecimalField(required=False, max_digits=12, decimal_places=2, help_text="Discount")
    notes = serializers.CharField(required=False, allow_blank=True, help_text="Special instructions")


class OrderItemResponseSchema(serializers.Serializer):
    """Schema for order item response"""
    id = serializers.IntegerField()
    order = serializers.IntegerField()
    product_variant = serializers.IntegerField()
    product_name = serializers.CharField()
    variant_name = serializers.CharField()
    product_name_display = serializers.CharField()
    variant_name_display = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2)
    notes = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


ORDER_ITEM_LIST_SCHEMA = extend_schema(
    tags=["Order Items"],
    summary="List Order Items",
    description="Get all order items with optional filtering.",
    parameters=[
        OpenApiParameter(
            name='order',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by order ID',
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=OrderItemResponseSchema(many=True),
            description="List of order items"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
)

ORDER_ITEM_CREATE_SCHEMA = extend_schema(
    tags=["Order Items"],
    summary="Create Order Item",
    description="Add an item to an order.",
    request=OrderItemCreateSchema,
    examples=[
        OpenApiExample(
            name="Add Burger to Order",
            summary="Add chicken burger",
            description="Add chicken burger to order.",
            value={
                "order": 1,
                "product_variant": 2,
                "product_name": "Chicken Burger",
                "variant_name": "Single Patty",
                "quantity": 2,
                "unit_price": "10.00",
                "notes": "Extra sauce"
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Add Pizza to Order",
            summary="Add pizza",
            description="Add cheese pizza to order.",
            value={
                "order": 1,
                "product_variant": 4,
                "product_name": "Cheese Pizza",
                "variant_name": "Large",
                "quantity": 1,
                "unit_price": "18.00"
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=OrderItemResponseSchema,
            description="Order item created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
)

ORDER_ITEM_RETRIEVE_SCHEMA = extend_schema(
    tags=["Order Items"],
    summary="Retrieve Order Item",
    description="Get order item details by ID.",
    responses={
        200: OpenApiResponse(
            response=OrderItemResponseSchema,
            description="Order item details"
        ),
        404: OpenApiResponse(description="Order item not found"),
    },
)

ORDER_ITEM_UPDATE_SCHEMA = extend_schema(
    tags=["Order Items"],
    summary="Update Order Item",
    description="Update order item details.",
    request=OrderItemUpdateSchema,
    responses={
        200: OpenApiResponse(
            response=OrderItemResponseSchema,
            description="Order item updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Order item not found"),
    },
)

ORDER_ITEM_DELETE_SCHEMA = extend_schema(
    tags=["Order Items"],
    summary="Delete Order Item",
    description="Soft delete an order item.",
    responses={
        204: OpenApiResponse(description="Order item deleted successfully"),
        404: OpenApiResponse(description="Order item not found"),
    },
)