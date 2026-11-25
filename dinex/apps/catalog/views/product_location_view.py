from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import ProductLocation, Product, ProductVariant
from apps.catalog.serializers.product_location_serializer import ProductLocationSerializer
from apps.catalog.selectors.product_location_selector import ProductLocationSelector
from apps.catalog.schemas.product_location_schema import (
    PRODUCT_LOCATION_LIST_SCHEMA,
    PRODUCT_LOCATION_CREATE_SCHEMA,
    PRODUCT_LOCATION_RETRIEVE_SCHEMA,
    PRODUCT_LOCATION_UPDATE_SCHEMA,
    PRODUCT_LOCATION_DELETE_SCHEMA,
    PRODUCT_LOCATION_BULK_ASSIGN_SCHEMA,
)
from apps.utils.permissions import user_can_manage_location_catalog
from apps.utils.pagination import StandardResultsSetPagination
from apps.catalog.utils import get_user_organization_id


# ============================================================
# PRODUCT LOCATION LIST & CREATE VIEW
# ============================================================

@extend_schema_view(
    get=PRODUCT_LOCATION_LIST_SCHEMA,
    post=PRODUCT_LOCATION_CREATE_SCHEMA,
)
class ProductLocationListCreateView(APIView):
    """
    View to list and create product location assignments
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        """Get all product location assignments for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        product_id = request.query_params.get('product', None)
        location_id = request.query_params.get('location', None)
        only_available = request.query_params.get('available', 'true').lower() == 'true'
        
        queryset = ProductLocationSelector.get_all_assignments(
            product_id, location_id, only_available
        )
        queryset = queryset.filter(
            product__organization_id=organization_id,
            location__organization_id=organization_id
        )
        queryset = queryset.select_related('product', 'product_variant', 'location')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProductLocationSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """Create a new product location assignment"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify product belongs to organization
        product_id = request.data.get('product')
        product_variant_id = request.data.get('product_variant')
        location_id = request.data.get('location')
        
        if product_id:
            get_object_or_404(Product, id=product_id, organization_id=organization_id)
        
        if product_variant_id:
            variant = get_object_or_404(
                ProductVariant, 
                id=product_variant_id, 
                product__organization_id=organization_id
            )
            # If product is also provided, ensure variant belongs to it
            if product_id and variant.product_id != product_id:
                return Response(
                    {"error": "Variant does not belong to the specified product."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if location_id:
            from apps.organizations.models import Location
            get_object_or_404(Location, id=location_id, organization_id=organization_id)

        if not user_can_manage_location_catalog(request.user, organization_id, location_id):
            return Response(
                {"error": "You do not have permission to manage this location's catalog."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProductLocationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            assignment = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# PRODUCT LOCATION RETRIEVE, UPDATE & DELETE VIEW
# ============================================================

@extend_schema_view(
    get=PRODUCT_LOCATION_RETRIEVE_SCHEMA,
    put=PRODUCT_LOCATION_UPDATE_SCHEMA,
    patch=PRODUCT_LOCATION_UPDATE_SCHEMA,
    delete=PRODUCT_LOCATION_DELETE_SCHEMA,
)
class ProductLocationRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a product location assignment
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get product location assignment by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment = get_object_or_404(
            ProductLocation,
            id=pk,
            product__organization_id=organization_id,
            location__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = ProductLocationSerializer(assignment, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update product location assignment"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment = get_object_or_404(
            ProductLocation,
            id=pk,
            product__organization_id=organization_id,
            location__organization_id=organization_id,
            is_deleted=False
        )
        
        if not user_can_manage_location_catalog(request.user, organization_id, assignment.location_id):
            return Response(
                {"error": "You do not have permission to manage this location's catalog."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Verify updated relationships belong to organization
        product_id = request.data.get('product')
        product_variant_id = request.data.get('product_variant')
        location_id = request.data.get('location')

        if product_id:
            get_object_or_404(Product, id=product_id, organization_id=organization_id)
        if product_variant_id:
            get_object_or_404(
                ProductVariant,
                id=product_variant_id,
                product__organization_id=organization_id
            )
        if location_id:
            from apps.organizations.models import Location
            get_object_or_404(Location, id=location_id, organization_id=organization_id)

            if not user_can_manage_location_catalog(request.user, organization_id, location_id):
                return Response(
                    {"error": "You do not have permission to reassign this record to that location."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = ProductLocationSerializer(
            assignment,
            data=request.data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            assignment = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Partial update product location assignment"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment = get_object_or_404(
            ProductLocation,
            id=pk,
            product__organization_id=organization_id,
            location__organization_id=organization_id,
            is_deleted=False
        )
        
        if not user_can_manage_location_catalog(request.user, organization_id, assignment.location_id):
            return Response(
                {"error": "You do not have permission to manage this location's catalog."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProductLocationSerializer(
            assignment,
            data=request.data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            assignment = serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete product location assignment"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment = get_object_or_404(
            ProductLocation,
            id=pk,
            product__organization_id=organization_id,
            location__organization_id=organization_id,
            is_deleted=False
        )
        
        if not user_can_manage_location_catalog(request.user, organization_id, assignment.location_id):
            return Response(
                {"error": "You do not have permission to manage this location's catalog."},
                status=status.HTTP_403_FORBIDDEN
            )

        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================
# PRODUCT LOCATION BULK ASSIGN VIEW
# ============================================================

class ProductLocationBulkAssignView(APIView):
    """
    View to bulk assign products/variants to locations
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        """Bulk assign products to locations"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        product_ids = request.data.get('product_ids', [])
        variant_ids = request.data.get('variant_ids', [])
        location_ids = request.data.get('location_ids', [])
        is_available = request.data.get('is_available', True)
        available_quantity = request.data.get('available_quantity', 0)
        
        if not product_ids and not variant_ids:
            return Response(
                {"error": "Either product_ids or variant_ids must be provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not location_ids:
            return Response(
                {"error": "location_ids list is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_assignments = []
        errors = []

        # Verify all locations belong to organization, and that the
        # caller may manage each one (org owner/platform, or that
        # location's manager)
        from apps.organizations.models import Location
        for location_id in location_ids:
            get_object_or_404(Location, id=location_id, organization_id=organization_id)

            if not user_can_manage_location_catalog(request.user, organization_id, location_id):
                return Response(
                    {"error": f"You do not have permission to manage location {location_id}."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Assign products
        for product_id in product_ids:
            get_object_or_404(Product, id=product_id, organization_id=organization_id)
            for location_id in location_ids:
                data = {
                    'product': product_id,
                    'location': location_id,
                    'is_available': is_available,
                    'available_quantity': available_quantity
                }
                serializer = ProductLocationSerializer(data=data, context={'request': request})
                if serializer.is_valid():
                    assignment = serializer.save()
                    created_assignments.append(assignment.id)
                else:
                    errors.append({
                        'product_id': product_id,
                        'location_id': location_id,
                        'errors': serializer.errors
                    })
        
        # Assign variants
        for variant_id in variant_ids:
            variant = get_object_or_404(
                ProductVariant, 
                id=variant_id, 
                product__organization_id=organization_id
            )
            for location_id in location_ids:
                data = {
                    'product_variant': variant_id,
                    'product': variant.product_id,
                    'location': location_id,
                    'is_available': is_available,
                    'available_quantity': available_quantity
                }
                serializer = ProductLocationSerializer(data=data, context={'request': request})
                if serializer.is_valid():
                    assignment = serializer.save()
                    created_assignments.append(assignment.id)
                else:
                    errors.append({
                        'variant_id': variant_id,
                        'location_id': location_id,
                        'errors': serializer.errors
                    })
        
        return Response({
            'message': f'Created {len(created_assignments)} assignments.',
            'assignment_ids': created_assignments,
            'errors': errors
        }, status=status.HTTP_201_CREATED if created_assignments else status.HTTP_400_BAD_REQUEST)