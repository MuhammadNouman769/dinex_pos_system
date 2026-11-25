from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class DealItemCreateSchema(serializers.Serializer):
    """Schema for creating a deal item"""
    deal = serializers.IntegerField(help_text="Deal ID")
    product_variant = serializers.IntegerField(help_text="Product variant ID")
    quantity = serializers.IntegerField(default=1, help_text="Quantity")


class DealItemUpdateSchema(serializers.Serializer):
    """Schema for updating a deal item"""
    deal = serializers.IntegerField(required=False, help_text="Deal ID")
    product_variant = serializers.IntegerField(required=False, help_text="Product variant ID")
    quantity = serializers.IntegerField(required=False, help_text="Quantity")


class DealItemResponseSchema(serializers.Serializer):
    """Schema for deal item response"""
    id = serializers.IntegerField()
    deal = serializers.IntegerField()
    deal_name = serializers.CharField()
    product_variant = serializers.IntegerField()
    variant_name = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


# ============================================
# LIST SCHEMA (GET)
# ============================================

DEAL_ITEM_LIST_SCHEMA = extend_schema(
    summary="List Deal Items",
    description="Get all deal items with optional filtering",
    parameters=[
        OpenApiParameter(
            name='deal',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by deal ID',
        ),
        OpenApiParameter(
            name='variant',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by product variant ID',
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=DealItemResponseSchema(many=True),
            description="List of deal items"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deal Items'],
)


# ============================================
# CREATE SCHEMA (POST) - WITH DUMMY DATA
# ============================================

DEAL_ITEM_CREATE_SCHEMA = extend_schema(
    summary="Create Deal Item",
    description="Add a product variant to a deal",
    request=DealItemCreateSchema,
    examples=[
        OpenApiExample(
            name="Add Chicken Burger to Summer Sale",
            summary="Add burger to summer sale",
            description="Add chicken burger variant to the summer sale deal.",
            value={
                "deal": 1,
                "product_variant": 2,
                "quantity": 1
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Add Cheese Pizza to Weekend Special",
            summary="Add pizza to weekend special",
            description="Add cheese pizza variant to the weekend special deal.",
            value={
                "deal": 2,
                "product_variant": 4,
                "quantity": 2
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Add Multiple Quantity",
            summary="Add multiple items",
            description="Add 5 items of a variant to a deal.",
            value={
                "deal": 1,
                "product_variant": 3,
                "quantity": 5
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Add French Fries to Combo Deal",
            summary="Add fries to combo deal",
            description="Add french fries variant to a combo deal.",
            value={
                "deal": 3,
                "product_variant": 5,
                "quantity": 1
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=DealItemResponseSchema,
            description="Deal item created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deal Items'],
)


# ============================================
# RETRIEVE SCHEMA (GET by ID)
# ============================================

DEAL_ITEM_RETRIEVE_SCHEMA = extend_schema(
    summary="Retrieve Deal Item",
    description="Get deal item details by ID",
    responses={
        200: OpenApiResponse(
            response=DealItemResponseSchema,
            description="Deal item details retrieved successfully"
        ),
        404: OpenApiResponse(description="Deal item not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deal Items'],
)


# ============================================
# UPDATE SCHEMA (PUT/PATCH)
# ============================================

DEAL_ITEM_UPDATE_SCHEMA = extend_schema(
    summary="Update Deal Item",
    description="Update deal item details",
    request=DealItemUpdateSchema,
    examples=[
        OpenApiExample(
            name="Update Quantity",
            summary="Change item quantity",
            description="Update the quantity of a deal item.",
            value={
                "quantity": 3
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Change Variant",
            summary="Change product variant",
            description="Replace with a different variant.",
            value={
                "product_variant": 3
            },
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=DealItemResponseSchema,
            description="Deal item updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Deal item not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deal Items'],
)


# ============================================
# DELETE SCHEMA (DELETE)
# ============================================

DEAL_ITEM_DELETE_SCHEMA = extend_schema(
    summary="Delete Deal Item",
    description="Soft delete a deal item",
    responses={
        204: OpenApiResponse(description="Deal item deleted successfully"),
        404: OpenApiResponse(description="Deal item not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deal Items'],
)