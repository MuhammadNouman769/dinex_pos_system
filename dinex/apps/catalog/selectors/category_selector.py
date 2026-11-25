from django.db.models import Q

from apps.catalog.models import ProductCategory


class CategorySelector:
    """
    Selector for ProductCategory with advanced filtering
    """
    
    @staticmethod
    def get_all_categories(organization_id=None, only_active=True):
        """
        Get all categories with optional organization filter
        """
        queryset = ProductCategory.objects.all()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @staticmethod
    def get_root_categories(organization_id=None, only_active=True):
        """
        Get only root categories (no parent)
        """
        queryset = CategorySelector.get_all_categories(organization_id, only_active)
        return queryset.filter(parent__isnull=True)
    
    @staticmethod
    def get_category_by_slug(organization_id, slug):
        """
        Get category by slug within organization
        """
        return ProductCategory.objects.get(
            organization_id=organization_id,
            slug=slug,
            is_deleted=False
        )
    
    @staticmethod
    def get_category_tree(organization_id=None):
        """
        Get complete category tree
        """
        categories = CategorySelector.get_root_categories(organization_id)
        
        def build_tree(category):
            children = category.children.filter(is_active=True)
            return {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'image': category.image.url if category.image else None,
                'position': category.position,
                'children': [build_tree(child) for child in children]
            }
        
        return [build_tree(category) for category in categories]
    
    @staticmethod
    def search_categories(organization_id, search_term):
        """
        Search categories by name or description
        """
        return ProductCategory.objects.filter(
            organization_id=organization_id,
            is_deleted=False
        ).filter(
            Q(name__icontains=search_term) |
            Q(description__icontains=search_term)
        )