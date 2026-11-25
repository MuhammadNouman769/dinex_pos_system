from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import ModifierGroup, ModifierOption
from apps.catalog.serializers.modifier_group_serializer import ModifierGroupSerializer
from apps.catalog.selectors.modifier_group_selector import ModifierGroupSelector
from apps.catalog.serializers.modifier_option_serializer import ModifierOptionSerializer
from apps.catalog.schemas.modifier_group_schema import (
    MODIFIER_GROUP_LIST_SCHEMA,
    MODIFIER_GROUP_CREATE_SCHEMA,
    MODIFIER_GROUP_RETRIEVE_SCHEMA,
    MODIFIER_GROUP_UPDATE_SCHEMA,
    MODIFIER_GROUP_DELETE_SCHEMA,
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
# MODIFIER GROUP LIST & CREATE VIEW
# ============================================================

@extend_schema_view(
    get=MODIFIER_GROUP_LIST_SCHEMA,
    post=MODIFIER_GROUP_CREATE_SCHEMA,
)
class ModifierGroupListCreateView(APIView):
    """
    View to list and create modifier groups
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request):
        """Get all modifier groups for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        only_active = request.query_params.get('active', 'true').lower() == 'true'
        search_term = request.query_params.get('search', None)
        
        if search_term:
            queryset = ModifierGroupSelector.search_groups(organization_id, search_term)
        else:
            queryset = ModifierGroupSelector.get_all_groups(organization_id, only_active)
        
        queryset = queryset.prefetch_related('options')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ModifierGroupSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    @transaction.atomic
    def post(self, request):
        """Create a new modifier group"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = ModifierGroupSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            group = serializer.save()
            
            # Handle options if provided
            options_data = request.data.get('options', [])
            if options_data:
                for option_data in options_data:
                    option_data['modifier_group'] = group.id
                    option_serializer = ModifierOptionSerializer(data=option_data)
                    if option_serializer.is_valid():
                        option_serializer.save()
            
            # Refresh to get options
            group = ModifierGroup.objects.get(id=group.id)
            response_serializer = ModifierGroupSerializer(group, context={'request': request})
            
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# MODIFIER GROUP RETRIEVE, UPDATE & DELETE VIEW
# ============================================================

@extend_schema_view(
    get=MODIFIER_GROUP_RETRIEVE_SCHEMA,
    put=MODIFIER_GROUP_UPDATE_SCHEMA,
    patch=MODIFIER_GROUP_UPDATE_SCHEMA,
    delete=MODIFIER_GROUP_DELETE_SCHEMA,
)
class ModifierGroupRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a modifier group
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request, pk):
        """Get modifier group by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        group = get_object_or_404(
            ModifierGroup,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = ModifierGroupSerializer(group, context={'request': request})
        return Response(serializer.data)
    
    @transaction.atomic
    def put(self, request, pk):
        """Update modifier group"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        group = get_object_or_404(
            ModifierGroup,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = ModifierGroupSerializer(
            group, 
            data=data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            group = serializer.save()
            
            # Handle options if provided
            options_data = request.data.get('options', [])
            if options_data:
                # Delete existing options not in the list
                existing_option_ids = [o.get('id') for o in options_data if o.get('id')]
                if existing_option_ids:
                    group.options.exclude(id__in=existing_option_ids).delete()
                
                for option_data in options_data:
                    option_data['modifier_group'] = group.id
                    if option_data.get('id'):
                        option = group.options.filter(id=option_data['id']).first()
                        if option:
                            option_serializer = ModifierOptionSerializer(option, data=option_data)
                            if option_serializer.is_valid():
                                option_serializer.save()
                    else:
                        option_serializer = ModifierOptionSerializer(data=option_data)
                        if option_serializer.is_valid():
                            option_serializer.save()
            
            group = ModifierGroup.objects.get(id=group.id)
            response_serializer = ModifierGroupSerializer(group, context={'request': request})
            
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def patch(self, request, pk):
        """Partial update modifier group"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        group = get_object_or_404(
            ModifierGroup,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = ModifierGroupSerializer(
            group, 
            data=data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete modifier group"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        group = get_object_or_404(
            ModifierGroup,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        # Check if group is linked to products
        if group.product_links.filter(product__is_active=True).exists():
            return Response(
                {"error": "Cannot delete modifier group linked to active products."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)