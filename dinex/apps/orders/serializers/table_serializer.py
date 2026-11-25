from rest_framework import serializers
from apps.utils.serializers import OrganizationScopedMixin
from apps.orders.models import Table
from apps.orders.validators import (
    validate_table_number,
    validate_table_capacity,
    validate_table_status_transition,
)


class TableSerializer(OrganizationScopedMixin, serializers.ModelSerializer):
    org_scoped_fields = {"location": "organization_id", "floor": "location__organization_id"}
    location_scoped_fields = {"location": "id", "floor": "location_id"}
    floor_name = serializers.CharField(source='floor.name', read_only=True, default=None)

    """
    Table Serializer
    """
    
    location_name = serializers.CharField(source='location.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Table
        fields = [
            'id',
            'location',
            'location_name',
            'floor',
            'floor_name',
            'table_number',
            'capacity',
            'shape',
            'pos_x',
            'pos_y',
            'status',
            'status_display',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_pos_x(self, v):
        if v is not None and v > 3000:
            raise serializers.ValidationError("Outside the floor plan.")
        return v

    validate_pos_y = validate_pos_x

    def validate_table_number(self, value):
        """Validate table number using validator"""
        return validate_table_number(value)

    def validate_capacity(self, value):
        """Validate capacity using validator"""
        return validate_table_capacity(value)

    def validate_status(self, value):
        """Validate status transition using validator"""
        # Re-sending the current status (e.g. a full PUT) is a no-op, not a transition
        if self.instance and value != self.instance.status:
            validate_table_status_transition(self.instance.status, value)
        return value

    def validate(self, data):
        """Validate table data"""
        # Check if table number already exists at this location
        if 'table_number' in data and 'location' in data:
            table = Table.objects.filter(
                location=data['location'],
                table_number=data['table_number']
            )
            if self.instance:
                table = table.exclude(id=self.instance.id)
            if table.exists():
                raise serializers.ValidationError(
                    f"Table {data['table_number']} already exists at this location."
                )
        return data