from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import ProductVariant, Product
from apps.catalog.serializers.variant_serializer import ProductVariantSerializer
from apps.catalog.selectors.variant_selector import VariantSelector
from apps.catalog.schemas.variant_schema import (
    VARIANT_LIST_SCHEMA,
    VARIANT_CREATE_SCHEMA,
    VARIANT_RETRIEVE_SCHEMA,
    VARIANT_UPDATE_SCHEMA,
    VARIANT_DELETE_SCHEMA,
    VARIANT_BULK_CREATE_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly
from apps.utils.pagination import StandardResultsSetPagination
from apps.catalog.utils import get_user_organization_id


# ============================================================
# VARIANT LIST & CREATE VIEW
# ============================================================

@extend_schema_view(
    get=VARIANT_LIST_SCHEMA,
    post=VARIANT_CREATE_SCHEMA,
)
class VariantListCreateView(APIView):
    """
    View to list and create variants
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Get all variants for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        product_id = request.query_params.get('product', None)
        only_active = request.query_params.get('active', 'true').lower() == 'true'
        search_term = request.query_params.get('search', None)
        
        queryset = VariantSelector.get_all_variants(product_id, only_active)
        queryset = queryset.filter(product__organization_id=organization_id)
        
        if search_term:
            queryset = VariantSelector.search_variants(search_term, product_id)
        
        queryset = queryset.select_related('product')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProductVariantSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """Create a new variant"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify product belongs to organization
        product_id = request.data.get('product')
        if product_id:
            get_object_or_404(Product, id=product_id, organization_id=organization_id)
        
        serializer = ProductVariantSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            variant = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# VARIANT RETRIEVE, UPDATE & DELETE VIEW
# ============================================================

@extend_schema_view(
    get=VARIANT_RETRIEVE_SCHEMA,
    put=VARIANT_UPDATE_SCHEMA,
    patch=VARIANT_UPDATE_SCHEMA,
    delete=VARIANT_DELETE_SCHEMA,
)
class VariantRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a variant
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request, pk):
        """Get variant by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        variant = get_object_or_404(
            ProductVariant,
            id=pk,
            product__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = ProductVariantSerializer(variant, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update variant"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        variant = get_object_or_404(
            ProductVariant,
            id=pk,
            product__organization_id=organization_id,
            is_deleted=False
        )
        
        # Verify product belongs to organization if product is being changed
        product_id = request.data.get('product')
        if product_id:
            get_object_or_404(Product, id=product_id, organization_id=organization_id)
        
        serializer = ProductVariantSerializer(
            variant, 
            data=request.data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            variant = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Partial update variant"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        variant = get_object_or_404(
            ProductVariant,
            id=pk,
            product__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = ProductVariantSerializer(
            variant, 
            data=request.data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            variant = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete variant"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        variant = get_object_or_404(
            ProductVariant,
            id=pk,
            product__organization_id=organization_id,
            is_deleted=False
        )
        
        # Check if variant is used in deals
        if variant.deal_items.filter(deal__is_active=True).exists():
            return Response(
                {"error": "Cannot delete variant that is used in active deals."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        variant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================
# VARIANT BULK CREATE VIEW
# ============================================================

class VariantBulkCreateView(APIView):
    """
    View to bulk create variants for a product
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    @transaction.atomic
    def post(self, request):
        """Bulk create variants"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        product_id = request.data.get('product_id')
        variants_data = request.data.get('variants', [])
        
        if not product_id:
            return Response(
                {"error": "product_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify product belongs to organization
        get_object_or_404(Product, id=product_id, organization_id=organization_id)
        
        if not variants_data:
            return Response(
                {"error": "variants list is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_variants = []
        errors = []
        
        for variant_data in variants_data:
            variant_data['product'] = product_id
            serializer = ProductVariantSerializer(data=variant_data, context={'request': request})
            
            if serializer.is_valid():
                variant = serializer.save()
                created_variants.append(variant.id)
            else:
                errors.append({
                    'data': variant_data,
                    'errors': serializer.errors
                })
        
        return Response({
            'message': f'Created {len(created_variants)} variants.',
            'variant_ids': created_variants,
            'errors': errors
        }, status=status.HTTP_201_CREATED if created_variants else status.HTTP_400_BAD_REQUEST)