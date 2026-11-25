from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class ProductLocationCreateSchema(serializers.Serializer):
    """Schema for creating a product location assignment"""
    product = serializers.IntegerField(required=False, help_text="Product ID")
    product_variant = serializers.IntegerField(required=False, help_text="Product variant ID")
    location = serializers.IntegerField(help_text="Location ID")
    is_available = serializers.BooleanField(default=True, help_text="Is product available at this location")
    available_quantity = serializers.IntegerField(default=0, help_text="Available quantity")


class ProductLocationUpdateSchema(serializers.Serializer):
    """Schema for updating a product location assignment"""
    product = serializers.IntegerField(required=False, help_text="Product ID")
    product_variant = serializers.IntegerField(required=False, help_text="Product variant ID")
    location = serializers.IntegerField(required=False, help_text="Location ID")
    is_available = serializers.BooleanField(required=False, help_text="Is product available at this location")
    available_quantity = serializers.IntegerField(required=False, help_text="Available quantity")


class ProductLocationResponseSchema(serializers.Serializer):
    """Schema for product location response"""
    id = serializers.IntegerField()
    product = serializers.IntegerField()
    product_name = serializers.CharField()
    product_variant = serializers.IntegerField(allow_null=True)
    variant_name = serializers.CharField(allow_null=True)
    location = serializers.IntegerField()
    location_name = serializers.CharField()
    is_available = serializers.BooleanField()
    available_quantity = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ProductLocationBulkAssignSchema(serializers.Serializer):
    """Schema for bulk assigning products to locations"""
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of product IDs"
    )
    variant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of variant IDs"
    )
    location_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of location IDs"
    )
    is_available = serializers.BooleanField(default=True, help_text="Is product available")
    available_quantity = serializers.IntegerField(default=0, help_text="Available quantity")


PRODUCT_LOCATION_LIST_SCHEMA = extend_schema(
    summary="List Product Location Assignments",
    description="Get all product location assignments with optional filtering",
    parameters=[
        OpenApiParameter(
            name='product',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by product ID',
        ),
        OpenApiParameter(
            name='location',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by location ID',
        ),
        OpenApiParameter(
            name='available',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Filter by availability',
            default=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ProductLocationResponseSchema(many=True),
            description="List of assignments"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Product Locations'],
)

PRODUCT_LOCATION_CREATE_SCHEMA = extend_schema(
    summary="Create Product Location Assignment",
    description="Assign a product or variant to a location",
    request=ProductLocationCreateSchema,
    responses={
        201: OpenApiResponse(
            response=ProductLocationResponseSchema,
            description="Assignment created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Product Locations'],
)

PRODUCT_LOCATION_BULK_ASSIGN_SCHEMA = extend_schema(
    summary="Bulk Assign Products to Locations",
    description="Assign multiple products/variants to multiple locations",
    request=ProductLocationBulkAssignSchema,
    responses={
        201: OpenApiResponse(
            response={
                "message": "Created X assignments.",
                "assignment_ids": [1, 2, 3],
                "errors": []
            },
            description="Assignments created"
        ),
        400: OpenApiResponse(description="Validation error"),
    },
    tags=['Product Locations'],
)

PRODUCT_LOCATION_RETRIEVE_SCHEMA = extend_schema(
    summary="Retrieve Product Location Assignment",
    description="Get product location assignment details by ID",
    responses={
        200: OpenApiResponse(
            response=ProductLocationResponseSchema,
            description="Assignment details"
        ),
        404: OpenApiResponse(description="Assignment not found"),
    },
    tags=['Product Locations'],
)

PRODUCT_LOCATION_UPDATE_SCHEMA = extend_schema(
    summary="Update Product Location Assignment",
    description="Update product location assignment details",
    request=ProductLocationUpdateSchema,
    responses={
        200: OpenApiResponse(
            response=ProductLocationResponseSchema,
            description="Assignment updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Assignment not found"),
    },
    tags=['Product Locations'],
)

PRODUCT_LOCATION_DELETE_SCHEMA = extend_schema(
    summary="Delete Product Location Assignment",
    description="Soft delete a product location assignment",
    responses={
        204: OpenApiResponse(description="Assignment deleted successfully"),
        404: OpenApiResponse(description="Assignment not found"),
    },
    tags=['Product Locations'],
)