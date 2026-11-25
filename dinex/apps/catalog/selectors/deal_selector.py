from django.db.models import Q, Prefetch
from django.utils import timezone

from apps.catalog.models import Deal, DealItem, DealLocation


class DealSelector:
    """
    Selector for Deal with advanced filtering
    """
    
    @staticmethod
    def get_all_deals(organization_id=None, only_active=True):
        """
        Get all deals with optional organization filter
        """
        queryset = Deal.objects.all()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @staticmethod
    def get_active_deals(organization_id=None):
        """
        Get currently active deals
        """
        now = timezone.now()
        queryset = DealSelector.get_all_deals(organization_id, True)
        return queryset.filter(
            start_at__lte=now,
            end_at__gte=now
        )
    
    @staticmethod
    def get_deals_by_location(location_id, organization_id=None):
        """
        Get deals available at a specific location
        """
        queryset = DealSelector.get_active_deals(organization_id)
        return queryset.filter(
            locations__location_id=location_id,
            locations__is_enabled=True
        )
    
    @staticmethod
    def get_deal_with_details(deal_id):
        """
        Get deal with all related data
        """
        return Deal.objects.select_related('organization').prefetch_related(
            Prefetch('items', queryset=DealItem.objects.select_related('product_variant__product')),
            Prefetch('locations', queryset=DealLocation.objects.filter(is_enabled=True))
        ).get(id=deal_id, is_deleted=False)
    
    @staticmethod
    def search_deals(organization_id, search_term):
        """
        Search deals by name or description
        """
        return Deal.objects.filter(
            organization_id=organization_id,
            is_deleted=False
        ).filter(
            Q(name__icontains=search_term) |
            Q(description__icontains=search_term)
        )