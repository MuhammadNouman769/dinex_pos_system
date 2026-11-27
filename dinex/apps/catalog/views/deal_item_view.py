from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.permissions import IsAuthenticated

from apps.catalog.utils import get_user_organization_id
from apps.catalog.models import DealItem, Deal, ProductVariant
from apps.catalog.serializers.deal_item_serializer import DealItemSerializer
from apps.catalog.selectors.deal_item_selector import DealItemSelector
from apps.catalog.schemas.deal_item_schema import (
    DEAL_ITEM_LIST_SCHEMA,
    DEAL_ITEM_CREATE_SCHEMA,
    DEAL_ITEM_RETRIEVE_SCHEMA,
    DEAL_ITEM_UPDATE_SCHEMA,
    DEAL_ITEM_DELETE_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly
from apps.utils.pagination import StandardResultsSetPagination


# ============================================================
# DEAL ITEM LIST & CREATE VIEW
# ============================================================

@extend_schema_view(
    get=DEAL_ITEM_LIST_SCHEMA,
    post=DEAL_ITEM_CREATE_SCHEMA,
)
class DealItemListCreateView(APIView):
    """
    View to list and create deal items
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        """Get all deal items for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal_id = request.query_params.get('deal', None)
        variant_id = request.query_params.get('variant', None)
        
        queryset = DealItemSelector.get_all_items(deal_id, variant_id)
        queryset = queryset.filter(
            deal__organization_id=organization_id,
            product_variant__product__organization_id=organization_id
        )
        queryset = queryset.select_related('deal', 'product_variant', 'product_variant__product').order_by('-id')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = DealItemSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """Create a new deal item"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify deal and variant belong to organization
        deal_id = request.data.get('deal')
        variant_id = request.data.get('product_variant')
        
        if deal_id:
            get_object_or_404(Deal, id=deal_id, organization_id=organization_id)
        if variant_id:
            get_object_or_404(
                ProductVariant, 
                id=variant_id, 
                product__organization_id=organization_id
            )
        
        serializer = DealItemSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            deal_item = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# DEAL ITEM RETRIEVE, UPDATE & DELETE VIEW
# ============================================================

@extend_schema_view(
    get=DEAL_ITEM_RETRIEVE_SCHEMA,
    put=DEAL_ITEM_UPDATE_SCHEMA,
    patch=DEAL_ITEM_UPDATE_SCHEMA,
    delete=DEAL_ITEM_DELETE_SCHEMA,
)
class DealItemRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a deal item
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request, pk):
        """Get deal item by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal_item = get_object_or_404(
            DealItem,
            id=pk,
            deal__organization_id=organization_id,
            product_variant__product__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = DealItemSerializer(deal_item, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update deal item"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal_item = get_object_or_404(
            DealItem,
            id=pk,
            deal__organization_id=organization_id,
            product_variant__product__organization_id=organization_id,
            is_deleted=False
        )
        
        # Verify relationships belong to organization if changed
        deal_id = request.data.get('deal')
        variant_id = request.data.get('product_variant')
        
        if deal_id:
            get_object_or_404(Deal, id=deal_id, organization_id=organization_id)
        if variant_id:
            get_object_or_404(
                ProductVariant, 
                id=variant_id, 
                product__organization_id=organization_id
            )
        
        serializer = DealItemSerializer(
            deal_item, 
            data=request.data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            deal_item = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Partial update deal item"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal_item = get_object_or_404(
            DealItem,
            id=pk,
            deal__organization_id=organization_id,
            product_variant__product__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = DealItemSerializer(
            deal_item, 
            data=request.data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            deal_item = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete deal item"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal_item = get_object_or_404(
            DealItem,
            id=pk,
            deal__organization_id=organization_id,
            product_variant__product__organization_id=organization_id,
            is_deleted=False
        )
        
        deal_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)