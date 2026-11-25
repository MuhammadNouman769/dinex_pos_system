from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class ProductModifierGroupCreateSchema(serializers.Serializer):
    """Schema for creating a product-modifier group link"""
    product = serializers.IntegerField(help_text="Product ID")
    modifier_group = serializers.IntegerField(help_text="Modifier group ID")
    display_order = serializers.IntegerField(default=0, help_text="Display order")
    is_required_override = serializers.BooleanField(required=False, allow_null=True, help_text="Override required status")
    min_selections_override = serializers.IntegerField(required=False, allow_null=True, help_text="Override min selections")
    max_selections_override = serializers.IntegerField(required=False, allow_null=True, help_text="Override max selections")


class ProductModifierGroupUpdateSchema(serializers.Serializer):
    """Schema for updating a product-modifier group link"""
    product = serializers.IntegerField(required=False, help_text="Product ID")
    modifier_group = serializers.IntegerField(required=False, help_text="Modifier group ID")
    display_order = serializers.IntegerField(required=False, help_text="Display order")
    is_required_override = serializers.BooleanField(required=False, allow_null=True, help_text="Override required status")
    min_selections_override = serializers.IntegerField(required=False, allow_null=True, help_text="Override min selections")
    max_selections_override = serializers.IntegerField(required=False, allow_null=True, help_text="Override max selections")


class ProductModifierGroupResponseSchema(serializers.Serializer):
    """Schema for product-modifier group response"""
    id = serializers.IntegerField()
    product = serializers.IntegerField()
    product_name = serializers.CharField()
    modifier_group = serializers.IntegerField()
    modifier_group_name = serializers.CharField()
    display_order = serializers.IntegerField()
    is_required_override = serializers.BooleanField(allow_null=True)
    min_selections_override = serializers.IntegerField(allow_null=True)
    max_selections_override = serializers.IntegerField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ProductModifierGroupBulkCreateSchema(serializers.Serializer):
    """Schema for bulk creating product-modifier group links"""
    product_id = serializers.IntegerField(help_text="Product ID")
    modifier_group_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of modifier group IDs to link"
    )


PRODUCT_MODIFIER_GROUP_LIST_SCHEMA = extend_schema(
    summary="List Product-Modifier Group Links",
    description="Get all product-modifier group links with optional filtering",
    parameters=[
        OpenApiParameter(
            name='product',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by product ID',
        ),
        OpenApiParameter(
            name='modifier_group',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by modifier group ID',
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ProductModifierGroupResponseSchema(many=True),
            description="List of links"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Product Modifier Groups'],
)

PRODUCT_MODIFIER_GROUP_CREATE_SCHEMA = extend_schema(
    summary="Create Product-Modifier Group Link",
    description="Link a modifier group to a product with optional overrides",
    request=ProductModifierGroupCreateSchema,
    responses={
        201: OpenApiResponse(
            response=ProductModifierGroupResponseSchema,
            description="Link created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Product Modifier Groups'],
)

PRODUCT_MODIFIER_GROUP_BULK_CREATE_SCHEMA = extend_schema(
    summary="Bulk Create Product-Modifier Group Links",
    description="Link multiple modifier groups to a product",
    request=ProductModifierGroupBulkCreateSchema,
    responses={
        201: OpenApiResponse(
            response={
                "message": "Created X links.",
                "link_ids": [1, 2, 3],
                "errors": []
            },
            description="Links created"
        ),
        400: OpenApiResponse(description="Validation error"),
    },
    tags=['Product Modifier Groups'],
)

PRODUCT_MODIFIER_GROUP_RETRIEVE_SCHEMA = extend_schema(
    summary="Retrieve Product-Modifier Group Link",
    description="Get product-modifier group link details by ID",
    responses={
        200: OpenApiResponse(
            response=ProductModifierGroupResponseSchema,
            description="Link details"
        ),
        404: OpenApiResponse(description="Link not found"),
    },
    tags=['Product Modifier Groups'],
)

PRODUCT_MODIFIER_GROUP_UPDATE_SCHEMA = extend_schema(
    summary="Update Product-Modifier Group Link",
    description="Update product-modifier group link details",
    request=ProductModifierGroupUpdateSchema,
    responses={
        200: OpenApiResponse(
            response=ProductModifierGroupResponseSchema,
            description="Link updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Link not found"),
    },
    tags=['Product Modifier Groups'],
)

PRODUCT_MODIFIER_GROUP_DELETE_SCHEMA = extend_schema(
    summary="Delete Product-Modifier Group Link",
    description="Soft delete a product-modifier group link",
    responses={
        204: OpenApiResponse(description="Link deleted successfully"),
        404: OpenApiResponse(description="Link not found"),
    },
    tags=['Product Modifier Groups'],
)