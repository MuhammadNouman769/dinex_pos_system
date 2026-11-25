from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


# ============================================
# REQUEST SCHEMAS
# ============================================

class ProductCreateSchema(serializers.Serializer):
    """Schema for creating a product"""
    category = serializers.IntegerField(help_text="Category ID")
    name = serializers.CharField(max_length=255, help_text="Product name")
    slug = serializers.SlugField(max_length=255, help_text="Product slug (unique per organization)")
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="Product SKU")
    description = serializers.CharField(required=False, allow_blank=True, help_text="Product description")
    product_type = serializers.ChoiceField(
        choices=['SELLABLE', 'INVENTORY', 'PREPARED'],
        default='SELLABLE',
        help_text="Product type"
    )
    image = serializers.ImageField(required=False, allow_null=True, help_text="Product image")
    is_active = serializers.BooleanField(default=True, help_text="Is product active")
    dietary_tags = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of dietary tag IDs"
    )
    variants = serializers.ListField(
        child=inline_serializer(
            name='VariantCreateInline',
            fields={
                'name': serializers.CharField(max_length=255),
                'sku': serializers.CharField(max_length=100, required=False, allow_blank=True),
                'barcode': serializers.CharField(max_length=100, required=False, allow_blank=True),
                'base_price': serializers.DecimalField(max_digits=12, decimal_places=2, default=0),
                'cost_price': serializers.DecimalField(max_digits=12, decimal_places=2, default=0),
                'is_default': serializers.BooleanField(default=False),
                'is_active': serializers.BooleanField(default=True),
            }
        ),
        required=False,
        help_text="List of variants to create with the product"
    )


class ProductUpdateSchema(serializers.Serializer):
    """Schema for updating a product"""
    category = serializers.IntegerField(required=False, help_text="Category ID")
    name = serializers.CharField(max_length=255, required=False, help_text="Product name")
    slug = serializers.SlugField(max_length=255, required=False, help_text="Product slug")
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="Product SKU")
    description = serializers.CharField(required=False, allow_blank=True, help_text="Product description")
    product_type = serializers.ChoiceField(
        choices=['SELLABLE', 'INVENTORY', 'PREPARED'],
        required=False,
        help_text="Product type"
    )
    image = serializers.ImageField(required=False, allow_null=True, help_text="Product image")
    is_active = serializers.BooleanField(required=False, help_text="Is product active")
    dietary_tags = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of dietary tag IDs"
    )


# ============================================
# RESPONSE SCHEMAS
# ============================================

class ProductResponseSchema(serializers.Serializer):
    """Schema for product response"""
    id = serializers.IntegerField()
    organization = serializers.IntegerField()
    organization_name = serializers.CharField()
    category = serializers.IntegerField()
    category_name = serializers.CharField()
    name = serializers.CharField()
    slug = serializers.CharField()
    sku = serializers.CharField()
    description = serializers.CharField()
    product_type = serializers.CharField()
    image = serializers.CharField(allow_null=True)
    is_active = serializers.BooleanField()
    dietary_tags = serializers.ListField()
    variants = serializers.ListField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ProductBulkCreateSchema(serializers.Serializer):
    """Schema for bulk creating products"""
    products = serializers.ListField(
        child=ProductCreateSchema(),
        help_text="List of products to create"
    )


# ============================================
# LIST SCHEMA (GET)
# ============================================

PRODUCT_LIST_SCHEMA = extend_schema(
    summary="List Products",
    description="Get all products for the user's organization with optional filtering",
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
            description='Search products by name, SKU, or description',
        ),
        OpenApiParameter(
            name='category',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by category ID',
        ),
        OpenApiParameter(
            name='type',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by product type (SELLABLE, INVENTORY, PREPARED)',
        ),
        OpenApiParameter(
            name='location',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by location ID (products available at this location)',
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ProductResponseSchema(many=True),
            description="List of products"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Products'],
)


# ============================================
# CREATE SCHEMA (POST) - WITH DUMMY DATA
# ============================================

PRODUCT_CREATE_SCHEMA = extend_schema(
    summary="Create Product",
    description="Create a new product with optional variants and dietary tags",
    request=ProductCreateSchema,
    examples=[
        OpenApiExample(
            name="Create Chicken Burger",
            summary="Create a chicken burger product",
            description="Chicken burger with single and double patty variants.",
            value={
                "category": 2,
                "name": "Chicken Burger",
                "slug": "chicken-burger",
                "sku": "CB-001",
                "description": "Delicious grilled chicken burger with fresh veggies",
                "product_type": "SELLABLE",
                "is_active": True,
                "dietary_tags": [1, 4],
                "variants": [
                    {
                        "name": "Single Patty",
                        "base_price": "10.00",
                        "cost_price": "5.00",
                        "is_default": True,
                        "is_active": True
                    },
                    {
                        "name": "Double Patty",
                        "base_price": "15.00",
                        "cost_price": "8.00",
                        "is_default": False,
                        "is_active": True
                    }
                ]
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Cheese Pizza",
            summary="Create a cheese pizza product",
            description="Classic cheese pizza with small and large variants.",
            value={
                "category": 3,
                "name": "Cheese Pizza",
                "slug": "cheese-pizza",
                "sku": "PZ-001",
                "description": "Classic cheese pizza with mozzarella",
                "product_type": "SELLABLE",
                "is_active": True,
                "dietary_tags": [1],
                "variants": [
                    {
                        "name": "Small",
                        "base_price": "12.00",
                        "cost_price": "6.00",
                        "is_default": True,
                        "is_active": True
                    },
                    {
                        "name": "Large",
                        "base_price": "18.00",
                        "cost_price": "9.00",
                        "is_default": False,
                        "is_active": True
                    }
                ]
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Chicken Shawarma",
            summary="Create a chicken shawarma product",
            description="Authentic chicken shawarma with garlic sauce.",
            value={
                "category": 4,
                "name": "Chicken Shawarma",
                "slug": "chicken-shawarma",
                "sku": "SW-001",
                "description": "Authentic chicken shawarma with garlic sauce",
                "product_type": "SELLABLE",
                "is_active": True,
                "dietary_tags": [1, 4],
                "variants": [
                    {
                        "name": "Regular",
                        "base_price": "8.00",
                        "cost_price": "4.00",
                        "is_default": True,
                        "is_active": True
                    }
                ]
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create French Fries",
            summary="Create a french fries product",
            description="Crispy french fries with no variants.",
            value={
                "category": 2,
                "name": "French Fries",
                "slug": "french-fries",
                "sku": "FF-001",
                "description": "Crispy golden french fries",
                "product_type": "SELLABLE",
                "is_active": True,
                "dietary_tags": [1],
                "variants": [
                    {
                        "name": "Regular",
                        "base_price": "5.00",
                        "cost_price": "2.50",
                        "is_default": True,
                        "is_active": True
                    }
                ]
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Zinger Burger",
            summary="Create a zinger burger product",
            description="Spicy zinger burger with crispy chicken.",
            value={
                "category": 2,
                "name": "Zinger Burger",
                "slug": "zinger-burger",
                "sku": "ZB-001",
                "description": "Spicy crispy zinger burger with special sauce",
                "product_type": "SELLABLE",
                "is_active": True,
                "dietary_tags": [1, 4],
                "variants": [
                    {
                        "name": "Single",
                        "base_price": "11.00",
                        "cost_price": "5.50",
                        "is_default": True,
                        "is_active": True
                    }
                ]
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=ProductResponseSchema,
            description="Product created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Products'],
)


# ============================================
# BULK CREATE SCHEMA
# ============================================

PRODUCT_BULK_CREATE_SCHEMA = extend_schema(
    summary="Bulk Create Products",
    description="Create multiple products in a single request",
    request=ProductBulkCreateSchema,
    examples=[
        OpenApiExample(
            name="Bulk Create Products",
            summary="Create multiple products at once",
            description="Bulk create chicken burger, pizza and fries.",
            value={
                "products": [
                    {
                        "category": 2,
                        "name": "Chicken Burger",
                        "slug": "chicken-burger",
                        "sku": "CB-001",
                        "product_type": "SELLABLE",
                        "is_active": True,
                        "variants": [
                            {
                                "name": "Single Patty",
                                "base_price": "10.00",
                                "is_default": True,
                                "is_active": True
                            }
                        ]
                    },
                    {
                        "category": 3,
                        "name": "Cheese Pizza",
                        "slug": "cheese-pizza",
                        "sku": "PZ-001",
                        "product_type": "SELLABLE",
                        "is_active": True,
                        "variants": [
                            {
                                "name": "Small",
                                "base_price": "12.00",
                                "is_default": True,
                                "is_active": True
                            }
                        ]
                    },
                    {
                        "category": 2,
                        "name": "French Fries",
                        "slug": "french-fries",
                        "sku": "FF-001",
                        "product_type": "SELLABLE",
                        "is_active": True,
                        "variants": [
                            {
                                "name": "Regular",
                                "base_price": "5.00",
                                "is_default": True,
                                "is_active": True
                            }
                        ]
                    }
                ]
            },
            request_only=True,
        )
    ],
    responses={
        201: OpenApiResponse(
            description="Products created"
        ),
        400: OpenApiResponse(description="Validation error"),
    },
    tags=['Products'],
)


# ============================================
# RETRIEVE SCHEMA (GET by ID)
# ============================================

PRODUCT_RETRIEVE_SCHEMA = extend_schema(
    summary="Retrieve Product",
    description="Get product details by ID with all related data",
    responses={
        200: OpenApiResponse(
            response=ProductResponseSchema,
            description="Product details retrieved successfully"
        ),
        404: OpenApiResponse(description="Product not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Products'],
)


# ============================================
# UPDATE SCHEMA (PUT/PATCH)
# ============================================

PRODUCT_UPDATE_SCHEMA = extend_schema(
    summary="Update Product",
    description="Update product details",
    request=ProductUpdateSchema,
    examples=[
        OpenApiExample(
            name="Update Product Name",
            summary="Update product name and slug",
            description="Change product name and slug.",
            value={
                "name": "Chicken Burger Deluxe",
                "slug": "chicken-burger-deluxe",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Update Product Price",
            summary="Update product variant prices",
            description="Change variant prices.",
            value={
                "variants": [
                    {
                        "id": 1,
                        "base_price": "12.00",
                        "cost_price": "6.00"
                    },
                    {
                        "id": 2,
                        "base_price": "18.00",
                        "cost_price": "9.00"
                    }
                ]
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Deactivate Product",
            summary="Deactivate a product",
            description="Set product as inactive.",
            value={
                "is_active": False
            },
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ProductResponseSchema,
            description="Product updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Product not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Products'],
)


# ============================================
# DELETE SCHEMA (DELETE)
# ============================================

PRODUCT_DELETE_SCHEMA = extend_schema(
    summary="Delete Product",
    description="Soft delete a product (cannot delete if it has active variants)",
    responses={
        204: OpenApiResponse(description="Product deleted successfully"),
        400: OpenApiResponse(
            description="Cannot delete product with active variants",
            examples=[
                OpenApiExample(
                    name="Delete Error",
                    summary="Product has active variants",
                    description="Error when trying to delete product with variants.",
                    value={
                        "error": "Cannot delete product with active variants."
                    }
                )
            ]
        ),
        404: OpenApiResponse(description="Product not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Products'],
)