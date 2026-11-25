from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from apps.customers.models.customer import Customer
from apps.customers.serializers.customer_serializer import CustomerSerializer
from apps.customers.selectors.customer_selector import CustomerSelector
from apps.customers.schemas.customer_schema import (
    CUSTOMER_LIST_SCHEMA,
    CUSTOMER_CREATE_SCHEMA,
    CUSTOMER_RETRIEVE_SCHEMA,
    CUSTOMER_UPDATE_SCHEMA,
    CUSTOMER_DELETE_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly, CanOperatePOS
from apps.utils.pagination import StandardResultsSetPagination
from apps.catalog.utils import get_user_organization_id
from apps.utils.helpers import location_scope, location_model_scope


@extend_schema_view(
    get=CUSTOMER_LIST_SCHEMA,
    post=CUSTOMER_CREATE_SCHEMA,
)
class CustomerListCreateView(APIView):
    """
    View to list and create customers
    """
    permission_classes = [IsAuthenticated, CanOperatePOS]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Get all customers for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get location_id from query or get all locations
        location_id = request.query_params.get('location', None)
        only_active = request.query_params.get('active', 'true').lower() == 'true'
        search_term = request.query_params.get('search', None)
        
        # Start from the caller's organization; filters only narrow it.
        queryset = Customer.objects.filter(**location_scope(request, organization_id))

        if location_id:
            try:
                queryset = queryset.filter(location_id=int(location_id))
            except (TypeError, ValueError):
                return Response({"error": "Invalid location id."}, status=status.HTTP_400_BAD_REQUEST)

        if only_active:
            queryset = queryset.filter(is_active=True)

        if search_term:
            queryset = CustomerSelector.filter_search(queryset, search_term)

        queryset = queryset.select_related('location')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = CustomerSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """Create a new customer"""
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
        
        serializer = CustomerSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            customer = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=CUSTOMER_RETRIEVE_SCHEMA,
    put=CUSTOMER_UPDATE_SCHEMA,
    patch=CUSTOMER_UPDATE_SCHEMA,
    delete=CUSTOMER_DELETE_SCHEMA,
)
class CustomerRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a customer
    """
    permission_classes = [IsAuthenticated, CanOperatePOS]
    
    def get(self, request, pk):
        """Get customer by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        customer = get_object_or_404(
            Customer,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        serializer = CustomerSerializer(customer, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update customer"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        customer = get_object_or_404(
            Customer,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        # Verify location belongs to organization if changed
        location_id = request.data.get('location')
        if location_id:
            from apps.organizations.models import Location
            get_object_or_404(Location, id=location_id, **location_model_scope(request, organization_id))
        
        serializer = CustomerSerializer(
            customer,
            data=request.data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            customer = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Partial update customer"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        customer = get_object_or_404(
            Customer,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        serializer = CustomerSerializer(
            customer,
            data=request.data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            customer = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete customer"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        customer = get_object_or_404(
            Customer,
            id=pk,
            **location_scope(request, organization_id),
            is_deleted=False
        )
        
        # Check if customer has orders
        if customer.orders.filter(is_deleted=False).exists():
            return Response(
                {"error": "Cannot delete customer with active orders."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        customer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)