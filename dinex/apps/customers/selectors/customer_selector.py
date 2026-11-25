from django.db.models import Q
from apps.customers.models.customer import Customer


class CustomerSelector:
    """
    Customer Selector with advanced filtering
    """
    
    @staticmethod
    def get_all_customers(location_id=None, only_active=True):
        """
        Get all customers with optional location filter
        """
        queryset = Customer.objects.all()
        
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @staticmethod
    def get_customer_by_phone(location_id, phone):
        """
        Get customer by phone number at a location
        """
        return Customer.objects.get(
            location_id=location_id,
            phone=phone,
            is_deleted=False
        )
    
    @staticmethod
    def filter_search(queryset, search_term):
        """Chain onto an already org-scoped queryset (never replaces it)."""
        return queryset.filter(
            Q(first_name__icontains=search_term) |
            Q(last_name__icontains=search_term) |
            Q(phone__icontains=search_term)
        )

    @staticmethod
    def search_customers(location_id, search_term):
        """
        Search customers by name or phone
        """
        return Customer.objects.filter(
            location_id=location_id,
            is_deleted=False
        ).filter(
            Q(first_name__icontains=search_term) |
            Q(last_name__icontains=search_term) |
            Q(phone__icontains=search_term)
        )
    
    @staticmethod
    def get_top_customers(location_id, limit=10):
        """
        Get top customers by total spent
        """
        return Customer.objects.filter(
            location_id=location_id,
            is_deleted=False,
            is_active=True
        ).order_by('-total_spent')[:limit]