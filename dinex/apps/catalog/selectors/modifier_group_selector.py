from django.db.models import Q

from apps.catalog.models import ModifierGroup


class ModifierGroupSelector:
    """
    Selector for ModifierGroup with advanced filtering
    """
    
    @staticmethod
    def get_all_groups(organization_id=None, only_active=True):
        """
        Get all modifier groups with optional organization filter
        """
        queryset = ModifierGroup.objects.all()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @staticmethod
    def get_groups_by_product(product_id):
        """
        Get modifier groups linked to a product
        """
        from apps.catalog.models import ProductModifierGroup
        
        product_modifier_groups = ProductModifierGroup.objects.filter(
            product_id=product_id,
            modifier_group__is_active=True
        ).select_related('modifier_group')
        
        return [pmg.modifier_group for pmg in product_modifier_groups]
    
    @staticmethod
    def search_groups(organization_id, search_term):
        """
        Search modifier groups by name or description
        """
        return ModifierGroup.objects.filter(
            organization_id=organization_id,
            is_deleted=False
        ).filter(
            Q(name__icontains=search_term) |
            Q(description__icontains=search_term)
        )