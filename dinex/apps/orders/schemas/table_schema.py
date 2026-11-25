from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class TableCreateSchema(serializers.Serializer):
    """Schema for creating a table"""
    location = serializers.IntegerField(help_text="Location ID")
    table_number = serializers.CharField(max_length=20, help_text="Table number (e.g., T-1)")
    capacity = serializers.IntegerField(default=2, help_text="Seating capacity")
    status = serializers.ChoiceField(
        choices=['AVAILABLE', 'OCCUPIED', 'RESERVED', 'CLEANING'],
        default='AVAILABLE',
        help_text="Table status"
    )
    is_active = serializers.BooleanField(default=True, help_text="Is active")


class TableUpdateSchema(serializers.Serializer):
    """Schema for updating a table"""
    location = serializers.IntegerField(required=False, help_text="Location ID")
    table_number = serializers.CharField(required=False, max_length=20, help_text="Table number")
    capacity = serializers.IntegerField(required=False, help_text="Seating capacity")
    status = serializers.ChoiceField(
        choices=['AVAILABLE', 'OCCUPIED', 'RESERVED', 'CLEANING'],
        required=False,
        help_text="Table status"
    )
    is_active = serializers.BooleanField(required=False, help_text="Is active")


class TableResponseSchema(serializers.Serializer):
    """Schema for table response"""
    id = serializers.IntegerField()
    location = serializers.IntegerField()
    location_name = serializers.CharField()
    table_number = serializers.CharField()
    capacity = serializers.IntegerField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


TABLE_LIST_SCHEMA = extend_schema(
    tags=["Tables"],
    summary="List Tables",
    description="Get all tables with optional filtering.",
    parameters=[
        OpenApiParameter(
            name='location',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by location ID',
        ),
        OpenApiParameter(
            name='status',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter by status',
        ),
        OpenApiParameter(
            name='available',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Get only available tables',
            default=False,
        ),
        OpenApiParameter(
            name='active',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description='Filter by active status',
            default=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=TableResponseSchema(many=True),
            description="List of tables"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
)

TABLE_CREATE_SCHEMA = extend_schema(
    tags=["Tables"],
    summary="Create Table",
    description="Create a new table.",
    request=TableCreateSchema,
    examples=[
        OpenApiExample(
            name="Create Table",
            summary="Create a new table",
            description="Add a table to a location.",
            value={
                "location": 4,
                "table_number": "T-1",
                "capacity": 4,
                "status": "AVAILABLE",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Multiple Tables",
            summary="Create multiple tables",
            description="Add multiple tables to a location.",
            value={
                "location": 4,
                "table_number": "T-2",
                "capacity": 2,
                "status": "AVAILABLE",
                "is_active": True
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=TableResponseSchema,
            description="Table created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
)

TABLE_RETRIEVE_SCHEMA = extend_schema(
    tags=["Tables"],
    summary="Retrieve Table",
    description="Get table details by ID.",
    responses={
        200: OpenApiResponse(
            response=TableResponseSchema,
            description="Table details"
        ),
        404: OpenApiResponse(description="Table not found"),
    },
)

TABLE_UPDATE_SCHEMA = extend_schema(
    tags=["Tables"],
    summary="Update Table",
    description="Update table details.",
    request=TableUpdateSchema,
    responses={
        200: OpenApiResponse(
            response=TableResponseSchema,
            description="Table updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Table not found"),
    },
)

TABLE_DELETE_SCHEMA = extend_schema(
    tags=["Tables"],
    summary="Delete Table",
    description="Soft delete a table.",
    responses={
        204: OpenApiResponse(description="Table deleted successfully"),
        400: OpenApiResponse(description="Cannot delete table with active orders"),
        404: OpenApiResponse(description="Table not found"),
    },
)

TABLE_OCCUPY_SCHEMA = extend_schema(
    tags=["Tables"],
    summary="Occupy Table",
    description="Mark a table as occupied.",
    responses={
        200: OpenApiResponse(
            description="Table occupied",
            examples=[
                OpenApiExample(
                    name="Success",
                    value={
                        "id": 1,
                        "table_number": "T-1",
                        "status": "OCCUPIED",
                        "message": "Table T-1 is now occupied."
                    }
                )
            ]
        ),
        400: OpenApiResponse(description="Table not available"),
        404: OpenApiResponse(description="Table not found"),
    },
)

TABLE_FREE_SCHEMA = extend_schema(
    tags=["Tables"],
    summary="Free Table",
    description="Mark a table as available.",
    responses={
        200: OpenApiResponse(
            description="Table freed",
            examples=[
                OpenApiExample(
                    name="Success",
                    value={
                        "id": 1,
                        "table_number": "T-1",
                        "status": "AVAILABLE",
                        "message": "Table T-1 is now available."
                    }
                )
            ]
        ),
        400: OpenApiResponse(description="Table not occupied"),
        404: OpenApiResponse(description="Table not found"),
    },
)

TABLE_AVAILABLE_SCHEMA = extend_schema(
    tags=["Tables"],
    summary="Get Available Tables",
    description="Get all available tables.",
    parameters=[
        OpenApiParameter(
            name='location',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by location ID',
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=TableResponseSchema(many=True),
            description="List of available tables"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
)