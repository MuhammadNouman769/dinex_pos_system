from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import ProductModifierGroup, Product, ModifierGroup
from apps.catalog.serializers.product_modifier_group_serializer import ProductModifierGroupSerializer
from apps.catalog.selectors.product_modifier_group_selector import ProductModifierGroupSelector
from apps.catalog.schemas.product_modifier_group_schema import (
    PRODUCT_MODIFIER_GROUP_LIST_SCHEMA,
    PRODUCT_MODIFIER_GROUP_CREATE_SCHEMA,
    PRODUCT_MODIFIER_GROUP_RETRIEVE_SCHEMA,
    PRODUCT_MODIFIER_GROUP_UPDATE_SCHEMA,
    PRODUCT_MODIFIER_GROUP_DELETE_SCHEMA,
    PRODUCT_MODIFIER_GROUP_BULK_CREATE_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly
from apps.catalog.utils import get_user_organization_id


# ============================================================
# PRODUCT MODIFIER GROUP LIST & CREATE VIEW
# ============================================================

@extend_schema_view(
    get=PRODUCT_MODIFIER_GROUP_LIST_SCHEMA,
    post=PRODUCT_MODIFIER_GROUP_CREATE_SCHEMA,
)
class ProductModifierGroupListCreateView(APIView):
    """
    View to list and create product-modifier group links
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request):
        """Get all product-modifier group links"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        product_id = request.query_params.get('product', None)
        modifier_group_id = request.query_params.get('modifier_group', None)
        
        queryset = ProductModifierGroupSelector.get_all_links(product_id, modifier_group_id)
        queryset = queryset.filter(
            product__organization_id=organization_id,
            modifier_group__organization_id=organization_id
        )
        queryset = queryset.select_related('product', 'modifier_group')
        
        serializer = ProductModifierGroupSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request):
        """Create a new product-modifier group link"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify product and modifier group belong to organization
        product_id = request.data.get('product')
        modifier_group_id = request.data.get('modifier_group')
        
        if product_id:
            get_object_or_404(Product, id=product_id, organization_id=organization_id)
        if modifier_group_id:
            get_object_or_404(ModifierGroup, id=modifier_group_id, organization_id=organization_id)
        
        serializer = ProductModifierGroupSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            link = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# PRODUCT MODIFIER GROUP RETRIEVE, UPDATE & DELETE VIEW
# ============================================================

@extend_schema_view(
    get=PRODUCT_MODIFIER_GROUP_RETRIEVE_SCHEMA,
    put=PRODUCT_MODIFIER_GROUP_UPDATE_SCHEMA,
    patch=PRODUCT_MODIFIER_GROUP_UPDATE_SCHEMA,
    delete=PRODUCT_MODIFIER_GROUP_DELETE_SCHEMA,
)
class ProductModifierGroupRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a product-modifier group link
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request, pk):
        """Get product-modifier group link by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        link = get_object_or_404(
            ProductModifierGroup,
            id=pk,
            product__organization_id=organization_id,
            modifier_group__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = ProductModifierGroupSerializer(link, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update product-modifier group link"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        link = get_object_or_404(
            ProductModifierGroup,
            id=pk,
            product__organization_id=organization_id,
            modifier_group__organization_id=organization_id,
            is_deleted=False
        )
        
        # Verify product and modifier group belong to organization if changed
        product_id = request.data.get('product')
        modifier_group_id = request.data.get('modifier_group')
        
        if product_id:
            get_object_or_404(Product, id=product_id, organization_id=organization_id)
        if modifier_group_id:
            get_object_or_404(ModifierGroup, id=modifier_group_id, organization_id=organization_id)
        
        serializer = ProductModifierGroupSerializer(
            link, 
            data=request.data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            link = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Partial update product-modifier group link"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        link = get_object_or_404(
            ProductModifierGroup,
            id=pk,
            product__organization_id=organization_id,
            modifier_group__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = ProductModifierGroupSerializer(
            link, 
            data=request.data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            link = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete product-modifier group link"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        link = get_object_or_404(
            ProductModifierGroup,
            id=pk,
            product__organization_id=organization_id,
            modifier_group__organization_id=organization_id,
            is_deleted=False
        )
        
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================
# PRODUCT MODIFIER GROUP BULK CREATE VIEW
# ============================================================

class ProductModifierGroupBulkCreateView(APIView):
    """
    View to bulk create product-modifier group links
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    @transaction.atomic
    def post(self, request):
        """Bulk create product-modifier group links"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        product_id = request.data.get('product_id')
        modifier_group_ids = request.data.get('modifier_group_ids', [])
        
        if not product_id:
            return Response(
                {"error": "product_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify product belongs to organization
        get_object_or_404(Product, id=product_id, organization_id=organization_id)
        
        if not modifier_group_ids:
            return Response(
                {"error": "modifier_group_ids list is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_links = []
        errors = []
        
        for modifier_group_id in modifier_group_ids:
            # Verify modifier group belongs to organization
            get_object_or_404(ModifierGroup, id=modifier_group_id, organization_id=organization_id)
            
            data = {
                'product': product_id,
                'modifier_group': modifier_group_id
            }
            
            serializer = ProductModifierGroupSerializer(data=data, context={'request': request})
            if serializer.is_valid():
                link = serializer.save()
                created_links.append(link.id)
            else:
                errors.append({
                    'modifier_group_id': modifier_group_id,
                    'errors': serializer.errors
                })
        
        return Response({
            'message': f'Created {len(created_links)} links.',
            'link_ids': created_links,
            'errors': errors
        }, status=status.HTTP_201_CREATED if created_links else status.HTTP_400_BAD_REQUEST)