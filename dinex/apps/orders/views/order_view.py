from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.permissions import IsAuthenticated

from apps.orders.models.order import Order
from apps.orders.serializers.order_serializer import OrderSerializer
from apps.orders.selectors.order_selector import OrderSelector
from apps.orders.schemas.order_schema import (
    ORDER_LIST_SCHEMA,
    ORDER_CREATE_SCHEMA,
    ORDER_RETRIEVE_SCHEMA,
    ORDER_UPDATE_SCHEMA,
    ORDER_DELETE_SCHEMA,
    ORDER_STATUS_UPDATE_SCHEMA,
    ORDER_STATS_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly, CanOperatePOS
from apps.utils.pagination import StandardResultsSetPagination
from apps.catalog.utils import get_user_organization_id
from apps.utils.helpers import location_scope, location_model_scope


@extend_schema_view(
    get=ORDER_LIST_SCHEMA,
    post=ORDER_CREATE_SCHEMA,
)
class OrderListCreateView(APIView):
    """
    View to list and create orders
    """
    permission_classes = [IsAuthenticated, CanOperatePOS]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Get all orders for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        location_id = request.query_params.get('location', None)
        status_filter = request.query_params.get('status', None)
        search_term = request.query_params.get('search', None)
        only_active = request.query_params.get('active', 'true').lower() == 'true'
        date_range = request.query_params.get('date', None)
        
        # Always start from the caller's organization; every filter below
        # only narrows this queryset, it never replaces it.
        queryset = Order.objects.filter(**location_scope(request, organization_id))

        if location_id:
            try:
                queryset = queryset.filter(location_id=int(location_id))
            except (TypeError, ValueError):
                return Response({"error": "Invalid location id."}, status=status.HTTP_400_BAD_REQUEST)

        if only_active:
            queryset = queryset.filter(is_active=True)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if search_term:
            queryset = OrderSelector.filter_search(queryset, search_term)

        if date_range:
            # Format: 2026-09-01,2026-09-08
            from datetime import datetime
            dates = date_range.split(',')
            try:
                if len(dates) != 2:
                    raise ValueError
                start = datetime.strptime(dates[0].strip(), '%Y-%m-%d').date()
                end = datetime.strptime(dates[1].strip(), '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "date must be 'YYYY-MM-DD,YYYY-MM-DD'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = OrderSelector.filter_date_range(queryset, start, end)

        queryset = queryset.select_related('location', 'customer', 'table').prefetch_related('items')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    @transaction.atomic
    def post(self, request):
        """Create a new order"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify location belongs to organization
        location_id = request.data.get('location')
        if location_id:
            from apps.organizations.models import Location
            get_object_or_404(Location, id=location_id, **location_model_scope(request, organization_id))
        
        data = request.data.copy()
        data['created_by'] = request.user.id
        
        serializer = OrderSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=ORDER_RETRIEVE_SCHEMA,
    put=ORDER_UPDATE_SCHEMA,
    patch=ORDER_UPDATE_SCHEMA,
    delete=ORDER_DELETE_SCHEMA,
)
class OrderRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete an order
    """
    permission_classes = [IsAuthenticated, CanOperatePOS]
    
    def get(self, request, pk):
        """Get order by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order = get_object_or_404(
            Order,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data)
    
    @transaction.atomic
    def put(self, request, pk):
        """Update order"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order = get_object_or_404(
            Order,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        # Verify location belongs to organization if changed
        location_id = request.data.get('location')
        if location_id:
            from apps.organizations.models import Location
            get_object_or_404(Location, id=location_id, **location_model_scope(request, organization_id))
        
        serializer = OrderSerializer(
            order,
            data=request.data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            order = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def patch(self, request, pk):
        """Partial update order"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order = get_object_or_404(
            Order,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        serializer = OrderSerializer(
            order,
            data=request.data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            order = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete order"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order = get_object_or_404(
            Order,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        # Cannot delete completed orders
        if order.status == Order.OrderStatus.COMPLETED:
            return Response(
                {"error": "Cannot delete completed orders."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if order.payments.exists():
            return Response(
                {"error": "This order has payments and cannot be deleted. Refund and cancel it instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.stock_deducted and order.status in ('PENDING', 'CONFIRMED'):
            from apps.inventory.services import sync_stock_for_order
            sync_stock_for_order(order, release_all=True)
        order.delete()
        order.release_table_if_unused()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderSyncView(APIView):
    """
    Place a whole order in ONE request (items, deals, payments). Safe to repeat: the same
    `client_uuid` never makes a second order. Used by the POS online and for orders saved offline.
    """
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def post(self, request):
        from apps.orders.sync import place_order
        organization_id = get_user_organization_id(request)
        if not organization_id:
            return Response({"error": "User has no organization assigned."}, status=status.HTTP_403_FORBIDDEN)
        order, created, info = place_order(request, organization_id, request.data)
        body = OrderSerializer(order, context={"request": request}).data
        return Response({"order": body, "created": created, **info},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class OrderStatusUpdateView(APIView):
    """
    View to update order status
    """
    permission_classes = [IsAuthenticated, CanOperatePOS]
    
    def post(self, request, pk):
        """Update order status"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        order = get_object_or_404(
            Order,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        new_status = request.data.get('status')
        if not new_status:
            return Response(
                {"error": "status is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', '')
        if new_status == 'CANCELLED' and order.status != 'PENDING':
            from apps.utils.helpers import is_manager_or_owner
            if not is_manager_or_owner(request, order.location):
                return Response(
                    {"error": "Only a manager or the owner can cancel an order that was sent to the kitchen."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        try:
            order.update_status(new_status, user=request.user, reason=reason)
            return Response({
                'id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'message': f'Order status updated to {new_status}',
                'stock_warnings': getattr(order, 'stock_warnings', []),
            })
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class OrderStatsView(APIView):
    """
    View to get order statistics
    """
    permission_classes = [IsAuthenticated, CanOperatePOS]
    
    def get(self, request):
        """Get order statistics"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        location_id = request.query_params.get('location', None)

        from apps.organizations.models import Location
        if not location_id:
            stats = {
                loc.name: OrderSelector.get_order_stats(organization_id, loc.id)
                for loc in Location.objects.filter(organization_id=organization_id)
            }
        else:
            try:
                location_id = int(location_id)
            except (TypeError, ValueError):
                return Response({"error": "Invalid location id."}, status=status.HTTP_400_BAD_REQUEST)
            # 404 if the location belongs to another organization
            get_object_or_404(Location, id=location_id, **location_model_scope(request, organization_id))
            stats = OrderSelector.get_order_stats(organization_id, location_id)

        return Response(stats)


class _OrderOpView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def order(self, request, pk):
        organization_id = get_user_organization_id(request)
        if not organization_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("User has no organization assigned.")
        return get_object_or_404(Order, pk=pk, **location_scope(request, organization_id, 'location'))


class OrderTransferTableView(_OrderOpView):
    """POST {table: id} - move an open dine-in order to a free table."""

    def post(self, request, pk):
        from apps.orders.ops import transfer_table
        order = transfer_table(self.order(request, pk), request.data.get("table"), request.user)
        return Response(OrderSerializer(order, context={"request": request}).data)


class OrderSplitView(_OrderOpView):
    """POST {items: [{item, quantity}]} - move those items to a new bill. Returns both orders."""

    def post(self, request, pk):
        from apps.orders.ops import split_order
        picks = request.data.get("items")
        if not isinstance(picks, list) or not all(isinstance(p, dict) and "item" in p and "quantity" in p for p in picks):
            return Response({"items": "Send items as [{item, quantity}]."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            picks = [{"item": int(p["item"]), "quantity": int(p["quantity"])} for p in picks]
        except (TypeError, ValueError):
            return Response({"items": "Send items as [{item, quantity}]."}, status=status.HTTP_400_BAD_REQUEST)
        original, new = split_order(self.order(request, pk), picks, request.user, request)
        ctx = {"request": request}
        return Response({"order": OrderSerializer(original, context=ctx).data, "new_order": OrderSerializer(new, context=ctx).data}, status=status.HTTP_201_CREATED)
