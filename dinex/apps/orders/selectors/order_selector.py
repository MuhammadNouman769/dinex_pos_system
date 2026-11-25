from django.db.models import Q, Sum, Count
from django.utils import timezone
from apps.orders.models import Order


class OrderSelector:
    """
    Order Selector with advanced filtering
    """
    
    @staticmethod
    def get_all_orders(location_id=None, only_active=True):
        """
        Get all orders with optional location filter
        """
        queryset = Order.objects.all()
        
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @staticmethod
    def get_orders_by_status(location_id, status):
        """
        Get orders by status
        """
        return Order.objects.filter(
            location_id=location_id,
            status=status,
            is_deleted=False
        )
    
    @staticmethod
    def get_active_orders(location_id):
        """
        Get active orders (not completed or cancelled)
        """
        return Order.objects.filter(
            location_id=location_id,
            is_deleted=False,
            is_active=True
        ).exclude(
            status__in=[
                Order.OrderStatus.COMPLETED,
                Order.OrderStatus.CANCELLED
            ]
        )
    
    @staticmethod
    def get_orders_by_date_range(location_id, start_date, end_date):
        """
        Get orders between dates
        """
        return Order.objects.filter(
            location_id=location_id,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_deleted=False
        )
    
    @staticmethod
    def get_today_orders(location_id):
        """
        Get today's orders
        """
        today = timezone.now().date()
        return Order.objects.filter(
            location_id=location_id,
            created_at__date=today,
            is_deleted=False
        )
    
    @staticmethod
    def filter_search(queryset, search_term):
        """Chain onto an already org-scoped queryset (never replaces it)."""
        return queryset.filter(
            Q(order_number__icontains=search_term) |
            Q(customer_name__icontains=search_term) |
            Q(customer_phone__icontains=search_term)
        )

    @staticmethod
    def filter_date_range(queryset, start_date, end_date):
        """Chain onto an already org-scoped queryset (never replaces it)."""
        return queryset.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )

    @staticmethod
    def get_order_stats(organization_id, location_id=None):
        """
        Order statistics, always limited to one organization
        (optionally narrowed to one of its locations).
        """
        today = timezone.localdate()
        orders = Order.objects.filter(
            location__organization_id=organization_id,
            is_deleted=False
        )
        if location_id:
            orders = orders.filter(location_id=location_id)
        
        return {
            'total_orders': orders.count(),
            'total_amount': orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'today_orders': orders.filter(created_at__date=today).count(),
            'pending_orders': orders.filter(status=Order.OrderStatus.PENDING).count(),
            'preparing_orders': orders.filter(status=Order.OrderStatus.PREPARING).count(),
            'ready_orders': orders.filter(status=Order.OrderStatus.READY).count(),
            'completed_orders': orders.filter(status=Order.OrderStatus.COMPLETED).count(),
            'cancelled_orders': orders.filter(status=Order.OrderStatus.CANCELLED).count(),
        }
    
    @staticmethod
    def search_orders(location_id, search_term):
        """
        Search orders by number or customer name
        """
        return Order.objects.filter(
            location_id=location_id,
            is_deleted=False
        ).filter(
            Q(order_number__icontains=search_term) |
            Q(customer_name__icontains=search_term) |
            Q(customer_phone__icontains=search_term)
        )