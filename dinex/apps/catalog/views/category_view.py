from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import ProductCategory
from apps.catalog.serializers.category_serializer import CategorySerializer
from apps.catalog.selectors.category_selector import CategorySelector
from apps.catalog.schemas.category_schema import (
    CATEGORY_LIST_SCHEMA,
    CATEGORY_CREATE_SCHEMA,
    CATEGORY_RETRIEVE_SCHEMA,
    CATEGORY_UPDATE_SCHEMA,
    CATEGORY_DELETE_SCHEMA,
    CATEGORY_TREE_SCHEMA,
    CATEGORY_REORDER_SCHEMA,
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
# CATEGORY LIST & CREATE VIEW
# ============================================================

@extend_schema_view(
    get=CATEGORY_LIST_SCHEMA,
    post=CATEGORY_CREATE_SCHEMA,
)
class CategoryListCreateView(APIView):
    """
    View to list and create categories
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Get all categories for the user's organization"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        only_active = request.query_params.get('active', 'true').lower() == 'true'
        search_term = request.query_params.get('search', None)
        root_only = request.query_params.get('root_only', 'false').lower() == 'true'
        
        if search_term:
            categories = CategorySelector.search_categories(organization_id, search_term)
        elif root_only:
            categories = CategorySelector.get_root_categories(organization_id, only_active)
        else:
            categories = CategorySelector.get_all_categories(organization_id, only_active)
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(categories, request)
        serializer = CategorySerializer(page, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    
    def post(self, request):
        """Create a new category"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = CategorySerializer(data=data, context={'request': request})
        if serializer.is_valid():
            category = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================
# CATEGORY RETRIEVE, UPDATE & DELETE VIEW
# ============================================================

@extend_schema_view(
    get=CATEGORY_RETRIEVE_SCHEMA,
    put=CATEGORY_UPDATE_SCHEMA,
    patch=CATEGORY_UPDATE_SCHEMA,
    delete=CATEGORY_DELETE_SCHEMA,
)
class CategoryRetrieveUpdateDeleteView(APIView):
    """
    View to retrieve, update and delete a category
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request, pk):
        """Get category by ID"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        category = get_object_or_404(
            ProductCategory,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        serializer = CategorySerializer(category, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update category"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        category = get_object_or_404(
            ProductCategory,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = CategorySerializer(
            category, 
            data=data,
            context={'request': request},
            partial=False
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, pk):
        """Partial update category"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        category = get_object_or_404(
            ProductCategory,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        data = request.data.copy()
        data['organization'] = organization_id
        
        serializer = CategorySerializer(
            category, 
            data=data,
            context={'request': request},
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft delete category"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        category = get_object_or_404(
            ProductCategory,
            id=pk,
            organization_id=organization_id,
            is_deleted=False
        )
        
        if category.products.filter(is_active=True).exists():
            return Response(
                {"error": "Cannot delete category with active products."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================
# CATEGORY TREE VIEW
# ============================================================

class CategoryTreeView(APIView):
    """
    View to get category tree
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def get(self, request):
        """Get complete category tree"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        tree = CategorySelector.get_category_tree(organization_id)
        return Response(tree)


# ============================================================
# CATEGORY REORDER VIEW
# ============================================================

class CategoryReorderView(APIView):
    """
    View to reorder categories
    """
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]
    
    def post(self, request):
        """Reorder categories"""
        organization_id = get_user_organization_id(request)
        
        if not organization_id:
            return Response(
                {"error": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        category_ids = request.data.get('category_ids', [])
        
        if not category_ids:
            return Response(
                {"error": "category_ids is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        for index, category_id in enumerate(category_ids):
            ProductCategory.objects.filter(
                id=category_id,
                organization_id=organization_id
            ).update(position=index + 1)
        
        return Response({"message": "Categories reordered successfully."})