from rest_framework import serializers
from apps.utils.serializers import OrganizationScopedMixin
from django.utils import timezone
from apps.orders.models import Order
from apps.orders.serializers.order_item_serializer import OrderItemSerializer
from apps.orders.validators import (
    validate_order_type,
    validate_order_dates,
    validate_order_discount,
    validate_customer_phone_for_order,
    validate_delivery_address_for_order,
)


class OrderSerializer(OrganizationScopedMixin, serializers.ModelSerializer):
    org_scoped_fields = {"location": "organization_id", "customer": "location__organization_id", "table": "location__organization_id", "waiter": "organization_id"}
    location_scoped_fields = {"location": "id", "customer": "location_id", "table": "location_id"}

    """
    Order Serializer with nested items
    """
    
    items = OrderItemSerializer(many=True, read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    customer_name_display = serializers.CharField(source='customer.full_name', read_only=True)
    loyalty = serializers.SerializerMethodField()

    def get_loyalty(self, obj):
        from apps.loyalty.services import order_info
        return order_info(obj)
    waiter_name = serializers.CharField(source='waiter.name', read_only=True, default=None)
    rider_name = serializers.CharField(source='rider.name', read_only=True, default=None)
    
    #  Fix: Add order_type_display for human-readable display
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'location',
            'location_name',
            'customer',
            'customer_name_display',
            'loyalty',
            'waiter',
            'waiter_name',
            'rider',
            'rider_name',
            'dispatched_at',
            'delivered_at',
            'customer_name',
            'customer_phone',
            'delivery_address',
            'order_number',
            'order_type',
            'order_type_display',        
            'table',
            'subtotal',
            'tax',
            'service_charge',
            'discount',
            'total_amount',
            'status',
            'status_display',            
            'payment_status',
            'payment_status_display',    
            'payment_method',
            'payment_method_display',    
            'created_by',
            'confirmed_at',
            'preparing_at',
            'ready_at',
            'completed_at',
            'cancelled_at',
            'estimated_time',
            'notes',
            'items',
            'is_active',
            'is_offline',
            'client_uuid',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'is_offline', 'client_uuid',
            'id', 'order_number', 'subtotal', 'tax', 'service_charge', 'total_amount',
            'confirmed_at', 'preparing_at', 'ready_at', 'completed_at',
            'cancelled_at', 'created_at', 'updated_at',
            # Set by the server only (state machine / payment module / request.user)
            'status', 'payment_status', 'created_by',
            'rider', 'dispatched_at', 'delivered_at',
        ]

    def validate_order_type(self, value):
        """Validate order type using validator"""
        # Get table and delivery_address from data
        table = self.initial_data.get('table', self.instance.table_id if self.instance else None)
        delivery_address = self.initial_data.get(
            'delivery_address', self.instance.delivery_address if self.instance else None
        )
        validate_order_type(value, table, delivery_address)
        return value

    def validate_discount(self, value):
        """Validate discount using validator"""
        subtotal = self.instance.subtotal if self.instance else 0
        return validate_order_discount(value, subtotal)

    def validate_customer_phone(self, value):
        """Validate customer phone using validator"""
        order_type = self.initial_data.get('order_type')
        return validate_customer_phone_for_order(value, order_type)

    def validate_delivery_address(self, value):
        """Validate delivery address using validator"""
        if value:
            return validate_delivery_address_for_order(value)
        return value

    def validate(self, data):
        waiter = data.get('waiter')
        if waiter is not None:
            loc = data.get('location') or (self.instance.location if self.instance else None)
            if waiter.location_id != getattr(loc, 'id', None):
                raise serializers.ValidationError({"waiter": "This waiter works at a different branch."})
            if not waiter.is_active or waiter.role not in ("WAITER", "MANAGER", "CASHIER"):
                raise serializers.ValidationError({"waiter": "Choose an active waiter."})
        discount = data.get('discount')
        if discount and discount > 0 and (self.instance is None or discount != self.instance.discount):
            from apps.utils.helpers import is_manager_or_owner
            request = self.context.get('request')
            location = data.get('location') or (self.instance.location if self.instance else None)
            if request is not None and location is not None and not is_manager_or_owner(request, location):
                raise serializers.ValidationError({"discount": "Only a manager or the owner can give a discount."})
        """Validate order data"""
        # Validate order type requirements
        order_type = data.get('order_type', self.instance.order_type if self.instance else None)
        table = data.get('table', self.instance.table if self.instance else None)
        delivery_address = data.get('delivery_address', self.instance.delivery_address if self.instance else None)
        
        validate_order_type(order_type, table, delivery_address)
        
        # Validate dates
        created_at = data.get('created_at')
        if created_at and created_at > timezone.now():
            raise serializers.ValidationError(
                "Order cannot be created in the future."
            )
        
        return data

    def create(self, validated_data):
        """Create order with auto-generated order number"""
        location = validated_data.get('location')
        
        # Generate order number (retry if two requests race for the same number)
        from django.db import IntegrityError, transaction
        from apps.orders.utils import generate_order_number

        request = self.context.get('request')
        if request is not None and request.user.is_authenticated:
            validated_data['created_by'] = request.user

        last_error = None
        for _ in range(5):
            validated_data['order_number'] = generate_order_number(location.id)
            try:
                with transaction.atomic():
                    order = super().create(validated_data)
                    if order.discount > 0:
                        from apps.cash.services import audit
                        audit(request.user if request else None, order.location, "discount", order,
                              order_number=order.order_number, discount=order.discount)
                    table = order.table
                    if table is not None and table.status != 'OCCUPIED':
                        table.status = 'OCCUPIED'
                        table.save(update_fields=['status', 'updated_at'])
                    return order
            except IntegrityError as exc:
                last_error = exc
        raise last_error

    def update(self, instance, validated_data):
        old_discount = instance.discount
        instance = super().update(instance, validated_data)
        if 'discount' in validated_data:
            instance.calculate_totals()
            if instance.discount != old_discount:
                from apps.cash.services import audit
                request = self.context.get('request')
                audit(request.user if request else None, instance.location, "discount", instance,
                      order_number=instance.order_number, discount=instance.discount, was=old_discount)
        return instance
