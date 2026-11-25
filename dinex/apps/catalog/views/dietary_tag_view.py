from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import DietaryTag
from apps.catalog.serializers.dietary_tag_serializer import DietaryTagSerializer
from apps.catalog.selectors.dietary_tag_selector import DietaryTagSelector
from apps.catalog.schemas.dietary_tag_schema import (
    DIETARY_TAG_LIST_SCHEMA,
    DIETARY_TAG_CREATE_SCHEMA,
    DIETARY_TAG_RETRIEVE_SCHEMA,
    DIETARY_TAG_UPDATE_SCHEMA,
    DIETARY_TAG_DELETE_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly
from apps.utils.pagination import StandardResultsSetPagination


# ============================================================
# HELPER FUNCTION - Get Organization ID
# ============================================================

def get_user_organization_id(request):
    """
    Helper to get organization_id from user.
    If not set, fetch from membership and set it.
    """
    organization_id = getattr(request.user, 'organization_id', None)
    
    if not organization_id:
        from apps.organizations.models import OrganizationMembership
        membership = OrganizationMembership.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('organization').first()
        
        if membership:
            organization_id = membership.organization_id
            request.user.organization_id = organization_id
            request.user.organization = membership.organization
    return organization_id


# ============================================================
# DIETARY TAG LIST & CREATE VIEW
# ============================================================

@extend_schema_view(
    get=DIETARY_TAG_LIST_SCHEMA,
    post=DIETARY_TAG_CREATE_SCHEMA,
)
class DietaryTagListCreateView(APIView):
    """
    View to list and create dietary tags
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        """Get all dietary tags for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        only_active = request.query_params.get('active', 'true').lower() == 'true'
        search_term = request.query_params.get('search', None)
        
        if search_term:
            queryset = DietaryTagSelector.search_tags(organization_id, search_term)
        else:
            queryset = DietaryTagSelector.get_all_tags(organization_id, only_active)
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = DietaryTagSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """Create a new dietary tag"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = DietaryTagSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            tag = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# DIETARY TAG RETRIEVE, UPDATE & DELETE VIEW
# ============================================================

@extend_schema_view(
    get=DIETARY_TAG_RETRIEVE_SCHEMA,
    put=DIETARY_TAG_UPDATE_SCHEMA,
    patch=DIETARY_TAG_UPDATE_SCHEMA,
    delete=DIETARY_TAG_DELETE_SCHEMA,
)
class DietaryTagRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a dietary tag
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request, pk):
        """Get dietary tag by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tag = get_object_or_404(
            DietaryTag,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = DietaryTagSerializer(tag, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update dietary tag"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tag = get_object_or_404(
            DietaryTag,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = DietaryTagSerializer(
            tag, 
            data=data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Partial update dietary tag"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tag = get_object_or_404(
            DietaryTag,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = DietaryTagSerializer(
            tag, 
            data=data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete dietary tag"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tag = get_object_or_404(
            DietaryTag,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        # Check if tag is used by products
        if tag.products.filter(is_active=True).exists():
            return Response(
                {"error": "Cannot delete dietary tag that is used by active products."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tag.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)