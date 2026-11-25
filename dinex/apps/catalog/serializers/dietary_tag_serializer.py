from rest_framework import serializers

from apps.catalog.models import DietaryTag


class DietaryTagSerializer(serializers.ModelSerializer):
    """
    Serializer for DietaryTag
    """
    
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = DietaryTag
        fields = [
            'id',
            'organization',
            'organization_name',
            'name',
            'slug',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Check if slug is unique for the organization
        if 'slug' in data or 'organization' in data:
            organization = data.get('organization', self.instance.organization if self.instance else None)
            slug = data.get('slug', self.instance.slug if self.instance else None)
            
            if organization and slug:
                queryset = DietaryTag.objects.filter(
                    organization=organization,
                    slug=slug
                )
                if self.instance:
                    queryset = queryset.exclude(id=self.instance.id)
                
                if queryset.exists():
                    raise serializers.ValidationError(
                        f"Dietary tag with slug '{slug}' already exists in this organization."
                    )
        
        return data