from django.db.models import Q

from apps.catalog.models import ProductVariant


class VariantSelector:
    """
    Selector for ProductVariant with advanced filtering
    """
    
    @staticmethod
    def get_all_variants(product_id=None, only_active=True):
        """
        Get all variants with optional product filter
        """
        queryset = ProductVariant.objects.all()
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @staticmethod
    def get_default_variant(product_id):
        """
        Get default variant for a product
        """
        return ProductVariant.objects.get(
            product_id=product_id,
            is_default=True,
            is_deleted=False
        )
    
    @staticmethod
    def get_variant_by_sku(sku, organization_id=None):
        """
        Get variant by SKU
        """
        queryset = ProductVariant.objects.filter(sku=sku, is_deleted=False)
        
        if organization_id:
            queryset = queryset.filter(product__organization_id=organization_id)
        
        return queryset.first()
    
    @staticmethod
    def get_variant_by_barcode(barcode, organization_id=None):
        """
        Get variant by barcode
        """
        queryset = ProductVariant.objects.filter(barcode=barcode, is_deleted=False)
        
        if organization_id:
            queryset = queryset.filter(product__organization_id=organization_id)
        
        return queryset.first()
    
    @staticmethod
    def search_variants(search_term, product_id=None):
        """
        Search variants by name, SKU, or barcode
        """
        queryset = ProductVariant.objects.filter(is_deleted=False)
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        return queryset.filter(
            Q(name__icontains=search_term) |
            Q(sku__icontains=search_term) |
            Q(barcode__icontains=search_term)
        )