from rest_framework import serializers

from apps.catalog.models import ModifierOption


class ModifierOptionSerializer(serializers.ModelSerializer):
    """
    Serializer for ModifierOption
    """
    
    group_name = serializers.CharField(source='modifier_group.name', read_only=True)
    
    class Meta:
        model = ModifierOption
        fields = [
            'id',
            'modifier_group',
            'group_name',
            'name',
            'price_adjustment',
            'position',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Validate price adjustment
        price_adjustment = data.get('price_adjustment', self.instance.price_adjustment if self.instance else 0)
        
        # Price adjustment can be negative, but let's set a reasonable limit
        if price_adjustment < -1000000:
            raise serializers.ValidationError(
                "Price adjustment cannot be less than -1,000,000."
            )
        
        return data