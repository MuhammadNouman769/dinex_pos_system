from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import Product
from apps.catalog.serializers.product_serializer import ProductSerializer
from apps.catalog.selectors.product_selector import ProductSelector
from apps.catalog.schemas.product_schema import (
    PRODUCT_LIST_SCHEMA,
    PRODUCT_CREATE_SCHEMA,
    PRODUCT_RETRIEVE_SCHEMA,
    PRODUCT_UPDATE_SCHEMA,
    PRODUCT_DELETE_SCHEMA,
    PRODUCT_BULK_CREATE_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly
from apps.utils.pagination import StandardResultsSetPagination
from apps.catalog.utils import get_user_organization_id


# ============================================================
# PRODUCT LIST & CREATE VIEW
# ============================================================


def _save_variants(product, variants_data, replace_missing=False):
    """Create/update variants. Invalid data raises a 400 (rolls back the request)
    instead of being silently skipped."""
    from rest_framework.exceptions import ValidationError
    from apps.catalog.serializers.variant_serializer import ProductVariantSerializer

    if not isinstance(variants_data, list):
        raise ValidationError({"variants": "Must be a list."})

    if replace_missing:
        keep_ids = [v.get("id") for v in variants_data if isinstance(v, dict) and v.get("id")]
        if keep_ids:
            product.variants.exclude(id__in=keep_ids).delete()

    errors = []
    for index, raw in enumerate(variants_data):
        if not isinstance(raw, dict):
            errors.append({"index": index, "errors": "Must be an object."})
            continue
        variant_data = {**raw, "product": product.id}
        instance = None
        if variant_data.get("id"):
            instance = product.variants.filter(id=variant_data["id"]).first()
            if instance is None:
                errors.append({"index": index, "errors": "Variant not found on this product."})
                continue
        serializer = ProductVariantSerializer(instance, data=variant_data)
        if serializer.is_valid():
            serializer.save()
        else:
            errors.append({"index": index, "errors": serializer.errors})
    if errors:
        raise ValidationError({"variants": errors})


def _set_dietary_tags(product, tag_ids, organization_id):
    """Only tags owned by the same organization may be attached."""
    from rest_framework.exceptions import ValidationError
    from apps.catalog.models import DietaryTag

    if not isinstance(tag_ids, list):
        raise ValidationError({"dietary_tags": "Must be a list of ids."})
    try:
        tag_ids = [int(t) for t in tag_ids]
    except (TypeError, ValueError):
        raise ValidationError({"dietary_tags": "Must be a list of ids."})
    tags = DietaryTag.objects.filter(organization_id=organization_id, id__in=tag_ids)
    if tags.count() != len(set(tag_ids)):
        raise ValidationError({"dietary_tags": "One or more tags do not exist."})
    product.dietary_tags.set(tags)


@extend_schema_view(
    get=PRODUCT_LIST_SCHEMA,
    post=PRODUCT_CREATE_SCHEMA,
)
class ProductListCreateView(APIView):
    """
    View to list and create products
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Get all products for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get query parameters
        only_active = request.query_params.get('active', 'true').lower() == 'true'
        search_term = request.query_params.get('search', None)
        category_id = request.query_params.get('category', None)
        product_type = request.query_params.get('type', None)
        location_id = request.query_params.get('location', None)
        
        queryset = ProductSelector.get_all_products(organization_id, only_active)
        
        # Apply filters
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        if product_type:
            queryset = queryset.filter(product_type=product_type)
        
        if location_id:
            queryset = queryset.filter(
                location_assignments__location_id=location_id,
                location_assignments__is_available=True
            )
        
        if search_term:
            queryset = ProductSelector.search_products(organization_id, search_term)
        
        # Prefetch related data
        queryset = queryset.select_related('category', 'organization').prefetch_related(
            'variants', 'dietary_tags'
        )
        
        # Paginate
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProductSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    @transaction.atomic
    def post(self, request):
        """Create a new product"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = ProductSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            product = serializer.save()
            
            variants_data = request.data.get('variants')
            if variants_data:
                _save_variants(product, variants_data)

            if request.data.get('dietary_tags'):
                _set_dietary_tags(product, request.data.get('dietary_tags'), organization_id)

            # Refresh to get all data
            product = ProductSelector.get_product_with_details(product.id)
            response_serializer = ProductSerializer(product, context={'request': request})
            
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# PRODUCT RETRIEVE, UPDATE & DELETE VIEW
# ============================================================

@extend_schema_view(
    get=PRODUCT_RETRIEVE_SCHEMA,
    put=PRODUCT_UPDATE_SCHEMA,
    patch=PRODUCT_UPDATE_SCHEMA,
    delete=PRODUCT_DELETE_SCHEMA,
)
class ProductRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a product
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request, pk):
        """Get product by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        product = get_object_or_404(
            Product,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        product = ProductSelector.get_product_with_details(product.id)
        serializer = ProductSerializer(product, context={'request': request})
        
        return Response(serializer.data)
    
    @transaction.atomic
    def put(self, request, pk):
        """Update product"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        product = get_object_or_404(
            Product,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = ProductSerializer(
            product, 
            data=data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            product = serializer.save()
            
            variants_data = request.data.get('variants')
            if variants_data:
                _save_variants(product, variants_data, replace_missing=True)

            if 'dietary_tags' in request.data:
                _set_dietary_tags(product, request.data.get('dietary_tags') or [], organization_id)

            product = ProductSelector.get_product_with_details(product.id)
            response_serializer = ProductSerializer(product, context={'request': request})
            
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def patch(self, request, pk):
        """Partial update product"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        product = get_object_or_404(
            Product,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = ProductSerializer(
            product, 
            data=data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            product = serializer.save()
            
            # Update dietary tags if provided
            if request.data.get('dietary_tags') is not None:
                _set_dietary_tags(product, request.data.get('dietary_tags'), organization_id)
            
            product = ProductSelector.get_product_with_details(product.id)
            response_serializer = ProductSerializer(product, context={'request': request})
            
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Soft delete product"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        product = get_object_or_404(
            Product,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        # Check if product has active variants
        if product.variants.filter(is_active=True).exists():
            return Response(
                {"error": "Cannot delete product with active variants."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================
# PRODUCT BULK CREATE VIEW
# ============================================================

class ProductBulkCreateView(APIView):
    """
    View to bulk create products
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    @transaction.atomic
    def post(self, request):
        """Bulk create products"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        products_data = request.data.get('products', [])
        
        if not products_data:
            return Response(
                {"error": "products list is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_products = []
        errors = []
        
        for product_data in products_data:
            product_data['organization'] = organization_id
            serializer = ProductSerializer(data=product_data, context={'request': request})
            
            if serializer.is_valid():
                product = serializer.save()
                created_products.append(product.id)
            else:
                errors.append({
                    'data': product_data,
                    'errors': serializer.errors
                })
        
        return Response({
            'message': f'Created {len(created_products)} products.',
            'product_ids': created_products,
            'errors': errors
        }, status=status.HTTP_201_CREATED if created_products else status.HTTP_400_BAD_REQUEST)