from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    inline_serializer,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class ModifierOptionInlineSchema(serializers.Serializer):
    """Schema for inline modifier option"""
    name = serializers.CharField(max_length=255, help_text="Option name")
    price_adjustment = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Price adjustment")
    position = serializers.IntegerField(default=0, help_text="Display position")
    is_active = serializers.BooleanField(default=True, help_text="Is option active")


class ModifierGroupCreateSchema(serializers.Serializer):
    """Schema for creating a modifier group"""
    name = serializers.CharField(max_length=255, help_text="Modifier group name")
    description = serializers.CharField(required=False, allow_blank=True, help_text="Modifier group description")
    min_selections = serializers.IntegerField(default=0, help_text="Minimum selections required")
    max_selections = serializers.IntegerField(default=1, help_text="Maximum selections allowed")
    is_required = serializers.BooleanField(default=False, help_text="Is group required")
    is_active = serializers.BooleanField(default=True, help_text="Is group active")
    options = serializers.ListField(
        child=ModifierOptionInlineSchema(),
        required=False,
        help_text="List of options to create with the group"
    )


class ModifierGroupUpdateSchema(serializers.Serializer):
    """Schema for updating a modifier group"""
    name = serializers.CharField(max_length=255, required=False, help_text="Modifier group name")
    description = serializers.CharField(required=False, allow_blank=True, help_text="Modifier group description")
    min_selections = serializers.IntegerField(required=False, help_text="Minimum selections required")
    max_selections = serializers.IntegerField(required=False, help_text="Maximum selections allowed")
    is_required = serializers.BooleanField(required=False, help_text="Is group required")
    is_active = serializers.BooleanField(required=False, help_text="Is group active")


class ModifierGroupResponseSchema(serializers.Serializer):
    """Schema for modifier group response"""
    id = serializers.IntegerField()
    organization = serializers.IntegerField()
    organization_name = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    min_selections = serializers.IntegerField()
    max_selections = serializers.IntegerField()
    is_required = serializers.BooleanField()
    is_active = serializers.BooleanField()
    options = serializers.ListField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


MODIFIER_GROUP_LIST_SCHEMA = extend_schema(
    summary="List Modifier Groups",
    description="Get all modifier groups for the user's organization",
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
            description='Search groups by name or description',
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ModifierGroupResponseSchema(many=True),
            description="List of modifier groups"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Modifier Groups'],
)

MODIFIER_GROUP_CREATE_SCHEMA = extend_schema(
    summary="Create Modifier Group",
    description="Create a new modifier group with optional options",
    request=ModifierGroupCreateSchema,
    responses={
        201: OpenApiResponse(
            response=ModifierGroupResponseSchema,
            description="Modifier group created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Modifier Groups'],
)

MODIFIER_GROUP_RETRIEVE_SCHEMA = extend_schema(
    summary="Retrieve Modifier Group",
    description="Get modifier group details by ID with all options",
    responses={
        200: OpenApiResponse(
            response=ModifierGroupResponseSchema,
            description="Modifier group details"
        ),
        404: OpenApiResponse(description="Modifier group not found"),
    },
    tags=['Modifier Groups'],
)

MODIFIER_GROUP_UPDATE_SCHEMA = extend_schema(
    summary="Update Modifier Group",
    description="Update modifier group details and options",
    request=ModifierGroupUpdateSchema,
    responses={
        200: OpenApiResponse(
            response=ModifierGroupResponseSchema,
            description="Modifier group updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Modifier group not found"),
    },
    tags=['Modifier Groups'],
)

MODIFIER_GROUP_DELETE_SCHEMA = extend_schema(
    summary="Delete Modifier Group",
    description="Soft delete a modifier group (cannot delete if linked to active products)",
    responses={
        204: OpenApiResponse(description="Modifier group deleted successfully"),
        400: OpenApiResponse(description="Cannot delete group linked to active products"),
        404: OpenApiResponse(description="Modifier group not found"),
    },
    tags=['Modifier Groups'],
)