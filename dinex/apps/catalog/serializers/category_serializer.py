from rest_framework import serializers

from apps.catalog.models import ProductCategory


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for ProductCategory with nested children support
    """
    
    children = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    class Meta:
        model = ProductCategory
        fields = [
            'id',
            'organization',
            'organization_name',
            'name',
            'slug',
            'description',
            'parent',
            'parent_name',
            'image',
            'is_active',
            'position',
            'children',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True, context=self.context).data
    
    def validate(self, data):
        # Prevent self-parenting
        if data.get('parent') and data.get('parent') == self.instance:
            raise serializers.ValidationError(
                "A category cannot be its own parent."
            )
        
        # Check for circular reference
        if self.instance and data.get('parent'):
            parent = data.get('parent')
            if self._is_circular_reference(parent):
                raise serializers.ValidationError(
                    "Circular reference detected in category hierarchy."
                )
        
        return data
    
    def _is_circular_reference(self, parent):
        """Check if the parent category would create a circular reference"""
        if not parent:
            return False
        
        current = parent
        while current:
            if current == self.instance:
                return True
            current = current.parent
        
        return False