from rest_framework import serializers
from django.utils import timezone

from apps.catalog.models import Deal, DealItem, DealLocation
from apps.catalog.serializers.deal_item_serializer import DealItemSerializer
from apps.catalog.serializers.deal_location_serializer import DealLocationSerializer


class DealSerializer(serializers.ModelSerializer):
    """
    Serializer for Deal with nested items and locations
    """
    
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    items = DealItemSerializer(many=True, read_only=True)
    locations = DealLocationSerializer(many=True, read_only=True)
    
    class Meta:
        model = Deal
        fields = [
            'id',
            'organization',
            'organization_name',
            'name',
            'slug',
            'description',
            'image',
            'discount_type',
            'discount_value',
            'start_at',
            'end_at',
            'is_active',
            'items',
            'locations',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Validate date range
        start_at = data.get('start_at', self.instance.start_at if self.instance else None)
        end_at = data.get('end_at', self.instance.end_at if self.instance else None)
        
        if start_at and end_at:
            if start_at >= end_at:
                raise serializers.ValidationError(
                    "Start date must be before end date."
                )
            
            if end_at < timezone.now():
                raise serializers.ValidationError(
                    "End date cannot be in the past."
                )
        
        # Validate discount
        discount_type = data.get('discount_type', self.instance.discount_type if self.instance else None)
        discount_value = data.get('discount_value', self.instance.discount_value if self.instance else 0)
        
        if discount_value <= 0:
            raise serializers.ValidationError("Discount value must be greater than 0.")
        
        if discount_type == Deal.DiscountType.PERCENTAGE and discount_value > 100:
            raise serializers.ValidationError("Percentage discount cannot exceed 100%.")
        
        # Check slug uniqueness
        if 'slug' in data or 'organization' in data:
            organization = data.get('organization', self.instance.organization if self.instance else None)
            slug = data.get('slug', self.instance.slug if self.instance else None)
            
            if organization and slug:
                queryset = Deal.objects.filter(
                    organization=organization,
                    slug=slug
                )
                if self.instance:
                    queryset = queryset.exclude(id=self.instance.id)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        f"Deal with slug '{slug}' already exists in this organization."
                    )
        
        return data