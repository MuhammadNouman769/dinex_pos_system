from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class DealLocationCreateSchema(serializers.Serializer):
    """Schema for creating a deal location assignment"""
    deal = serializers.IntegerField(help_text="Deal ID")
    location = serializers.IntegerField(help_text="Location ID")
    is_enabled = serializers.BooleanField(default=True, help_text="Is deal enabled at this location")


class DealLocationUpdateSchema(serializers.Serializer):
    """Schema for updating a deal location assignment"""
    deal = serializers.IntegerField(required=False, help_text="Deal ID")
    location = serializers.IntegerField(required=False, help_text="Location ID")
    is_enabled = serializers.BooleanField(required=False, help_text="Is deal enabled at this location")


class DealLocationResponseSchema(serializers.Serializer):
    """Schema for deal location response"""
    id = serializers.IntegerField()
    deal = serializers.IntegerField()
    deal_name = serializers.CharField()
    location = serializers.IntegerField()
    location_name = serializers.CharField()
    is_enabled = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class DealLocationBulkAssignSchema(serializers.Serializer):
    """Schema for bulk assigning deals to locations"""
    deal_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of deal IDs"
    )
    location_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of location IDs"
    )
    is_enabled = serializers.BooleanField(default=True, help_text="Is deal enabled")


# ============================================
# LIST SCHEMA (GET)
# ============================================

DEAL_LOCATION_LIST_SCHEMA = extend_schema(
    summary="List Deal Location Assignments",
    description="Get all deal location assignments with optional filtering",
    parameters=[
        OpenApiParameter(
            name='deal',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by deal ID',
        ),
        OpenApiParameter(
            name='location',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by location ID',
        ),
        OpenApiParameter(
            name='enabled',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Filter by enabled status',
            default=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=DealLocationResponseSchema(many=True),
            description="List of assignments"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deal Locations'],
)


# ============================================
# CREATE SCHEMA (POST) - WITH DUMMY DATA
# ============================================

DEAL_LOCATION_CREATE_SCHEMA = extend_schema(
    summary="Create Deal Location Assignment",
    description="Assign a deal to a location",
    request=DealLocationCreateSchema,
    examples=[
        OpenApiExample(
            name="Assign Summer Sale to Main Branch",
            summary="Assign deal to main branch",
            description="Make summer sale available at main branch.",
            value={
                "deal": 1,
                "location": 4,
                "is_enabled": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Assign Weekend Special to Multiple Locations",
            summary="Assign deal to multiple locations",
            description="Make weekend special available at all branches.",
            value={
                "deal": 2,
                "location": 4,
                "is_enabled": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Disable Deal at Location",
            summary="Disable deal at a location",
            description="Temporarily disable a deal at a specific location.",
            value={
                "deal": 1,
                "location": 4,
                "is_enabled": False
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=DealLocationResponseSchema,
            description="Assignment created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deal Locations'],
)


# ============================================
# BULK ASSIGN SCHEMA
# ============================================

DEAL_LOCATION_BULK_ASSIGN_SCHEMA = extend_schema(
    summary="Bulk Assign Deals to Locations",
    description="Assign multiple deals to multiple locations in a single request",
    request=DealLocationBulkAssignSchema,
    examples=[
        OpenApiExample(
            name="Bulk Assign Deals to All Locations",
            summary="Assign multiple deals to all locations",
            description="Make all deals available at all branches.",
            value={
                "deal_ids": [1, 2, 3],
                "location_ids": [4, 5, 6],
                "is_enabled": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Bulk Disable Deals at Locations",
            summary="Disable multiple deals at locations",
            description="Temporarily disable deals at specific locations.",
            value={
                "deal_ids": [1, 2],
                "location_ids": [4, 5],
                "is_enabled": False
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            description="Assignments created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deal Locations'],
)


# ============================================
# RETRIEVE SCHEMA (GET by ID)
# ============================================

DEAL_LOCATION_RETRIEVE_SCHEMA = extend_schema(
    summary="Retrieve Deal Location Assignment",
    description="Get deal location assignment details by ID",
    responses={
        200: OpenApiResponse(
            response=DealLocationResponseSchema,
            description="Assignment details retrieved successfully"
        ),
        404: OpenApiResponse(description="Assignment not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deal Locations'],
)


# ============================================
# UPDATE SCHEMA (PUT/PATCH)
# ============================================

DEAL_LOCATION_UPDATE_SCHEMA = extend_schema(
    summary="Update Deal Location Assignment",
    description="Update deal location assignment details",
    request=DealLocationUpdateSchema,
    examples=[
        OpenApiExample(
            name="Enable Deal at Location",
            summary="Enable a deal at a location",
            description="Activate a deal at a specific location.",
            value={
                "is_enabled": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Disable Deal at Location",
            summary="Disable a deal at a location",
            description="Deactivate a deal at a specific location.",
            value={
                "is_enabled": False
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Change Location for Deal",
            summary="Change location for a deal",
            description="Move a deal to a different location.",
            value={
                "location": 5
            },
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=DealLocationResponseSchema,
            description="Assignment updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Assignment not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deal Locations'],
)


# ============================================
# DELETE SCHEMA (DELETE)
# ============================================

DEAL_LOCATION_DELETE_SCHEMA = extend_schema(
    summary="Delete Deal Location Assignment",
    description="Soft delete a deal location assignment",
    responses={
        204: OpenApiResponse(description="Assignment deleted successfully"),
        404: OpenApiResponse(description="Assignment not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Deal Locations'],
)