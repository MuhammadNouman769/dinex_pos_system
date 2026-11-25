from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class CustomerCreateSchema(serializers.Serializer):
    """Schema for creating a customer"""
    location = serializers.IntegerField(help_text="Location ID")
    first_name = serializers.CharField(max_length=100, help_text="First name")
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=100, help_text="Last name")
    phone = serializers.CharField(max_length=20, help_text="Phone number")
    email = serializers.EmailField(required=False, allow_blank=True, help_text="Email")
    address = serializers.CharField(required=False, allow_blank=True, help_text="Address")
    customer_type = serializers.ChoiceField(
        choices=['WALK_IN', 'REGULAR', 'CORPORATE'],
        default='WALK_IN',
        help_text="Customer type"
    )
    notes = serializers.CharField(required=False, allow_blank=True, help_text="Notes")
    is_active = serializers.BooleanField(default=True, help_text="Is active")


class CustomerUpdateSchema(serializers.Serializer):
    """Schema for updating a customer"""
    location = serializers.IntegerField(required=False, help_text="Location ID")
    first_name = serializers.CharField(required=False, max_length=100, help_text="First name")
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=100, help_text="Last name")
    phone = serializers.CharField(required=False, max_length=20, help_text="Phone number")
    email = serializers.EmailField(required=False, allow_blank=True, help_text="Email")
    address = serializers.CharField(required=False, allow_blank=True, help_text="Address")
    customer_type = serializers.ChoiceField(
        choices=['WALK_IN', 'REGULAR', 'CORPORATE'],
        required=False,
        help_text="Customer type"
    )
    notes = serializers.CharField(required=False, allow_blank=True, help_text="Notes")
    is_active = serializers.BooleanField(required=False, help_text="Is active")


class CustomerResponseSchema(serializers.Serializer):
    """Schema for customer response"""
    id = serializers.IntegerField()
    location = serializers.IntegerField()
    location_name = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.CharField(allow_blank=True)
    address = serializers.CharField(allow_blank=True)
    customer_type = serializers.CharField()
    total_orders = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    last_order_at = serializers.DateTimeField(allow_null=True)
    notes = serializers.CharField(allow_blank=True)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


CUSTOMER_LIST_SCHEMA = extend_schema(
    tags=["Customers"],
    summary="List Customers",
    description="Get all customers with optional filtering.",
    parameters=[
        OpenApiParameter(
            name='location',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter by location ID',
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
            description='Search by name or phone',
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=CustomerResponseSchema(many=True),
            description="List of customers"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
)

CUSTOMER_CREATE_SCHEMA = extend_schema(
    tags=["Customers"],
    summary="Create Customer",
    description="Create a new customer.",
    request=CustomerCreateSchema,
    examples=[
        OpenApiExample(
            name="Create Regular Customer",
            summary="Create a regular customer",
            description="Customer who orders frequently.",
            value={
                "location": 4,
                "first_name": "Muhammad",
                "last_name": "Nouman",
                "phone": "03001234567",
                "email": "nouman@example.com",
                "address": "Islamabad, Pakistan",
                "customer_type": "REGULAR",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Walk-in Customer",
            summary="Create a walk-in customer",
            description="Customer visiting the restaurant.",
            value={
                "location": 4,
                "first_name": "Ali",
                "last_name": "Hassan",
                "phone": "03007654321",
                "customer_type": "WALK_IN",
                "is_active": True
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Corporate Customer",
            summary="Create a corporate customer",
            description="Corporate/office customer.",
            value={
                "location": 4,
                "first_name": "Ahmed",
                "last_name": "Raza",
                "phone": "03009876543",
                "email": "ahmed@company.com",
                "address": "Office #5, Blue Area, Islamabad",
                "customer_type": "CORPORATE",
                "notes": "Corporate account - monthly billing",
                "is_active": True
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=CustomerResponseSchema,
            description="Customer created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
)

CUSTOMER_RETRIEVE_SCHEMA = extend_schema(
    tags=["Customers"],
    summary="Retrieve Customer",
    description="Get customer details by ID.",
    responses={
        200: OpenApiResponse(
            response=CustomerResponseSchema,
            description="Customer details"
        ),
        404: OpenApiResponse(description="Customer not found"),
    },
)

CUSTOMER_UPDATE_SCHEMA = extend_schema(
    tags=["Customers"],
    summary="Update Customer",
    description="Update customer details.",
    request=CustomerUpdateSchema,
    responses={
        200: OpenApiResponse(
            response=CustomerResponseSchema,
            description="Customer updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Customer not found"),
    },
)

CUSTOMER_DELETE_SCHEMA = extend_schema(
    tags=["Customers"],
    summary="Delete Customer",
    description="Soft delete a customer.",
    responses={
        204: OpenApiResponse(description="Customer deleted successfully"),
        400: OpenApiResponse(description="Customer has active orders"),
        404: OpenApiResponse(description="Customer not found"),
    },
)