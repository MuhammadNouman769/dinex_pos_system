from django.urls import path
from apps.loyalty.views import RedeemView
from apps.orders.views.order_view import (
    OrderListCreateView,
    OrderRetrieveUpdateDeleteView,
    OrderStatusUpdateView,
    OrderStatsView,
    OrderSyncView,
    OrderTransferTableView,
    OrderSplitView,
)
from apps.orders.views.order_item_view import (
    OrderItemListCreateView,
    OrderItemRetrieveUpdateDeleteView,
)
from apps.orders.views.table_view import (
    TableListCreateView,
    TableRetrieveUpdateDeleteView,
    TableOccupyView,
    TableFreeView,
    AvailableTablesView,
)

from apps.orders.views.floor_view import FloorListCreateView, FloorDetailView

urlpatterns = [
    # Order URLs
    path('', OrderListCreateView.as_view(), name='order-list-create'),
    path('sync/', OrderSyncView.as_view(), name='order-sync'),
    path('stats/', OrderStatsView.as_view(), name='order-stats'),
    path('<int:pk>/', OrderRetrieveUpdateDeleteView.as_view(), name='order-detail'),
    path('<int:pk>/transfer-table/', OrderTransferTableView.as_view(), name='order-transfer-table'),
    path('<int:pk>/split/', OrderSplitView.as_view(), name='order-split'),
    path('<int:pk>/redeem-points/', RedeemView.as_view(), name='order-redeem-points'),
    path('<int:pk>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
    
    # Order Item URLs
    path('items/', OrderItemListCreateView.as_view(), name='order-item-list-create'),
    path('items/<int:pk>/', OrderItemRetrieveUpdateDeleteView.as_view(), name='order-item-detail'),
    
    # Table URLs
    path('floors/', FloorListCreateView.as_view(), name='floor-list-create'),
    path('floors/<int:pk>/', FloorDetailView.as_view(), name='floor-detail'),
    path('tables/', TableListCreateView.as_view(), name='table-list-create'),
    path('tables/available/', AvailableTablesView.as_view(), name='table-available'),
    path('tables/<int:pk>/', TableRetrieveUpdateDeleteView.as_view(), name='table-detail'),
    path('tables/<int:pk>/occupy/', TableOccupyView.as_view(), name='table-occupy'),
    path('tables/<int:pk>/free/', TableFreeView.as_view(), name='table-free'),
]