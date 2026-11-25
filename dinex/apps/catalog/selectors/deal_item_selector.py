from apps.catalog.models import DealItem


class DealItemSelector:
    """
    Selector for DealItem with advanced filtering
    """
    
    @staticmethod
    def get_all_items(deal_id=None, variant_id=None):
        """
        Get all deal items with optional filters
        """
        queryset = DealItem.objects.all()
        
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        
        if variant_id:
            queryset = queryset.filter(product_variant_id=variant_id)
        
        return queryset
    
    @staticmethod
    def get_deal_items_with_details(deal_id):
        """
        Get all items for a deal with variant details
        """
        return DealItem.objects.filter(
            deal_id=deal_id
        ).select_related('product_variant', 'product_variant__product')