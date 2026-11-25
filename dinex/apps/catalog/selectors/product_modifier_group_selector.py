from apps.catalog.models import ProductModifierGroup


class ProductModifierGroupSelector:
    """
    Selector for ProductModifierGroup with advanced filtering
    """
    
    @staticmethod
    def get_all_links(product_id=None, modifier_group_id=None):
        """
        Get all product-modifier group links
        """
        queryset = ProductModifierGroup.objects.all()
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        if modifier_group_id:
            queryset = queryset.filter(modifier_group_id=modifier_group_id)
        
        return queryset
    
    @staticmethod
    def get_product_modifier_groups_with_details(product_id):
        """
        Get all modifier group links for a product with details
        """
        return ProductModifierGroup.objects.filter(
            product_id=product_id
        ).select_related('modifier_group')