from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from apps.catalog.utils import get_user_organization_id
from apps.catalog.models import ModifierOption, ModifierGroup
from apps.catalog.serializers.modifier_option_serializer import ModifierOptionSerializer
from apps.catalog.selectors.modifier_option_selector import ModifierOptionSelector
from apps.catalog.schemas.modifier_option_schema import (
    MODIFIER_OPTION_LIST_SCHEMA,
    MODIFIER_OPTION_CREATE_SCHEMA,
    MODIFIER_OPTION_RETRIEVE_SCHEMA,
    MODIFIER_OPTION_UPDATE_SCHEMA,
    MODIFIER_OPTION_DELETE_SCHEMA,
    MODIFIER_OPTION_REORDER_SCHEMA,
)
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly
from apps.utils.pagination import StandardResultsSetPagination

@extend_schema_view(
    get=MODIFIER_OPTION_LIST_SCHEMA,
    post=MODIFIER_OPTION_CREATE_SCHEMA,
)

class ModifierOptionListCreateView(APIView):
    """
    View to list and create modifier options
    """
    permission_classes = [IsOrganizationOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Get all modifier options for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        modifier_group_id = request.query_params.get('modifier_group', None)
        only_active = request.query_params.get('active', 'true').lower() == 'true'
        search_term = request.query_params.get('search', None)
        
        queryset = ModifierOptionSelector.get_all_options(modifier_group_id, only_active)
        queryset = queryset.filter(modifier_group__organization_id=organization_id)
        
        if search_term:
            queryset = ModifierOptionSelector.search_options(search_term, modifier_group_id)
        
        queryset = queryset.select_related('modifier_group')
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ModifierOptionSerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """Create a new modifier option"""
        organization_id = get_user_organization_id(request)
        
        # Verify modifier group belongs to organization
        modifier_group_id = request.data.get('modifier_group')
        if modifier_group_id:
            get_object_or_404(ModifierGroup, id=modifier_group_id, organization_id=organization_id)
        
        serializer = ModifierOptionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema_view(
    get=MODIFIER_OPTION_RETRIEVE_SCHEMA,
    put=MODIFIER_OPTION_UPDATE_SCHEMA,
    patch=MODIFIER_OPTION_UPDATE_SCHEMA,
    delete=MODIFIER_OPTION_DELETE_SCHEMA,
)

class ModifierOptionRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a modifier option
    """
    permission_classes = [IsOrganizationOwnerOrReadOnly]
    
    def get(self, request, pk):
        """Get modifier option by ID"""
        organization_id = get_user_organization_id(request)
        option = get_object_or_404(
            ModifierOption,
            id=pk,
            modifier_group__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = ModifierOptionSerializer(option, context={'request': request})
        return Response(serializer.data)
    def put(self, request, pk):
        """Update modifier option"""
        organization_id = get_user_organization_id(request)
        option = get_object_or_404(
            ModifierOption,
            id=pk,
            modifier_group__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = ModifierOptionSerializer(
            option, 
            data=request.data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Partial update modifier option"""
        organization_id = get_user_organization_id(request)
        option = get_object_or_404(
            ModifierOption,
            id=pk,
            modifier_group__organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = ModifierOptionSerializer(
            option, 
            data=request.data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete modifier option"""
        organization_id = get_user_organization_id(request)
        option = get_object_or_404(
            ModifierOption,
            id=pk,
            modifier_group__organization_id=organization_id,
            is_deleted=False
        )
        
        option.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ModifierOptionReorderView(APIView):
    """
    View to reorder modifier options
    """
    permission_classes = [IsOrganizationOwnerOrReadOnly]
    def post(self, request):
        """Reorder modifier options within a group"""
        organization_id = get_user_organization_id(request)
        modifier_group_id = request.data.get('modifier_group_id')
        option_ids = request.data.get('option_ids', [])
        
        if not modifier_group_id:
            return Response(
                {"error": "modifier_group_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not option_ids:
            return Response(
                {"error": "option_ids is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify modifier group belongs to organization
        get_object_or_404(ModifierGroup, id=modifier_group_id, organization_id=organization_id)
        
        # Update positions
        for index, option_id in enumerate(option_ids):
            ModifierOption.objects.filter(
                id=option_id,
                modifier_group_id=modifier_group_id
            ).update(position=index + 1)
        
        return Response({"message": "Options reordered successfully."})