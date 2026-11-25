from django.db.models import Q

from apps.catalog.models import DietaryTag


class DietaryTagSelector:
    """
    Selector for DietaryTag with advanced filtering
    """
    
    @staticmethod
    def get_all_tags(organization_id=None, only_active=True):
        """
        Get all dietary tags with optional organization filter
        """
        queryset = DietaryTag.objects.all()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @staticmethod
    def get_tag_by_slug(organization_id, slug):
        """
        Get tag by slug
        """
        return DietaryTag.objects.get(
            organization_id=organization_id,
            slug=slug,
            is_deleted=False
        )
    
    @staticmethod
    def search_tags(organization_id, search_term):
        """
        Search tags by name
        """
        return DietaryTag.objects.filter(
            organization_id=organization_id,
            is_deleted=False,
            name__icontains=search_term
        )