from django.db.models import Q

from apps.catalog.models import ProductLocation


class ProductLocationSelector:
    """
    Selector for ProductLocation with advanced filtering
    """
    
    @staticmethod
    def get_all_assignments(product_id=None, location_id=None, only_available=True):
        """
        Get all location assignments with optional filters
        """
        queryset = ProductLocation.objects.all()
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        
        if only_available:
            queryset = queryset.filter(is_available=True)
        
        return queryset
    
    @staticmethod
    def get_product_locations(product_id):
        """
        Get all locations where a product is available
        """
        return ProductLocation.objects.filter(
            product_id=product_id,
            is_available=True
        ).select_related('location')
    
    @staticmethod
    def get_location_products(location_id):
        """
        Get all products available at a location
        """
        return ProductLocation.objects.filter(
            location_id=location_id,
            is_available=True
        ).select_related('product', 'product_variant')