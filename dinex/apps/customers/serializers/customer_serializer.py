from rest_framework import serializers
from apps.utils.serializers import OrganizationScopedMixin
from apps.customers.models.customer import Customer
from apps.customers.validators import (
    validate_customer_phone,
    validate_customer_email,
    validate_customer_name,
    validate_customer_address,
    validate_customer_type,
)


class CustomerSerializer(OrganizationScopedMixin, serializers.ModelSerializer):
    org_scoped_fields = {"location": "organization_id"}
    location_scoped_fields = {"location": "id"}

    """
    Customer Serializer
    """
    
    full_name = serializers.CharField(read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id',
            'location',
            'location_name',
            'first_name',
            'last_name',
            'full_name',
            'phone',
            'email',
            'address',
            'customer_type',
            'points_balance',
            'total_orders',
            'total_spent',
            'last_order_at',
            'notes',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'points_balance', 'total_orders', 'total_spent', 'last_order_at', 'created_at', 'updated_at']
        extra_kwargs = {
            'phone': {'required': True},
            'first_name': {'required': True},
        }

    def validate_phone(self, value):
        """Validate phone number using validator"""
        return validate_customer_phone(value)

    def validate_email(self, value):
        """Validate email using validator"""
        return validate_customer_email(value)

    def validate_first_name(self, value):
        """Validate first name using validator"""
        return validate_customer_name(value, "First name")

    def validate_last_name(self, value):
        """Validate last name using validator"""
        if value:
            return validate_customer_name(value, "Last name")
        return value

    def validate_address(self, value):
        """Validate address using validator"""
        return validate_customer_address(value)

    def validate_customer_type(self, value):
        """Validate customer type using validator"""
        return validate_customer_type(value)

    def validate(self, data):
        """Validate customer data (object-level validation)"""
        # Check if customer with same phone exists at same location
        if 'phone' in data and 'location' in data:
            customer = Customer.objects.filter(
                location=data['location'],
                phone=data['phone']
            )
            if self.instance:
                customer = customer.exclude(id=self.instance.id)
            if customer.exists():
                raise serializers.ValidationError(
                    "Customer with this phone already exists at this location."
                )
        return data