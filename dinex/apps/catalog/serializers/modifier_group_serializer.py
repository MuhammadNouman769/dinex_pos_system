from rest_framework import serializers

from apps.catalog.models import ModifierGroup, ModifierOption
from apps.catalog.serializers.modifier_option_serializer import ModifierOptionSerializer


class ModifierGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for ModifierGroup with options
    """
    
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    options = ModifierOptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = ModifierGroup
        fields = [
            'id',
            'organization',
            'organization_name',
            'name',
            'description',
            'min_selections',
            'max_selections',
            'is_required',
            'is_active',
            'options',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Validate min/max selections
        min_selections = data.get('min_selections', self.instance.min_selections if self.instance else 0)
        max_selections = data.get('max_selections', self.instance.max_selections if self.instance else 1)
        
        if min_selections > max_selections:
            raise serializers.ValidationError(
                "Minimum selections cannot be greater than maximum selections."
            )
        
        # If required, min_selections should be at least 1
        is_required = data.get('is_required', self.instance.is_required if self.instance else False)
        if is_required and min_selections == 0:
            raise serializers.ValidationError(
                "Required modifier group must have min_selections at least 1."
            )
        
        return data