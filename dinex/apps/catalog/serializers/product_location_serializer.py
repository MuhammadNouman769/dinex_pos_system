from rest_framework import serializers

from apps.catalog.models import ProductLocation


class ProductLocationSerializer(serializers.ModelSerializer):
    """
    Serializer for ProductLocation (location assignment)
    """
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    
    class Meta:
        model = ProductLocation
        fields = [
            'id',
            'product',
            'product_name',
            'product_variant',
            'variant_name',
            'location',
            'location_name',
            'is_available',
            'available_quantity',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # On a partial update, fields not included in the request are
        # simply absent from `data` — fall back to the existing
        # instance's value so PATCHing e.g. just `available_quantity`
        # doesn't spuriously fail this check.
        product = data['product'] if 'product' in data else getattr(self.instance, 'product', None)
        product_variant = (
            data['product_variant'] if 'product_variant' in data
            else getattr(self.instance, 'product_variant', None)
        )
        location = data['location'] if 'location' in data else getattr(self.instance, 'location', None)

        if not product and not product_variant:
            raise serializers.ValidationError(
                "Either product or product_variant must be provided."
            )
        
        if product and product_variant:
            # If both provided, variant must belong to product
            if product_variant.product != product:
                raise serializers.ValidationError(
                    "The variant does not belong to the specified product."
                )
        
        # Check for duplicate assignment
        if location:
            if product and not product_variant:
                # Product-level assignment: only one per product+location.
                # (Per-variant rows are checked separately below, so several
                # variants of one product can live at the same location.)
                queryset = ProductLocation.objects.filter(
                    product=product,
                    location=location,
                    product_variant__isnull=True,
                )
                if self.instance:
                    queryset = queryset.exclude(id=self.instance.id)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        "This product is already assigned to this location."
                    )
            
            if product_variant:
                queryset = ProductLocation.objects.filter(
                    product_variant=product_variant,
                    location=location
                )
                if self.instance:
                    queryset = queryset.exclude(id=self.instance.id)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        "This variant is already assigned to this location."
                    )
        
        return data