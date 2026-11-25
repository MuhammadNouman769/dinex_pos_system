from django.db.models import Q

from apps.catalog.models import ModifierOption


class ModifierOptionSelector:
    """
    Selector for ModifierOption with advanced filtering
    """
    
    @staticmethod
    def get_all_options(modifier_group_id=None, only_active=True):
        """
        Get all options with optional group filter
        """
        queryset = ModifierOption.objects.all()
        
        if modifier_group_id:
            queryset = queryset.filter(modifier_group_id=modifier_group_id)
        
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @staticmethod
    def search_options(search_term, modifier_group_id=None):
        """
        Search options by name
        """
        queryset = ModifierOption.objects.filter(is_deleted=False)
        
        if modifier_group_id:
            queryset = queryset.filter(modifier_group_id=modifier_group_id)
        
        return queryset.filter(name__icontains=search_term)