from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from apps.orders.models import Table
from apps.orders.serializers.table_serializer import TableSerializer
from apps.orders.selectors.table_selector import TableSelector
from apps.orders.schemas.table_schema import (
    TABLE_LIST_SCHEMA,
    TABLE_CREATE_SCHEMA,
    TABLE_RETRIEVE_SCHEMA,
    TABLE_UPDATE_SCHEMA,
    TABLE_DELETE_SCHEMA,
    TABLE_OCCUPY_SCHEMA,
    TABLE_FREE_SCHEMA,
    TABLE_AVAILABLE_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly, CanOperatePOS
from apps.utils.pagination import StandardResultsSetPagination
from apps.catalog.utils import get_user_organization_id
from apps.utils.helpers import location_scope, location_model_scope


@extend_schema_view(
    get=TABLE_LIST_SCHEMA,
    post=TABLE_CREATE_SCHEMA,
)
class TableListCreateView(APIView):
    """
    View to list and create tables
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Get all tables for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        location_id = request.query_params.get('location', None)
        only_active = request.query_params.get('active', 'true').lower() == 'true'
        status_filter = request.query_params.get('status', None)
        only_available = request.query_params.get('available', 'false').lower() == 'true'
        
        if only_available:
            queryset = TableSelector.get_available_tables(location_id)
        else:
            queryset = TableSelector.get_all_tables(location_id, only_active)
        
        queryset = queryset.filter(**location_scope(request, organization_id))
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        queryset = queryset.select_related('location')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = TableSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """Create a new table"""
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
        
        serializer = TableSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            table = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=TABLE_RETRIEVE_SCHEMA,
    put=TABLE_UPDATE_SCHEMA,
    patch=TABLE_UPDATE_SCHEMA,
    delete=TABLE_DELETE_SCHEMA,
)
class TableRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a table
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request, pk):
        """Get table by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        table = get_object_or_404(
            Table,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        serializer = TableSerializer(table, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update table"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        table = get_object_or_404(
            Table,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        # Verify location belongs to organization if changed
        location_id = request.data.get('location')
        if location_id:
            from apps.organizations.models import Location
            get_object_or_404(Location, id=location_id, **location_model_scope(request, organization_id))
        
        serializer = TableSerializer(
            table,
            data=request.data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            table = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Partial update table"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        table = get_object_or_404(
            Table,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        serializer = TableSerializer(
            table,
            data=request.data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            table = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete table"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        table = get_object_or_404(
            Table,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        # Check if table has active orders
        if table.orders.filter(is_active=True).exists():
            return Response(
                {"error": "Cannot delete table with active orders."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        table.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TableOccupyView(APIView):
    """
    View to occupy a table
    """
    permission_classes = [IsAuthenticated, CanOperatePOS]
    
    def post(self, request, pk):
        """Occupy a table"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        table = get_object_or_404(
            Table,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        if not table.is_available():
            return Response(
                {"error": f"Table {table.table_number} is not available."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        table.occupy()
        return Response({
            'id': table.id,
            'table_number': table.table_number,
            'status': table.status,
            'message': f'Table {table.table_number} is now occupied.'
        })


class TableFreeView(APIView):
    """
    View to free a table
    """
    permission_classes = [IsAuthenticated, CanOperatePOS]
    
    def post(self, request, pk):
        """Free a table"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        table = get_object_or_404(
            Table,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        if table.status != Table.TableStatus.OCCUPIED:
            return Response(
                {"error": f"Table {table.table_number} is not occupied."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        table.free()
        return Response({
            'id': table.id,
            'table_number': table.table_number,
            'status': table.status,
            'message': f'Table {table.table_number} is now available.'
        })


class AvailableTablesView(APIView):
    """
    View to get available tables
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request):
        """Get available tables"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        location_id = request.query_params.get('location', None)
        
        queryset = TableSelector.get_available_tables(location_id)
        queryset = queryset.filter(**location_scope(request, organization_id))
        
        serializer = TableSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)