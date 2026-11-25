from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class ModifierOptionCreateSchema(serializers.Serializer):
    """Schema for creating a modifier option"""
    modifier_group = serializers.IntegerField(help_text="Modifier group ID")
    name = serializers.CharField(max_length=255, help_text="Option name")
    price_adjustment = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Price adjustment")
    position = serializers.IntegerField(default=0, help_text="Display position")
    is_active = serializers.BooleanField(default=True, help_text="Is option active")


class ModifierOptionUpdateSchema(serializers.Serializer):
    """Schema for updating a modifier option"""
    modifier_group = serializers.IntegerField(required=False, help_text="Modifier group ID")
    name = serializers.CharField(max_length=255, required=False, help_text="Option name")
    price_adjustment = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, help_text="Price adjustment")
    position = serializers.IntegerField(required=False, help_text="Display position")
    is_active = serializers.BooleanField(required=False, help_text="Is option active")


class ModifierOptionResponseSchema(serializers.Serializer):
    """Schema for modifier option response"""
    id = serializers.IntegerField()
    modifier_group = serializers.IntegerField()
    group_name = serializers.CharField()
    name = serializers.CharField()
    price_adjustment = serializers.DecimalField(max_digits=12, decimal_places=2)
    position = serializers.IntegerField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ModifierOptionReorderSchema(serializers.Serializer):
    """Schema for reordering modifier options"""
    modifier_group_id = serializers.IntegerField(help_text="Modifier group ID")
    option_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of option IDs in desired order"
    )


MODIFIER_OPTION_LIST_SCHEMA = extend_schema(
    summary="List Modifier Options",
    description="Get all modifier options for the user's organization",
    parameters=[
        OpenApiParameter(
            name='modifier_group',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by modifier group ID',
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
            description='Search options by name',
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ModifierOptionResponseSchema(many=True),
            description="List of modifier options"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Modifier Options'],
)

MODIFIER_OPTION_CREATE_SCHEMA = extend_schema(
    summary="Create Modifier Option",
    description="Create a new modifier option for a group",
    request=ModifierOptionCreateSchema,
    responses={
        201: OpenApiResponse(
            response=ModifierOptionResponseSchema,
            description="Modifier option created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
    tags=['Modifier Options'],
)

MODIFIER_OPTION_RETRIEVE_SCHEMA = extend_schema(
    summary="Retrieve Modifier Option",
    description="Get modifier option details by ID",
    responses={
        200: OpenApiResponse(
            response=ModifierOptionResponseSchema,
            description="Modifier option details"
        ),
        404: OpenApiResponse(description="Modifier option not found"),
    },
    tags=['Modifier Options'],
)

MODIFIER_OPTION_UPDATE_SCHEMA = extend_schema(
    summary="Update Modifier Option",
    description="Update modifier option details",
    request=ModifierOptionUpdateSchema,
    responses={
        200: OpenApiResponse(
            response=ModifierOptionResponseSchema,
            description="Modifier option updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Modifier option not found"),
    },
    tags=['Modifier Options'],
)

MODIFIER_OPTION_DELETE_SCHEMA = extend_schema(
    summary="Delete Modifier Option",
    description="Soft delete a modifier option",
    responses={
        204: OpenApiResponse(description="Modifier option deleted successfully"),
        404: OpenApiResponse(description="Modifier option not found"),
    },
    tags=['Modifier Options'],
)

MODIFIER_OPTION_REORDER_SCHEMA = extend_schema(
    summary="Reorder Modifier Options",
    description="Reorder modifier options within a group",
    request=ModifierOptionReorderSchema,
    responses={
        200: OpenApiResponse(
            response={"message": "Options reordered successfully."},
            description="Options reordered"
        ),
        400: OpenApiResponse(description="Validation error"),
    },
    tags=['Modifier Options'],
)