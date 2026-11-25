from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    OpenApiParameter,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers


# ============================================
# REQUEST SCHEMAS (Input)
# ============================================

class CategoryCreateSchema(serializers.Serializer):
    """Schema for creating a category"""
    name = serializers.CharField(
        max_length=255, 
        help_text="Category name"
    )
    slug = serializers.SlugField(
        max_length=255, 
        help_text="Category slug (unique per organization)"
    )
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="Category description"
    )
    parent = serializers.IntegerField(
        required=False, 
        allow_null=True, 
        default=None,
        help_text="Parent category ID (null for root category)"
    )
    image = serializers.ImageField(
        required=False, 
        allow_null=True, 
        help_text="Category image"
    )
    is_active = serializers.BooleanField(
        default=True, 
        help_text="Is category active"
    )
    position = serializers.IntegerField(
        required=False, 
        help_text="Display position"
    )


class CategoryUpdateSchema(serializers.Serializer):
    """Schema for updating a category"""
    name = serializers.CharField(
        max_length=255, 
        required=False, 
        help_text="Category name"
    )
    slug = serializers.SlugField(
        max_length=255, 
        required=False, 
        help_text="Category slug"
    )
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        help_text="Category description"
    )
    parent = serializers.IntegerField(
        required=False, 
        allow_null=True, 
        default=None,
        help_text="Parent category ID (null for root category)"
    )
    image = serializers.ImageField(
        required=False, 
        allow_null=True, 
        help_text="Category image"
    )
    is_active = serializers.BooleanField(
        required=False, 
        help_text="Is category active"
    )
    position = serializers.IntegerField(
        required=False, 
        help_text="Display position"
    )


# ============================================
# RESPONSE SCHEMAS (Output)
# ============================================

class CategoryResponseSchema(serializers.Serializer):
    """Schema for category response"""
    id = serializers.IntegerField(help_text="Category ID")
    organization = serializers.IntegerField(help_text="Organization ID")
    organization_name = serializers.CharField(help_text="Organization name")
    name = serializers.CharField(help_text="Category name")
    slug = serializers.CharField(help_text="Category slug")
    description = serializers.CharField(help_text="Category description")
    parent = serializers.IntegerField(allow_null=True, help_text="Parent category ID")
    parent_name = serializers.CharField(allow_null=True, help_text="Parent category name")
    image = serializers.CharField(allow_null=True, help_text="Category image URL")
    is_active = serializers.BooleanField(help_text="Is category active")
    position = serializers.IntegerField(help_text="Display position")
    children = serializers.ListField(help_text="Child categories")
    created_at = serializers.DateTimeField(help_text="Created timestamp")
    updated_at = serializers.DateTimeField(help_text="Updated timestamp")


# ============================================
# REORDER SCHEMA
# ============================================

class CategoryReorderSchema(serializers.Serializer):
    """Schema for reordering categories"""
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of category IDs in desired order"
    )


# ============================================
# CATEGORY LIST SCHEMA (GET)
# ============================================

CATEGORY_LIST_SCHEMA = extend_schema(
    tags=["Categories"],
    summary="List Categories",
    description="Get all categories for the user's organization with optional filtering.",
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
            description='Search categories by name or description',
        ),
        OpenApiParameter(
            name='root_only',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Get only root categories (no parent)',
            default=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=CategoryResponseSchema(many=True),
            description="List of categories retrieved successfully."
        ),
        401: OpenApiResponse(description="Authentication required."),
    },
)


# ============================================
# ✅ CATEGORY CREATE SCHEMA (With Dummy Data)
# ============================================

CATEGORY_CREATE_SCHEMA = extend_schema(
    tags=["Categories"],
    summary="Create Category",
    description="Create a new category for the user's organization.",
    request=CategoryCreateSchema,
    examples=[
        OpenApiExample(
            name="Create Root Category",
            summary="Create a main menu category",
            description="Create a root category with no parent.",
            value={
                "name": "Main Menu",
                "slug": "main-menu",
                "description": "All main menu categories including breakfast, lunch and dinner",
                "parent": None,
                "image": None,
                "is_active": True,
                "position": 1
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Breakfast Category",
            summary="Create a breakfast category",
            description="Create a sub-category under Main Menu.",
            value={
                "name": "Breakfast",
                "slug": "breakfast",
                "description": "All breakfast items including eggs, pancakes and parathas",
                "parent": 1,
                "image": None,
                "is_active": True,
                "position": 1
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Lunch Category",
            summary="Create a lunch category",
            description="Create a sub-category under Main Menu.",
            value={
                "name": "Lunch",
                "slug": "lunch",
                "description": "All lunch items including burgers, pizzas and sandwiches",
                "parent": 1,
                "image": None,
                "is_active": True,
                "position": 2
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Dinner Category",
            summary="Create a dinner category",
            description="Create a sub-category under Main Menu.",
            value={
                "name": "Dinner",
                "slug": "dinner",
                "description": "All dinner items including BBQ, steaks and grills",
                "parent": 1,
                "image": None,
                "is_active": True,
                "position": 3
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Beverages Category",
            summary="Create a beverages category",
            description="Create a root category for drinks.",
            value={
                "name": "Beverages",
                "slug": "beverages",
                "description": "All beverages including cold drinks, juices and shakes",
                "parent": None,
                "image": None,
                "is_active": True,
                "position": 2
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Desserts Category",
            summary="Create a desserts category",
            description="Create a root category for sweets.",
            value={
                "name": "Desserts",
                "slug": "desserts",
                "description": "All desserts including cakes, pastries and ice cream",
                "parent": None,
                "image": None,
                "is_active": True,
                "position": 3
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=CategoryResponseSchema,
            description="Category created successfully."
        ),
        400: OpenApiResponse(description="Validation error."),
        401: OpenApiResponse(description="Authentication required."),
    },
)


# ============================================
# ✅ CATEGORY UPDATE SCHEMA (With Dummy Data)
# ============================================

CATEGORY_UPDATE_SCHEMA = extend_schema(
    tags=["Categories"],
    summary="Update Category",
    description="Update category details (full or partial).",
    request=CategoryUpdateSchema,
    examples=[
        OpenApiExample(
            name="Update Category Name",
            summary="Update category name and slug",
            description="Update name and slug of a category.",
            value={
                "name": "Main Menu Updated",
                "slug": "main-menu-updated",
                "description": "Updated description for main menu",
                "parent": None,
                "is_active": True,
                "position": 1
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Change Category Parent",
            summary="Move category to another parent",
            description="Change parent category of a sub-category.",
            value={
                "parent": 2,
                "position": 1
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Deactivate Category",
            summary="Deactivate a category",
            description="Set category as inactive.",
            value={
                "is_active": False
            },
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=CategoryResponseSchema,
            description="Category updated successfully."
        ),
        400: OpenApiResponse(description="Validation error."),
        404: OpenApiResponse(description="Category not found."),
    },
)


# ============================================
# ✅ CATEGORY RETRIEVE SCHEMA (GET by ID)
# ============================================

CATEGORY_RETRIEVE_SCHEMA = extend_schema(
    tags=["Categories"],
    summary="Retrieve Category",
    description="Get category details by ID.",
    parameters=[
        OpenApiParameter(
            name='include_children',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Include children categories',
            default=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=CategoryResponseSchema,
            description="Category details retrieved successfully.",
            examples=[
                OpenApiExample(
                    name="Category Response",
                    summary="Category details with children",
                    description="Full category details with nested children.",
                    value={
                        "id": 1,
                        "organization": 1,
                        "organization_name": "The Makar",
                        "name": "Main Menu",
                        "slug": "main-menu",
                        "description": "All main menu categories including breakfast, lunch and dinner",
                        "parent": None,
                        "parent_name": None,
                        "image": None,
                        "is_active": True,
                        "position": 1,
                        "children": [
                            {
                                "id": 2,
                                "name": "Breakfast",
                                "slug": "breakfast",
                                "description": "All breakfast items including eggs, pancakes and parathas",
                                "parent": 1,
                                "parent_name": "Main Menu",
                                "is_active": True,
                                "position": 1,
                                "children": [],
                                "created_at": "2026-09-06T10:00:00Z",
                                "updated_at": "2026-09-06T10:00:00Z"
                            },
                            {
                                "id": 3,
                                "name": "Lunch",
                                "slug": "lunch",
                                "description": "All lunch items including burgers, pizzas and sandwiches",
                                "parent": 1,
                                "parent_name": "Main Menu",
                                "is_active": True,
                                "position": 2,
                                "children": [],
                                "created_at": "2026-09-06T10:00:00Z",
                                "updated_at": "2026-09-06T10:00:00Z"
                            }
                        ],
                        "created_at": "2026-09-06T10:00:00Z",
                        "updated_at": "2026-09-06T10:00:00Z"
                    }
                )
            ]
        ),
        404: OpenApiResponse(description="Category not found."),
    },
)


# ============================================
# ✅ CATEGORY DELETE SCHEMA
# ============================================

CATEGORY_DELETE_SCHEMA = extend_schema(
    tags=["Categories"],
    summary="Delete Category",
    description="Soft delete a category (cannot delete if it has active products).",
    responses={
        204: OpenApiResponse(
            description="Category deleted successfully."
        ),
        400: OpenApiResponse(
            description="Cannot delete category with active products.",
            examples=[
                OpenApiExample(
                    name="Delete Error",
                    summary="Category has active products",
                    description="Error when trying to delete category with products.",
                    value={
                        "error": "Cannot delete category with active products."
                    }
                )
            ]
        ),
        404: OpenApiResponse(description="Category not found."),
    },
)


# ============================================
# ✅ CATEGORY TREE SCHEMA (GET Tree)
# ============================================

CATEGORY_TREE_SCHEMA = extend_schema(
    tags=["Categories"],
    summary="Get Category Tree",
    description="Get complete category tree with nested children (hierarchy).",
    responses={
        200: OpenApiResponse(
            response=CategoryResponseSchema(many=True),
            description="Category tree retrieved successfully.",
            examples=[
                OpenApiExample(
                    name="Category Tree",
                    summary="Complete category hierarchy",
                    description="Full category tree with all nested categories.",
                    value=[
                        {
                            "id": 1,
                            "name": "Main Menu",
                            "slug": "main-menu",
                            "description": "All main menu categories",
                            "parent": None,
                            "is_active": True,
                            "position": 1,
                            "children": [
                                {
                                    "id": 2,
                                    "name": "Breakfast",
                                    "slug": "breakfast",
                                    "description": "All breakfast items",
                                    "parent": 1,
                                    "is_active": True,
                                    "position": 1,
                                    "children": []
                                },
                                {
                                    "id": 3,
                                    "name": "Lunch",
                                    "slug": "lunch",
                                    "description": "All lunch items",
                                    "parent": 1,
                                    "is_active": True,
                                    "position": 2,
                                    "children": []
                                },
                                {
                                    "id": 4,
                                    "name": "Dinner",
                                    "slug": "dinner",
                                    "description": "All dinner items",
                                    "parent": 1,
                                    "is_active": True,
                                    "position": 3,
                                    "children": []
                                }
                            ]
                        },
                        {
                            "id": 5,
                            "name": "Beverages",
                            "slug": "beverages",
                            "description": "All beverages including cold drinks, juices and shakes",
                            "parent": None,
                            "is_active": True,
                            "position": 2,
                            "children": []
                        },
                        {
                            "id": 6,
                            "name": "Desserts",
                            "slug": "desserts",
                            "description": "All desserts including cakes, pastries and ice cream",
                            "parent": None,
                            "is_active": True,
                            "position": 3,
                            "children": []
                        }
                    ]
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required."),
    },
)


# ============================================
# ✅ CATEGORY REORDER SCHEMA (POST Reorder)
# ============================================

CATEGORY_REORDER_SCHEMA = extend_schema(
    tags=["Categories"],
    summary="Reorder Categories",
    description="Reorder categories by providing list of category IDs in desired order.",
    request=CategoryReorderSchema,
    examples=[
        OpenApiExample(
            name="Reorder Categories",
            summary="Change display order of categories",
            description="Provide category IDs in new order.",
            value={
                "category_ids": [3, 1, 4, 2, 5]
            },
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Categories reordered successfully.",
            examples=[
                OpenApiExample(
                    name="Reorder Success",
                    summary="Categories reordered",
                    description="Success message after reordering.",
                    value={
                        "message": "Categories reordered successfully."
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Validation error.",
            examples=[
                OpenApiExample(
                    name="Missing IDs",
                    summary="category_ids missing",
                    description="Error when category_ids is not provided.",
                    value={
                        "error": "category_ids is required."
                    }
                )
            ]
        ),
    },
)