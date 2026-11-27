from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import Deal, DealItem, DealLocation
from apps.catalog.serializers.deal_serializer import DealSerializer
from apps.catalog.selectors.deal_selector import DealSelector
from apps.catalog.schemas.deal_schema import (
    DEAL_LIST_SCHEMA,
    DEAL_CREATE_SCHEMA,
    DEAL_RETRIEVE_SCHEMA,
    DEAL_UPDATE_SCHEMA,
    DEAL_DELETE_SCHEMA,
    DEAL_TOGGLE_ACTIVE_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly
from apps.utils.pagination import StandardResultsSetPagination
from apps.catalog.utils import get_user_organization_id


# ============================================================
# DEAL LIST & CREATE VIEW
# ============================================================

@extend_schema_view(
    get=DEAL_LIST_SCHEMA,
    post=DEAL_CREATE_SCHEMA,
)
class DealListCreateView(APIView):
    """
    View to list and create deals
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Get all deals for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        only_active = request.query_params.get('active', 'true').lower() == 'true'
        search_term = request.query_params.get('search', None)
        location_id = request.query_params.get('location', None)
        show_active_only = request.query_params.get('active_deals', 'false').lower() == 'true'
        
        if show_active_only:
            queryset = DealSelector.get_active_deals(organization_id)
        else:
            queryset = DealSelector.get_all_deals(organization_id, only_active)
        
        if location_id:
            queryset = queryset.filter(
                locations__location_id=location_id,
                locations__is_enabled=True
            )
        
        if search_term:
            queryset = DealSelector.search_deals(organization_id, search_term)
        
        queryset = queryset.prefetch_related('items', 'locations').order_by('-id')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = DealSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    @transaction.atomic
    def post(self, request):
        """Create a new deal"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = DealSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            deal = serializer.save()
            
            # Handle items if provided
            items_data = request.data.get('items', [])
            if items_data:
                from apps.catalog.serializers.deal_item_serializer import DealItemSerializer
                for item_data in items_data:
                    item_data['deal'] = deal.id
                    item_serializer = DealItemSerializer(data=item_data)
                    if item_serializer.is_valid():
                        item_serializer.save()
            
            # Handle locations if provided
            locations_data = request.data.get('locations', [])
            if locations_data:
                from apps.catalog.serializers.deal_location_serializer import DealLocationSerializer
                for location_data in locations_data:
                    location_data['deal'] = deal.id
                    location_serializer = DealLocationSerializer(data=location_data)
                    if location_serializer.is_valid():
                        location_serializer.save()
            
            # Refresh to get all data
            deal = DealSelector.get_deal_with_details(deal.id)
            response_serializer = DealSerializer(deal, context={'request': request})
            
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# DEAL RETRIEVE, UPDATE & DELETE VIEW
# ============================================================

@extend_schema_view(
    get=DEAL_RETRIEVE_SCHEMA,
    put=DEAL_UPDATE_SCHEMA,
    patch=DEAL_UPDATE_SCHEMA,
    delete=DEAL_DELETE_SCHEMA,
)
class DealRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a deal
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request, pk):
        """Get deal by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal = get_object_or_404(
            Deal,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        deal = DealSelector.get_deal_with_details(deal.id)
        serializer = DealSerializer(deal, context={'request': request})
        
        return Response(serializer.data)
    
    @transaction.atomic
    def put(self, request, pk):
        """Update deal"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal = get_object_or_404(
            Deal,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = DealSerializer(
            deal, 
            data=data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            deal = serializer.save()
            
            # Handle items if provided
            items_data = request.data.get('items', [])
            if items_data:
                from apps.catalog.serializers.deal_item_serializer import DealItemSerializer
                # Delete existing items not in the list
                existing_item_ids = [i.get('id') for i in items_data if i.get('id')]
                if existing_item_ids:
                    deal.items.exclude(id__in=existing_item_ids).delete()
                
                for item_data in items_data:
                    item_data['deal'] = deal.id
                    if item_data.get('id'):
                        item = deal.items.filter(id=item_data['id']).first()
                        if item:
                            item_serializer = DealItemSerializer(item, data=item_data)
                            if item_serializer.is_valid():
                                item_serializer.save()
                    else:
                        item_serializer = DealItemSerializer(data=item_data)
                        if item_serializer.is_valid():
                            item_serializer.save()
            
            # Handle locations if provided
            locations_data = request.data.get('locations', [])
            if locations_data:
                from apps.catalog.serializers.deal_location_serializer import DealLocationSerializer
                existing_location_ids = [l.get('id') for l in locations_data if l.get('id')]
                if existing_location_ids:
                    deal.locations.exclude(id__in=existing_location_ids).delete()
                
                for location_data in locations_data:
                    location_data['deal'] = deal.id
                    if location_data.get('id'):
                        location = deal.locations.filter(id=location_data['id']).first()
                        if location:
                            location_serializer = DealLocationSerializer(location, data=location_data)
                            if location_serializer.is_valid():
                                location_serializer.save()
                    else:
                        location_serializer = DealLocationSerializer(data=location_data)
                        if location_serializer.is_valid():
                            location_serializer.save()
            
            deal = DealSelector.get_deal_with_details(deal.id)
            response_serializer = DealSerializer(deal, context={'request': request})
            
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def patch(self, request, pk):
        """Partial update deal"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal = get_object_or_404(
            Deal,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = DealSerializer(
            deal, 
            data=data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            deal = serializer.save()
            deal = DealSelector.get_deal_with_details(deal.id)
            response_serializer = DealSerializer(deal, context={'request': request})
            
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete deal"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal = get_object_or_404(
            Deal,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        deal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================
# DEAL TOGGLE ACTIVE VIEW
# ============================================================

class DealToggleActiveView(APIView):
    """
    View to toggle deal active status
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def post(self, request, pk):
        """Toggle deal active status"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal = get_object_or_404(
            Deal,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        deal.is_active = not deal.is_active
        deal.save()
        
        return Response({
            'id': deal.id,
            'is_active': deal.is_active,
            'message': f'Deal {"activated" if deal.is_active else "deactivated"} successfully.'
        })