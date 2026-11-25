from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


# ============================================
# REQUEST SCHEMAS (WITHOUT example)
# ============================================

class DietaryTagCreateSchema(serializers.Serializer):
    """Schema for creating a dietary tag"""
    name = serializers.CharField(
        max_length=100, 
        help_text="Dietary tag name"
        # ❌ example="Vegetarian" - Hataayein
    )
    slug = serializers.SlugField(
        max_length=100, 
        help_text="Dietary tag slug (unique per organization)"
        # ❌ example="vegetarian" - Hataayein
    )
    is_active = serializers.BooleanField(
        default=True, 
        help_text="Is tag active"
        # ❌ example=True - Hataayein
    )


class DietaryTagUpdateSchema(serializers.Serializer):
    """Schema for updating a dietary tag"""
    name = serializers.CharField(
        max_length=100, 
        required=False, 
        help_text="Dietary tag name"
        # ❌ example="Vegan" - Hataayein
    )
    slug = serializers.SlugField(
        max_length=100, 
        required=False, 
        help_text="Dietary tag slug"
        # ❌ example="vegan" - Hataayein
    )
    is_active = serializers.BooleanField(
        required=False, 
        help_text="Is tag active"
        # ❌ example=True - Hataayein
    )


# ============================================
# RESPONSE SCHEMAS
# ============================================

class DietaryTagResponseSchema(serializers.Serializer):
    """Schema for dietary tag response"""
    id = serializers.IntegerField(help_text="Dietary tag ID")
    organization = serializers.IntegerField(help_text="Organization ID")
    organization_name = serializers.CharField(help_text="Organization name")
    name = serializers.CharField(help_text="Dietary tag name")
    slug = serializers.CharField(help_text="Dietary tag slug")
    is_active = serializers.BooleanField(help_text="Is tag active")
    created_at = serializers.DateTimeField(help_text="Created timestamp")
    updated_at = serializers.DateTimeField(help_text="Updated timestamp")


# ============================================
# LIST SCHEMA (GET)
# ============================================

DIETARY_TAG_LIST_SCHEMA = extend_schema(
    summary="List Dietary Tags",
    description="Get all dietary tags for the user's organization",
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
            description='Search tags by name',
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=DietaryTagResponseSchema(many=True),
            description="List of dietary tags retrieved successfully"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Dietary Tags'],
)


# ============================================
# CREATE SCHEMA (POST) - WITH DUMMY DATA VIA EXAMPLES
# ============================================

DIETARY_TAG_CREATE_SCHEMA = extend_schema(
    summary="Create Dietary Tag",
    description="Create a new dietary tag for the user's organization",
    request=DietaryTagCreateSchema,
    examples=[
        OpenApiExample(
            name="Create Vegetarian Tag",
            summary="Create a vegetarian dietary tag",
            description="Common dietary tag for vegetarian items.",
            value={
                "name": "Vegetarian",
                "slug": "vegetarian",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Vegan Tag",
            summary="Create a vegan dietary tag",
            description="Dietary tag for vegan items.",
            value={
                "name": "Vegan",
                "slug": "vegan",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Gluten Free Tag",
            summary="Create a gluten free dietary tag",
            description="Dietary tag for gluten free items.",
            value={
                "name": "Gluten Free",
                "slug": "gluten-free",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Spicy Tag",
            summary="Create a spicy dietary tag",
            description="Dietary tag for spicy items.",
            value={
                "name": "Spicy",
                "slug": "spicy",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Halal Tag",
            summary="Create a halal dietary tag",
            description="Dietary tag for halal items.",
            value={
                "name": "Halal",
                "slug": "halal",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Dairy Free Tag",
            summary="Create a dairy free dietary tag",
            description="Dietary tag for dairy free items.",
            value={
                "name": "Dairy Free",
                "slug": "dairy-free",
                "is_active": True
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=DietaryTagResponseSchema,
            description="Dietary tag created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Dietary Tags'],
)


# ============================================
# RETRIEVE SCHEMA (GET by ID)
# ============================================

DIETARY_TAG_RETRIEVE_SCHEMA = extend_schema(
    summary="Retrieve Dietary Tag",
    description="Get dietary tag details by ID",
    responses={
        200: OpenApiResponse(
            response=DietaryTagResponseSchema,
            description="Dietary tag details retrieved successfully"
        ),
        404: OpenApiResponse(description="Dietary tag not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Dietary Tags'],
)


# ============================================
# UPDATE SCHEMA (PUT/PATCH)
# ============================================

DIETARY_TAG_UPDATE_SCHEMA = extend_schema(
    summary="Update Dietary Tag",
    description="Update dietary tag details (full or partial)",
    request=DietaryTagUpdateSchema,
    examples=[
        OpenApiExample(
            name="Update Tag Name",
            summary="Update dietary tag name",
            description="Change the name of a dietary tag.",
            value={
                "name": "Vegan",
                "slug": "vegan",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Deactivate Tag",
            summary="Deactivate a dietary tag",
            description="Set tag as inactive.",
            value={
                "is_active": False
            },
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=DietaryTagResponseSchema,
            description="Dietary tag updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Dietary tag not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Dietary Tags'],
)


# ============================================
# DELETE SCHEMA (DELETE)
# ============================================

DIETARY_TAG_DELETE_SCHEMA = extend_schema(
    summary="Delete Dietary Tag",
    description="Soft delete a dietary tag (cannot delete if used by active products)",
    responses={
        204: OpenApiResponse(description="Dietary tag deleted successfully"),
        400: OpenApiResponse(
            description="Cannot delete tag used by active products"
        ),
        404: OpenApiResponse(description="Dietary tag not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Dietary Tags'],
)

# ============================================
# CREATE SCHEMA (POST) - WITH DUMMY DATA
# ============================================

DIETARY_TAG_CREATE_SCHEMA = extend_schema(
    summary="Create Dietary Tag",
    description="Create a new dietary tag for the user's organization",
    request=DietaryTagCreateSchema,
    examples=[
        OpenApiExample(
            name="Create Vegetarian Tag",
            summary="Create a vegetarian dietary tag",
            description="Common dietary tag for vegetarian items.",
            value={
                "name": "Vegetarian",
                "slug": "vegetarian",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Vegan Tag",
            summary="Create a vegan dietary tag",
            description="Dietary tag for vegan items.",
            value={
                "name": "Vegan",
                "slug": "vegan",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Gluten Free Tag",
            summary="Create a gluten free dietary tag",
            description="Dietary tag for gluten free items.",
            value={
                "name": "Gluten Free",
                "slug": "gluten-free",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Spicy Tag",
            summary="Create a spicy dietary tag",
            description="Dietary tag for spicy items.",
            value={
                "name": "Spicy",
                "slug": "spicy",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Halal Tag",
            summary="Create a halal dietary tag",
            description="Dietary tag for halal items.",
            value={
                "name": "Halal",
                "slug": "halal",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Dairy Free Tag",
            summary="Create a dairy free dietary tag",
            description="Dietary tag for dairy free items.",
            value={
                "name": "Dairy Free",
                "slug": "dairy-free",
                "is_active": True
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=DietaryTagResponseSchema,
            description="Dietary tag created successfully",
            examples=[
                OpenApiExample(
                    name="Create Success",
                    summary="Dietary tag created",
                    description="Successful creation response.",
                    value={
                        "id": 1,
                        "organization": 4,
                        "organization_name": "Yasir Broast",
                        "name": "Vegetarian",
                        "slug": "vegetarian",
                        "is_active": True,
                        "created_at": "2026-09-06T17:30:00Z",
                        "updated_at": "2026-09-06T17:30:00Z"
                    }
                )
            ]
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Dietary Tags'],
)


# ============================================
# RETRIEVE SCHEMA (GET by ID)
# ============================================

DIETARY_TAG_RETRIEVE_SCHEMA = extend_schema(
    summary="Retrieve Dietary Tag",
    description="Get dietary tag details by ID",
    responses={
        200: OpenApiResponse(
            response=DietaryTagResponseSchema,
            description="Dietary tag details retrieved successfully",
            examples=[
                OpenApiExample(
                    name="Retrieve Success",
                    summary="Dietary tag details",
                    description="Full dietary tag details.",
                    value={
                        "id": 1,
                        "organization": 4,
                        "organization_name": "Yasir Broast",
                        "name": "Vegetarian",
                        "slug": "vegetarian",
                        "is_active": True,
                        "created_at": "2026-09-06T17:30:00Z",
                        "updated_at": "2026-09-06T17:30:00Z"
                    }
                )
            ]
        ),
        404: OpenApiResponse(description="Dietary tag not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Dietary Tags'],
)


# ============================================
# UPDATE SCHEMA (PUT/PATCH)
# ============================================

DIETARY_TAG_UPDATE_SCHEMA = extend_schema(
    summary="Update Dietary Tag",
    description="Update dietary tag details (full or partial)",
    request=DietaryTagUpdateSchema,
    examples=[
        OpenApiExample(
            name="Update Tag Name",
            summary="Update dietary tag name",
            description="Change the name of a dietary tag.",
            value={
                "name": "Vegan",
                "slug": "vegan",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Deactivate Tag",
            summary="Deactivate a dietary tag",
            description="Set tag as inactive.",
            value={
                "is_active": False
            },
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=DietaryTagResponseSchema,
            description="Dietary tag updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Dietary tag not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Dietary Tags'],
)


# ============================================
# DELETE SCHEMA (DELETE)
# ============================================

DIETARY_TAG_DELETE_SCHEMA = extend_schema(
    summary="Delete Dietary Tag",
    description="Soft delete a dietary tag (cannot delete if used by active products)",
    responses={
        204: OpenApiResponse(description="Dietary tag deleted successfully"),
        400: OpenApiResponse(
            description="Cannot delete tag used by active products",
            examples=[
                OpenApiExample(
                    name="Delete Error",
                    summary="Tag in use",
                    description="Error when trying to delete a tag used by products.",
                    value={
                        "error": "Cannot delete dietary tag that is used by active products."
                    }
                )
            ]
        ),
        404: OpenApiResponse(description="Dietary tag not found"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Dietary Tags'],
)