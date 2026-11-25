from rest_framework import serializers
from apps.utils.serializers import OrganizationScopedMixin

from apps.catalog.models import Product, ProductVariant
from apps.catalog.serializers.variant_serializer import ProductVariantSerializer
from apps.catalog.serializers.dietary_tag_serializer import DietaryTagSerializer


class ProductSerializer(OrganizationScopedMixin, serializers.ModelSerializer):
    org_scoped_fields = {"category": "organization_id", "dietary_tags": "organization_id"}

    """
    Serializer for Product with nested relationships
    """
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    dietary_tags = DietaryTagSerializer(many=True, read_only=True)
    modifier_groups = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'organization',
            'organization_name',
            'category',
            'category_name',
            'name',
            'slug',
            'sku',
            'description',
            'product_type',
            'image',
            'is_active',
            'dietary_tags',
            'variants',
            'modifier_groups',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_modifier_groups(self, obj):
        from apps.catalog.modifiers import effective_groups
        return effective_groups(obj)

    def validate(self, data):
        # Check if slug is unique for the organization
        if 'slug' in data or 'organization' in data:
            organization = data.get('organization', self.instance.organization if self.instance else None)
            slug = data.get('slug', self.instance.slug if self.instance else None)
            
            if organization and slug:
                queryset = Product.objects.filter(
                    organization=organization,
                    slug=slug
                )
                if self.instance:
                    queryset = queryset.exclude(id=self.instance.id)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        f"Product with slug '{slug}' already exists in this organization."
                    )
        
        return data