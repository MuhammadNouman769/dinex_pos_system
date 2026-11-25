from apps.orders.models import OrderItem


class OrderItemSelector:
    """
    Order Item Selector with advanced filtering
    """
    
    @staticmethod
    def get_all_items(order_id=None):
        """
        Get all order items with optional order filter
        """
        queryset = OrderItem.objects.all()
        
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        
        return queryset
    
    @staticmethod
    def get_items_by_order(order_id):
        """
        Get all items for a specific order
        """
        return OrderItem.objects.filter(
            order_id=order_id,
            is_deleted=False
        ).select_related('product_variant')
    
    @staticmethod
    def get_item_by_product(order_id, product_variant_id):
        """
        Get item by product variant in an order
        """
        return OrderItem.objects.get(
            order_id=order_id,
            product_variant_id=product_variant_id,
            is_deleted=False
        )