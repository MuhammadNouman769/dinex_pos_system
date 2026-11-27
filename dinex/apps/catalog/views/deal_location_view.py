from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.permissions import IsAuthenticated

from apps.catalog.utils import get_user_organization_id
from apps.catalog.models import DealLocation, Deal
from apps.catalog.serializers.deal_location_serializer import DealLocationSerializer
from apps.catalog.selectors.deal_location_selector import DealLocationSelector
from apps.catalog.schemas.deal_location_schema import (
    DEAL_LOCATION_LIST_SCHEMA,
    DEAL_LOCATION_CREATE_SCHEMA,
    DEAL_LOCATION_RETRIEVE_SCHEMA,
    DEAL_LOCATION_UPDATE_SCHEMA,
    DEAL_LOCATION_DELETE_SCHEMA,
    DEAL_LOCATION_BULK_ASSIGN_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly
from apps.utils.pagination import StandardResultsSetPagination


# ============================================================
# DEAL LOCATION LIST & CREATE VIEW
# ============================================================

@extend_schema_view(
    get=DEAL_LOCATION_LIST_SCHEMA,
    post=DEAL_LOCATION_CREATE_SCHEMA,
)
class DealLocationListCreateView(APIView):
    """
    View to list and create deal location assignments
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Get all deal location assignments for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal_id = request.query_params.get('deal', None)
        location_id = request.query_params.get('location', None)
        only_enabled = request.query_params.get('enabled', 'true').lower() == 'true'
        
        queryset = DealLocationSelector.get_all_assignments(deal_id, location_id, only_enabled)
        queryset = queryset.filter(
            deal__organization_id=organization_id,
            location__organization_id=organization_id
        )
        queryset = queryset.select_related('deal', 'location').order_by('-id')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = DealLocationSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """Create a new deal location assignment"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify deal and location belong to organization
        deal_id = request.data.get('deal')
        location_id = request.data.get('location')
        
        if deal_id:
            get_object_or_404(Deal, id=deal_id, organization_id=organization_id)
        if location_id:
            from apps.organizations.models import Location
            get_object_or_404(Location, id=location_id, organization_id=organization_id)
        
        serializer = DealLocationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            assignment = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# DEAL LOCATION RETRIEVE, UPDATE & DELETE VIEW
# ============================================================

@extend_schema_view(
    get=DEAL_LOCATION_RETRIEVE_SCHEMA,
    put=DEAL_LOCATION_UPDATE_SCHEMA,
    patch=DEAL_LOCATION_UPDATE_SCHEMA,
    delete=DEAL_LOCATION_DELETE_SCHEMA,
)
class DealLocationRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a deal location assignment
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request, pk):
        """Get deal location assignment by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment = get_object_or_404(
            DealLocation,
            id=pk,
            deal__organization_id=organization_id,
            location__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = DealLocationSerializer(assignment, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update deal location assignment"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment = get_object_or_404(
            DealLocation,
            id=pk,
            deal__organization_id=organization_id,
            location__organization_id=organization_id,
            is_deleted=False
        )
        
        # Verify relationships belong to organization if changed
        deal_id = request.data.get('deal')
        location_id = request.data.get('location')
        
        if deal_id:
            get_object_or_404(Deal, id=deal_id, organization_id=organization_id)
        if location_id:
            from apps.organizations.models import Location
            get_object_or_404(Location, id=location_id, organization_id=organization_id)
        
        serializer = DealLocationSerializer(
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
        """Partial update deal location assignment"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment = get_object_or_404(
            DealLocation,
            id=pk,
            deal__organization_id=organization_id,
            location__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = DealLocationSerializer(
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
        """Soft delete deal location assignment"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment = get_object_or_404(
            DealLocation,
            id=pk,
            deal__organization_id=organization_id,
            location__organization_id=organization_id,
            is_deleted=False
        )
        
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================
# DEAL LOCATION BULK ASSIGN VIEW
# ============================================================

class DealLocationBulkAssignView(APIView):
    """
    View to bulk assign deals to locations
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    @transaction.atomic
    def post(self, request):
        """Bulk assign deals to locations"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deal_ids = request.data.get('deal_ids', [])
        location_ids = request.data.get('location_ids', [])
        is_enabled = request.data.get('is_enabled', True)
        
        if not deal_ids:
            return Response(
                {"error": "deal_ids list is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not location_ids:
            return Response(
                {"error": "location_ids list is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_assignments = []
        errors = []
        
        # Verify all deals and locations belong to organization
        from apps.organizations.models import Location
        for deal_id in deal_ids:
            get_object_or_404(Deal, id=deal_id, organization_id=organization_id)
        
        for location_id in location_ids:
            get_object_or_404(Location, id=location_id, organization_id=organization_id)
        
        # Create assignments
        for deal_id in deal_ids:
            for location_id in location_ids:
                data = {
                    'deal': deal_id,
                    'location': location_id,
                    'is_enabled': is_enabled
                }
                serializer = DealLocationSerializer(data=data, context={'request': request})
                if serializer.is_valid():
                    assignment = serializer.save()
                    created_assignments.append(assignment.id)
                else:
                    errors.append({
                        'deal_id': deal_id,
                        'location_id': location_id,
                        'errors': serializer.errors
                    })
        
        return Response({
            'message': f'Created {len(created_assignments)} assignments.',
            'assignment_ids': created_assignments,
            'errors': errors
        }, status=status.HTTP_201_CREATED if created_assignments else status.HTTP_400_BAD_REQUEST)