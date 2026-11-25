from django.db import transaction
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from apps.orders.models.order import Order
from apps.orders.models.order_item import  OrderItem
from apps.orders.serializers.order_item_serializer import OrderItemSerializer
from apps.orders.selectors.order_item_selector import OrderItemSelector
from apps.orders.schemas.order_item_schema import (
    ORDER_ITEM_LIST_SCHEMA,
    ORDER_ITEM_CREATE_SCHEMA,
    ORDER_ITEM_RETRIEVE_SCHEMA,
    ORDER_ITEM_UPDATE_SCHEMA,
    ORDER_ITEM_DELETE_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly, CanOperatePOS
from apps.utils.pagination import StandardResultsSetPagination
from apps.catalog.utils import get_user_organization_id
from apps.utils.helpers import location_scope, location_model_scope


@extend_schema_view(
    get=ORDER_ITEM_LIST_SCHEMA,
    post=ORDER_ITEM_CREATE_SCHEMA,
)
class OrderItemListCreateView(APIView):
    """
    View to list and create order items
    """
    permission_classes = [IsAuthenticated, CanOperatePOS]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Get all order items for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order_id = request.query_params.get('order', None)
        
        queryset = OrderItemSelector.get_all_items(order_id)
        queryset = queryset.filter(
            **location_scope(request, organization_id, 'order__location')
        )
        queryset = queryset.select_related('order', 'product_variant')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderItemSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    @transaction.atomic
    def post(self, request):
        """Create a new order item"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify order belongs to organization
        order_id = request.data.get('order')
        if order_id:
            get_object_or_404(Order, id=order_id, **location_scope(request, organization_id))
        
        serializer = OrderItemSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order_item = serializer.save()
            # Recalculate order totals
            order_item.order.calculate_totals()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=ORDER_ITEM_RETRIEVE_SCHEMA,
    put=ORDER_ITEM_UPDATE_SCHEMA,
    patch=ORDER_ITEM_UPDATE_SCHEMA,
    delete=ORDER_ITEM_DELETE_SCHEMA,
)
class OrderItemRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete an order item
    """
    permission_classes = [IsAuthenticated, CanOperatePOS]
    
    def get(self, request, pk):
        """Get order item by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order_item = get_object_or_404(
            OrderItem,
            id=pk,
            **location_scope(request, organization_id, 'order__location'),
            is_deleted=False
        )
        
        serializer = OrderItemSerializer(order_item, context={'request': request})
        return Response(serializer.data)
    
    @transaction.atomic
    def put(self, request, pk):
        """Update order item"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order_item = get_object_or_404(
            OrderItem,
            id=pk,
            **location_scope(request, organization_id, 'order__location'),
            is_deleted=False
        )
        
        serializer = OrderItemSerializer(
            order_item,
            data=request.data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            order_item = serializer.save()
            order_item.order.calculate_totals()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def patch(self, request, pk):
        """Partial update order item"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order_item = get_object_or_404(
            OrderItem,
            id=pk,
            **location_scope(request, organization_id, 'order__location'),
            is_deleted=False
        )
        
        serializer = OrderItemSerializer(
            order_item,
            data=request.data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            order_item = serializer.save()
            order_item.order.calculate_totals()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def delete(self, request, pk):
        """Soft delete order item"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order_item = get_object_or_404(
            OrderItem,
            id=pk,
            **location_scope(request, organization_id, 'order__location'),
            is_deleted=False
        )
        
        order = order_item.order
        order_item.delete()
        order.calculate_totals()
        return Response(status=status.HTTP_204_NO_CONTENT)