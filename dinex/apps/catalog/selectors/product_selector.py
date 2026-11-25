from django.db.models import Q, Prefetch

from apps.catalog.models import Product, ProductVariant, ProductLocation, DietaryTag


class ProductSelector:
    """
    Selector for Product with advanced filtering
    """
    
    @staticmethod
    def get_all_products(organization_id=None, only_active=True):
        """
        Get all products with optional organization filter
        """
        queryset = Product.objects.all()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @staticmethod
    def get_products_by_category(category_id, organization_id=None, only_active=True):
        """
        Get products by category
        """
        queryset = ProductSelector.get_all_products(organization_id, only_active)
        return queryset.filter(category_id=category_id)
    
    @staticmethod
    def get_products_by_location(location_id, organization_id=None, only_active=True):
        """
        Get products available at a specific location
        """
        queryset = ProductSelector.get_all_products(organization_id, only_active)
        return queryset.filter(
            location_assignments__location_id=location_id,
            location_assignments__is_available=True
        )
    
    @staticmethod
    def get_product_with_details(product_id):
        """
        Get product with all related data (variants, tags, locations)
        """
        return Product.objects.select_related('category', 'organization').prefetch_related(
            Prefetch('variants', queryset=ProductVariant.objects.filter(is_active=True)),
            Prefetch('dietary_tags', queryset=DietaryTag.objects.filter(is_active=True)),
            Prefetch('location_assignments', 
                    queryset=ProductLocation.objects.filter(is_available=True))
        ).get(id=product_id, is_deleted=False)
    
    @staticmethod
    def get_products_by_type(product_type, organization_id=None):
        """
        Get products by type
        """
        queryset = ProductSelector.get_all_products(organization_id)
        return queryset.filter(product_type=product_type)
    
    @staticmethod
    def search_products(organization_id, search_term):
        """
        Search products by name, SKU, or description
        """
        return Product.objects.filter(
            organization_id=organization_id,
            is_deleted=False
        ).filter(
            Q(name__icontains=search_term) |
            Q(sku__icontains=search_term) |
            Q(description__icontains=search_term)
        )