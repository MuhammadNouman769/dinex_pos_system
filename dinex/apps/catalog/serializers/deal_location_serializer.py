from rest_framework import serializers

from apps.catalog.models import DealLocation


class DealLocationSerializer(serializers.ModelSerializer):
    """
    Serializer for DealLocation
    """
    
    deal_name = serializers.CharField(source='deal.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    
    class Meta:
        model = DealLocation
        fields = [
            'id',
            'deal',
            'deal_name',
            'location',
            'location_name',
            'is_enabled',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Check for duplicate deal-location combination
        if 'deal' in data or 'location' in data:
            deal = data.get('deal', self.instance.deal if self.instance else None)
            location = data.get('location', self.instance.location if self.instance else None)
            
            if deal and location:
                queryset = DealLocation.objects.filter(
                    deal=deal,
                    location=location
                )
                if self.instance:
                    queryset = queryset.exclude(id=self.instance.id)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        "This location is already assigned to this deal."
                    )
        
        return data