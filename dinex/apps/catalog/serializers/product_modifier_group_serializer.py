from rest_framework import serializers

from apps.catalog.models import ProductModifierGroup


class ProductModifierGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for ProductModifierGroup (junction table)
    """
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    modifier_group_name = serializers.CharField(source='modifier_group.name', read_only=True)
    
    class Meta:
        model = ProductModifierGroup
        fields = [
            'id',
            'product',
            'product_name',
            'modifier_group',
            'modifier_group_name',
            'display_order',
            'is_required_override',
            'min_selections_override',
            'max_selections_override',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Check for duplicate product-modifier group combination
        if 'product' in data or 'modifier_group' in data:
            product = data.get('product', self.instance.product if self.instance else None)
            modifier_group = data.get('modifier_group', self.instance.modifier_group if self.instance else None)
            
            if product and modifier_group:
                queryset = ProductModifierGroup.objects.filter(
                    product=product,
                    modifier_group=modifier_group
                )
                if self.instance:
                    queryset = queryset.exclude(id=self.instance.id)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        "This modifier group is already linked to this product."
                    )
        
        # Validate overrides
        min_override = data.get('min_selections_override')
        max_override = data.get('max_selections_override')
        
        if min_override is not None and max_override is not None:
            if min_override > max_override:
                raise serializers.ValidationError(
                    "Min selections override cannot be greater than max selections override."
                )
        
        return data