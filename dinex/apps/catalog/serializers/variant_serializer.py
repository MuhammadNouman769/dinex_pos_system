from rest_framework import serializers
from apps.utils.serializers import OrganizationScopedMixin

from apps.catalog.models import ProductVariant


class ProductVariantSerializer(OrganizationScopedMixin, serializers.ModelSerializer):
    org_scoped_fields = {"product": "organization_id"}

    """
    Serializer for ProductVariant
    """
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = [
            'id',
            'product',
            'product_name',
            'name',
            'sku',
            'barcode',
            'base_price',
            'cost_price',
            'position',
            'is_default',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Only one default variant per product
        if data.get('is_default', False):
            product = data.get('product', self.instance.product if self.instance else None)
            if product:
                queryset = ProductVariant.objects.filter(
                    product=product,
                    is_default=True
                )
                if self.instance:
                    queryset = queryset.exclude(id=self.instance.id)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        "A product can have only one default variant."
                    )
        
        # Validate SKU uniqueness within product
        if 'sku' in data or 'product' in data:
            product = data.get('product', self.instance.product if self.instance else None)
            sku = data.get('sku', self.instance.sku if self.instance else None)
            
            if product and sku:
                queryset = ProductVariant.objects.filter(
                    product=product,
                    sku=sku
                )
                if self.instance:
                    queryset = queryset.exclude(id=self.instance.id)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        f"Variant with SKU '{sku}' already exists for this product."
                    )
        
        # Validate price fields
        base_price = data.get('base_price', self.instance.base_price if self.instance else 0)
        cost_price = data.get('cost_price', self.instance.cost_price if self.instance else 0)
        
        if base_price < 0:
            raise serializers.ValidationError("Base price cannot be negative.")
        
        if cost_price < 0:
            raise serializers.ValidationError("Cost price cannot be negative.")
        
        return data