from apps.catalog.models import DealLocation


class DealLocationSelector:
    """
    Selector for DealLocation with advanced filtering
    """
    
    @staticmethod
    def get_all_assignments(deal_id=None, location_id=None, only_enabled=True):
        """
        Get all deal-location assignments with optional filters
        """
        queryset = DealLocation.objects.all()
        
        if deal_id:
            queryset = queryset.filter(deal_id=deal_id)
        
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        
        if only_enabled:
            queryset = queryset.filter(is_enabled=True)
        
        return queryset
    
    @staticmethod
    def get_deal_locations(deal_id):
        """
        Get all locations where a deal is available
        """
        return DealLocation.objects.filter(
            deal_id=deal_id,
            is_enabled=True
        ).select_related('location')
    
    @staticmethod
    def get_location_deals(location_id):
        """
        Get all deals available at a location
        """
        return DealLocation.objects.filter(
            location_id=location_id,
            is_enabled=True
        ).select_related('deal')