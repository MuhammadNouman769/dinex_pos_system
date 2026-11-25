from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class DealItemInlineSchema(serializers.Serializer):
    """Schema for inline deal item"""
    product_variant = serializers.IntegerField(help_text="Product variant ID")
    quantity = serializers.IntegerField(default=1, help_text="Quantity")


class DealLocationInlineSchema(serializers.Serializer):
    """Schema for inline deal location"""
    location = serializers.IntegerField(help_text="Location ID")
    is_enabled = serializers.BooleanField(default=True, help_text="Is deal enabled at this location")


class DealCreateSchema(serializers.Serializer):
    """Schema for creating a deal"""
    name = serializers.CharField(max_length=255, help_text="Deal name")
    slug = serializers.SlugField(max_length=255, help_text="Deal slug (unique per organization)")
    description = serializers.CharField(required=False, allow_blank=True, help_text="Deal description")
    discount_type = serializers.ChoiceField(
        choices=['FIXED', 'PERCENTAGE'],
        help_text="Discount type"
    )
    discount_value = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Discount value")
    start_at = serializers.DateTimeField(help_text="Start date and time")
    end_at = serializers.DateTimeField(help_text="End date and time")
    is_active = serializers.BooleanField(default=True, help_text="Is deal active")
    items = serializers.ListField(
        child=DealItemInlineSchema(),
        required=False,
        help_text="List of deal items"
    )
    locations = serializers.ListField(
        child=DealLocationInlineSchema(),
        required=False,
        help_text="List of deal locations"
    )


class DealUpdateSchema(serializers.Serializer):
    """Schema for updating a deal"""
    name = serializers.CharField(max_length=255, required=False, help_text="Deal name")
    slug = serializers.SlugField(max_length=255, required=False, help_text="Deal slug")
    description = serializers.CharField(required=False, allow_blank=True, help_text="Deal description")
    discount_type = serializers.ChoiceField(
        choices=['FIXED', 'PERCENTAGE'],
        required=False,
        help_text="Discount type"
    )
    discount_value = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, help_text="Discount value")
    start_at = serializers.DateTimeField(required=False, help_text="Start date and time")
    end_at = serializers.DateTimeField(required=False, help_text="End date and time")
    is_active = serializers.BooleanField(required=False, help_text="Is deal active")


class DealResponseSchema(serializers.Serializer):
    """Schema for deal response"""
    id = serializers.IntegerField()
    organization = serializers.IntegerField()
    organization_name = serializers.CharField()
    name = serializers.CharField()
    slug = serializers.CharField()
    description = serializers.CharField()
    discount_type = serializers.CharField()
    discount_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    is_active = serializers.BooleanField()
    items = serializers.ListField()
    locations = serializers.ListField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


# ============================================
# LIST SCHEMA (GET)
# ============================================

DEAL_LIST_SCHEMA = extend_schema(
    summary="List Deals",
    description="Get all deals for the user's organization with optional filtering",
    parameters=[
        OpenApiParameter(
            name='active',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Filter by active status',
            default=True,
        ),
        OpenApiParameter(
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search deals by name or description',
        ),
        OpenApiParameter(
            name='location',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by location ID (deals available at this location)',
        ),
        OpenApiParameter(
            name='active_deals',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Get only currently active deals (based on date range)',
            default=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=DealResponseSchema(many=True),
            description="List of deals"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deals'],
)


# ============================================
# CREATE SCHEMA (POST) - WITH DUMMY DATA
# ============================================

DEAL_CREATE_SCHEMA = extend_schema(
    summary="Create Deal",
    description="Create a new deal with optional items and locations",
    request=DealCreateSchema,
    examples=[
        OpenApiExample(
            name="Create Percentage Discount Deal",
            summary="Create a percentage-based discount deal",
            description="20% off on all burgers for summer.",
            value={
                "name": "Summer Sale",
                "slug": "summer-sale",
                "description": "20% off on all burgers this summer!",
                "discount_type": "PERCENTAGE",
                "discount_value": "20.00",
                "start_at": "2026-09-10T00:00:00Z",
                "end_at": "2026-10-10T23:59:59Z",
                "is_active": True,
                "items": [
                    {
                        "product_variant": 2,
                        "quantity": 1
                    }
                ],
                "locations": [
                    {
                        "location": 4,
                        "is_enabled": True
                    }
                ]
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Fixed Discount Deal",
            summary="Create a fixed amount discount deal",
            description="Rs.50 off on all pizzas for weekend.",
            value={
                "name": "Weekend Special",
                "slug": "weekend-special",
                "description": "Rs.50 off on all pizzas this weekend!",
                "discount_type": "FIXED",
                "discount_value": "50.00",
                "start_at": "2026-09-12T00:00:00Z",
                "end_at": "2026-09-14T23:59:59Z",
                "is_active": True,
                "items": [
                    {
                        "product_variant": 4,
                        "quantity": 2
                    }
                ],
                "locations": [
                    {
                        "location": 4,
                        "is_enabled": True
                    }
                ]
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Multiple Items Deal",
            summary="Create a deal with multiple items",
            description="Combo deal with burger and fries.",
            value={
                "name": "Combo Deal",
                "slug": "combo-deal",
                "description": "Get burger and fries combo at discounted price!",
                "discount_type": "FIXED",
                "discount_value": "30.00",
                "start_at": "2026-09-15T00:00:00Z",
                "end_at": "2026-10-15T23:59:59Z",
                "is_active": True,
                "items": [
                    {
                        "product_variant": 2,
                        "quantity": 1
                    },
                    {
                        "product_variant": 5,
                        "quantity": 1
                    }
                ],
                "locations": [
                    {
                        "location": 4,
                        "is_enabled": True
                    }
                ]
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Deal All Locations",
            summary="Create a deal available at all locations",
            description="Deal available everywhere.",
            value={
                "name": "Global Sale",
                "slug": "global-sale",
                "description": "Special discount for all locations!",
                "discount_type": "PERCENTAGE",
                "discount_value": "15.00",
                "start_at": "2026-10-01T00:00:00Z",
                "end_at": "2026-10-31T23:59:59Z",
                "is_active": True,
                "items": [
                    {
                        "product_variant": 2,
                        "quantity": 1
                    }
                ],
                "locations": [
                    {
                        "location": 4,
                        "is_enabled": True
                    }
                ]
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=DealResponseSchema,
            description="Deal created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deals'],
)


# ============================================
# RETRIEVE SCHEMA (GET by ID)
# ============================================

DEAL_RETRIEVE_SCHEMA = extend_schema(
    summary="Retrieve Deal",
    description="Get deal details by ID with all items and locations",
    responses={
        200: OpenApiResponse(
            response=DealResponseSchema,
            description="Deal details retrieved successfully"
        ),
        404: OpenApiResponse(description="Deal not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deals'],
)


# ============================================
# UPDATE SCHEMA (PUT/PATCH)
# ============================================

DEAL_UPDATE_SCHEMA = extend_schema(
    summary="Update Deal",
    description="Update deal details with items and locations",
    request=DealUpdateSchema,
    examples=[
        OpenApiExample(
            name="Update Deal Name",
            summary="Update deal name and description",
            description="Change deal name.",
            value={
                "name": "Summer Sale 2026",
                "description": "Updated summer sale description",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Update Discount Value",
            summary="Update discount value",
            description="Change discount percentage.",
            value={
                "discount_value": "25.00"
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Deactivate Deal",
            summary="Deactivate a deal",
            description="Set deal as inactive.",
            value={
                "is_active": False
            },
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=DealResponseSchema,
            description="Deal updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Deal not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deals'],
)


# ============================================
# DELETE SCHEMA (DELETE)
# ============================================

DEAL_DELETE_SCHEMA = extend_schema(
    summary="Delete Deal",
    description="Soft delete a deal",
    responses={
        204: OpenApiResponse(description="Deal deleted successfully"),
        404: OpenApiResponse(description="Deal not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deals'],
)


# ============================================
# TOGGLE ACTIVE SCHEMA (POST Toggle)
# ============================================

DEAL_TOGGLE_ACTIVE_SCHEMA = extend_schema(
    summary="Toggle Deal Active Status",
    description="Activate or deactivate a deal",
    responses={
        200: OpenApiResponse(
            description="Deal status toggled successfully",
            examples=[
                OpenApiExample(
                    name="Activated",
                    summary="Deal activated",
                    description="Response when deal is activated.",
                    value={
                        "id": 1,
                        "is_active": True,
                        "message": "Deal activated successfully."
                    }
                ),
                OpenApiExample(
                    name="Deactivated",
                    summary="Deal deactivated",
                    description="Response when deal is deactivated.",
                    value={
                        "id": 1,
                        "is_active": False,
                        "message": "Deal deactivated successfully."
                    }
                )
            ]
        ),
        404: OpenApiResponse(description="Deal not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deals'],
)