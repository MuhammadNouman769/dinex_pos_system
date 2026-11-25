from rest_framework import serializers

from apps.catalog.models import DealItem


class DealItemSerializer(serializers.ModelSerializer):
    """
    Serializer for DealItem
    """
    
    deal_name = serializers.CharField(source='deal.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    
    class Meta:
        model = DealItem
        fields = [
            'id',
            'deal',
            'deal_name',
            'product_variant',
            'variant_name',
            'product_name',
            'quantity',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Check for duplicate deal-variant combination
        if 'deal' in data or 'product_variant' in data:
            deal = data.get('deal', self.instance.deal if self.instance else None)
            product_variant = data.get('product_variant', self.instance.product_variant if self.instance else None)
            
            if deal and product_variant:
                queryset = DealItem.objects.filter(
                    deal=deal,
                    product_variant=product_variant
                )
                if self.instance:
                    queryset = queryset.exclude(id=self.instance.id)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        "This variant is already added to this deal."
                    )
        
        # Validate quantity
        quantity = data.get('quantity', self.instance.quantity if self.instance else 1)
        if quantity <= 0:
            raise serializers.ValidationError("Quantity must be at least 1.")
        
        return data