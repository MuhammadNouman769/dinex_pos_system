from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class VariantCreateSchema(serializers.Serializer):
    """Schema for creating a variant"""
    product = serializers.IntegerField(help_text="Product ID")
    name = serializers.CharField(max_length=255, help_text="Variant name")
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="Variant SKU")
    barcode = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="Variant barcode")
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Base price")
    cost_price = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Cost price")
    position = serializers.IntegerField(default=0, help_text="Display position")
    is_default = serializers.BooleanField(default=False, help_text="Is default variant")
    is_active = serializers.BooleanField(default=True, help_text="Is variant active")


class VariantUpdateSchema(serializers.Serializer):
    """Schema for updating a variant"""
    product = serializers.IntegerField(required=False, help_text="Product ID")
    name = serializers.CharField(max_length=255, required=False, help_text="Variant name")
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="Variant SKU")
    barcode = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="Variant barcode")
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, help_text="Base price")
    cost_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, help_text="Cost price")
    position = serializers.IntegerField(required=False, help_text="Display position")
    is_default = serializers.BooleanField(required=False, help_text="Is default variant")
    is_active = serializers.BooleanField(required=False, help_text="Is variant active")


class VariantResponseSchema(serializers.Serializer):
    """Schema for variant response"""
    id = serializers.IntegerField()
    product = serializers.IntegerField()
    product_name = serializers.CharField()
    name = serializers.CharField()
    sku = serializers.CharField()
    barcode = serializers.CharField()
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    cost_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    position = serializers.IntegerField()
    is_default = serializers.BooleanField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class VariantBulkCreateSchema(serializers.Serializer):
    """Schema for bulk creating variants"""
    product_id = serializers.IntegerField(help_text="Product ID")
    variants = serializers.ListField(
        child=VariantCreateSchema(),
        help_text="List of variants to create"
    )


VARIANT_LIST_SCHEMA = extend_schema(
    summary="List Variants",
    description="Get all variants for the user's organization with optional filtering",
    parameters=[
        OpenApiParameter(
            name='product',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by product ID',
        ),
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
            description='Search variants by name, SKU, or barcode',
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=VariantResponseSchema(many=True),
            description="List of variants"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Variants'],
)

VARIANT_CREATE_SCHEMA = extend_schema(
    summary="Create Variant",
    description="Create a new variant for a product",
    request=VariantCreateSchema,
    responses={
        201: OpenApiResponse(
            response=VariantResponseSchema,
            description="Variant created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Variants'],
)

VARIANT_BULK_CREATE_SCHEMA = extend_schema(
    summary="Bulk Create Variants",
    description="Create multiple variants for a product in a single request",
    request=VariantBulkCreateSchema,
    responses={
        201: OpenApiResponse(
            response={
                "message": "Created X variants.",
                "variant_ids": [1, 2, 3],
                "errors": []
            },
            description="Variants created"
        ),
        400: OpenApiResponse(description="Validation error"),
    },
    tags=['Variants'],
)

VARIANT_RETRIEVE_SCHEMA = extend_schema(
    summary="Retrieve Variant",
    description="Get variant details by ID",
    responses={
        200: OpenApiResponse(
            response=VariantResponseSchema,
            description="Variant details"
        ),
        404: OpenApiResponse(description="Variant not found"),
    },
    tags=['Variants'],
)

VARIANT_UPDATE_SCHEMA = extend_schema(
    summary="Update Variant",
    description="Update variant details",
    request=VariantUpdateSchema,
    responses={
        200: OpenApiResponse(
            response=VariantResponseSchema,
            description="Variant updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Variant not found"),
    },
    tags=['Variants'],
)

VARIANT_DELETE_SCHEMA = extend_schema(
    summary="Delete Variant",
    description="Soft delete a variant (cannot delete if used in active deals)",
    responses={
        204: OpenApiResponse(description="Variant deleted successfully"),
        400: OpenApiResponse(description="Cannot delete variant used in active deals"),
        404: OpenApiResponse(description="Variant not found"),
    },
    tags=['Variants'],
)