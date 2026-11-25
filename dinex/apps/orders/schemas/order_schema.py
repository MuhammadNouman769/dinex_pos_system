from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes


class OrderItemInlineSchema(serializers.Serializer):
    """Schema for inline order item"""
    product_variant = serializers.IntegerField(help_text="Product variant ID")
    quantity = serializers.IntegerField(default=1, help_text="Quantity")
    notes = serializers.CharField(required=False, allow_blank=True, help_text="Special instructions")


class OrderCreateSchema(serializers.Serializer):
    """Schema for creating an order"""
    location = serializers.IntegerField(help_text="Location ID")
    customer = serializers.IntegerField(required=False, allow_null=True, help_text="Customer ID")
    customer_name = serializers.CharField(required=False, allow_blank=True, help_text="Customer name")
    customer_phone = serializers.CharField(required=False, allow_blank=True, help_text="Customer phone")
    delivery_address = serializers.CharField(required=False, allow_blank=True, help_text="Delivery address")
    order_type = serializers.ChoiceField(
        choices=['DINE_IN', 'TAKEAWAY', 'DELIVERY'],
        help_text="Order type"
    )
    table = serializers.IntegerField(required=False, allow_null=True, help_text="Table ID for Dine In")
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Discount")
    payment_method = serializers.ChoiceField(
        choices=['CASH', 'CARD', 'ONLINE', 'COD'],
        required=False,
        help_text="Payment method"
    )
    estimated_time = serializers.IntegerField(default=30, help_text="Estimated preparation time")
    notes = serializers.CharField(required=False, allow_blank=True, help_text="Additional notes")


class OrderUpdateSchema(serializers.Serializer):
    """Schema for updating an order"""
    location = serializers.IntegerField(required=False, help_text="Location ID")
    customer = serializers.IntegerField(required=False, allow_null=True, help_text="Customer ID")
    customer_name = serializers.CharField(required=False, allow_blank=True, help_text="Customer name")
    customer_phone = serializers.CharField(required=False, allow_blank=True, help_text="Customer phone")
    delivery_address = serializers.CharField(required=False, allow_blank=True, help_text="Delivery address")
    order_type = serializers.ChoiceField(
        choices=['DINE_IN', 'TAKEAWAY', 'DELIVERY'],
        required=False,
        help_text="Order type"
    )
    table = serializers.IntegerField(required=False, allow_null=True, help_text="Table ID for Dine In")
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, help_text="Discount")
    payment_method = serializers.ChoiceField(
        choices=['CASH', 'CARD', 'ONLINE', 'COD'],
        required=False,
        help_text="Payment method"
    )
    estimated_time = serializers.IntegerField(required=False, help_text="Estimated preparation time")
    notes = serializers.CharField(required=False, allow_blank=True, help_text="Additional notes")


class OrderStatusUpdateSchema(serializers.Serializer):
    """Schema for updating order status"""
    status = serializers.ChoiceField(
        choices=['PENDING', 'CONFIRMED', 'PREPARING', 'READY', 'OUT_FOR_DELIVERY', 'COMPLETED', 'CANCELLED'],
        help_text="New order status"
    )


class OrderResponseSchema(serializers.Serializer):
    """Schema for order response"""
    id = serializers.IntegerField()
    location = serializers.IntegerField()
    location_name = serializers.CharField()
    customer = serializers.IntegerField(allow_null=True)
    customer_name_display = serializers.CharField()
    customer_name = serializers.CharField(allow_blank=True)
    customer_phone = serializers.CharField(allow_blank=True)
    delivery_address = serializers.CharField(allow_blank=True)
    order_number = serializers.CharField()
    order_type = serializers.CharField()
    table = serializers.IntegerField(allow_null=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    payment_status = serializers.CharField()
    payment_method = serializers.CharField(allow_blank=True)
    created_by = serializers.IntegerField(allow_null=True)
    confirmed_at = serializers.DateTimeField(allow_null=True)
    preparing_at = serializers.DateTimeField(allow_null=True)
    ready_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    cancelled_at = serializers.DateTimeField(allow_null=True)
    estimated_time = serializers.IntegerField()
    notes = serializers.CharField(allow_blank=True)
    items = serializers.ListField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


ORDER_LIST_SCHEMA = extend_schema(
    tags=["Orders"],
    summary="List Orders",
    description="Get all orders with optional filtering.",
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
            name='search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Search by order number or customer name',
        ),
        OpenApiParameter(
            name='date',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Date range (YYYY-MM-DD,YYYY-MM-DD)',
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
            response=OrderResponseSchema(many=True),
            description="List of orders"
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
)

ORDER_CREATE_SCHEMA = extend_schema(
    tags=["Orders"],
    summary="Create Order",
    description="Create a new order.",
    request=OrderCreateSchema,
    examples=[
        OpenApiExample(
            name="Create Dine In Order",
            summary="Create a dine in order",
            description="Order at table T-5.",
            value={
                "location": 4,
                "customer": 1,
                "order_type": "DINE_IN",
                "table": 1,
                "payment_method": "CASH",
                "estimated_time": 20,
                "notes": "Extra napkins"
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Takeaway Order",
            summary="Create a takeaway order",
            description="Customer picking up food.",
            value={
                "location": 4,
                "customer_name": "Ali Hassan",
                "customer_phone": "03007654321",
                "order_type": "TAKEAWAY",
                "payment_method": "CARD",
                "estimated_time": 15,
                "notes": "Call when ready"
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Create Delivery Order",
            summary="Create a delivery order",
            description="Customer called for delivery.",
            value={
                "location": 4,
                "customer_name": "Muhammad Nouman",
                "customer_phone": "03001234567",
                "delivery_address": "House #5, Street 12, Islamabad",
                "order_type": "DELIVERY",
                "payment_method": "COD",
                "estimated_time": 30,
                "notes": "Call before delivery"
            },
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            response=OrderResponseSchema,
            description="Order created successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        401: OpenApiResponse(description="Authentication required"),
    },
)

ORDER_RETRIEVE_SCHEMA = extend_schema(
    tags=["Orders"],
    summary="Retrieve Order",
    description="Get order details by ID.",
    responses={
        200: OpenApiResponse(
            response=OrderResponseSchema,
            description="Order details"
        ),
        404: OpenApiResponse(description="Order not found"),
    },
)

ORDER_UPDATE_SCHEMA = extend_schema(
    tags=["Orders"],
    summary="Update Order",
    description="Update order details.",
    request=OrderUpdateSchema,
    responses={
        200: OpenApiResponse(
            response=OrderResponseSchema,
            description="Order updated successfully"
        ),
        400: OpenApiResponse(description="Validation error"),
        404: OpenApiResponse(description="Order not found"),
    },
)

ORDER_DELETE_SCHEMA = extend_schema(
    tags=["Orders"],
    summary="Delete Order",
    description="Soft delete an order.",
    responses={
        204: OpenApiResponse(description="Order deleted successfully"),
        400: OpenApiResponse(description="Cannot delete completed orders"),
        404: OpenApiResponse(description="Order not found"),
    },
)

ORDER_STATUS_UPDATE_SCHEMA = extend_schema(
    tags=["Orders"],
    summary="Update Order Status",
    description="Update order status with timestamp.",
    request=OrderStatusUpdateSchema,
    examples=[
        OpenApiExample(
            name="Confirm Order",
            summary="Confirm order",
            description="Accept the order.",
            value={
                "status": "CONFIRMED"
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Start Preparing",
            summary="Start preparing order",
            description="Kitchen started preparing.",
            value={
                "status": "PREPARING"
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Mark Ready",
            summary="Mark order ready",
            description="Food is ready.",
            value={
                "status": "READY"
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Complete Order",
            summary="Complete order",
            description="Order is completed.",
            value={
                "status": "COMPLETED"
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Cancel Order",
            summary="Cancel order",
            description="Order is cancelled.",
            value={
                "status": "CANCELLED"
            },
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Order status updated",
            examples=[
                OpenApiExample(
                    name="Success",
                    value={
                        "id": 1,
                        "order_number": "ORD-20260908-0042",
                        "status": "CONFIRMED",
                        "message": "Order status updated to CONFIRMED"
                    }
                )
            ]
        ),
        400: OpenApiResponse(description="Invalid status transition"),
        404: OpenApiResponse(description="Order not found"),
    },
)

ORDER_STATS_SCHEMA = extend_schema(
    tags=["Orders"],
    summary="Get Order Statistics",
    description="Get order statistics for dashboard.",
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
            description="Order statistics",
            examples=[
                OpenApiExample(
                    name="Stats",
                    value={
                        "total_orders": 150,
                        "total_amount": "150000.00",
                        "today_orders": 25,
                        "pending_orders": 5,
                        "preparing_orders": 8,
                        "ready_orders": 3,
                        "completed_orders": 9,
                        "cancelled_orders": 0
                    }
                )
            ]
        ),
        401: OpenApiResponse(description="Authentication required"),
    },
)