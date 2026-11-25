from django.urls import path

from apps.catalog.views.image_view import CatalogImageView
from apps.catalog.views.category_view import (
    CategoryListCreateView,
    CategoryRetrieveUpdateDeleteView,
    CategoryTreeView,
    CategoryReorderView
)
from apps.catalog.views.product_view import (
    ProductListCreateView,
    ProductRetrieveUpdateDeleteView,
    ProductBulkCreateView
)
from apps.catalog.views.variant_view import (
    VariantListCreateView,
    VariantRetrieveUpdateDeleteView,
    VariantBulkCreateView
)
from apps.catalog.views.dietary_tag_view import (
    DietaryTagListCreateView,
    DietaryTagRetrieveUpdateDeleteView
)
from apps.catalog.views.modifier_group_view import (
    ModifierGroupListCreateView,
    ModifierGroupRetrieveUpdateDeleteView
)
from apps.catalog.views.modifier_option_view import (
    ModifierOptionListCreateView,
    ModifierOptionRetrieveUpdateDeleteView,
    ModifierOptionReorderView
)
from apps.catalog.views.product_modifier_group_view import (
    ProductModifierGroupListCreateView,
    ProductModifierGroupRetrieveUpdateDeleteView,
    ProductModifierGroupBulkCreateView
)
from apps.catalog.views.product_location_view import (
    ProductLocationListCreateView,
    ProductLocationRetrieveUpdateDeleteView,
    ProductLocationBulkAssignView
)
from apps.catalog.views.deal_view import (
    DealListCreateView,
    DealRetrieveUpdateDeleteView,
    DealToggleActiveView
)
from apps.catalog.views.deal_item_view import (
    DealItemListCreateView,
    DealItemRetrieveUpdateDeleteView
)
from apps.catalog.views.deal_location_view import (
    DealLocationListCreateView,
    DealLocationRetrieveUpdateDeleteView,
    DealLocationBulkAssignView
)

urlpatterns = [
    # Category URLs
    path('images/<str:kind>/<int:pk>/', CatalogImageView.as_view(), name='catalog-image'),
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/tree/', CategoryTreeView.as_view(), name='category-tree'),
    path('categories/reorder/', CategoryReorderView.as_view(), name='category-reorder'),
    path('categories/<int:pk>/', CategoryRetrieveUpdateDeleteView.as_view(), name='category-detail'),
    
    # Product URLs
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('products/bulk/', ProductBulkCreateView.as_view(), name='product-bulk-create'),
    path('products/<int:pk>/', ProductRetrieveUpdateDeleteView.as_view(), name='product-detail'),
    
    # Variant URLs
    path('variants/', VariantListCreateView.as_view(), name='variant-list-create'),
    path('variants/bulk/', VariantBulkCreateView.as_view(), name='variant-bulk-create'),
    path('variants/<int:pk>/', VariantRetrieveUpdateDeleteView.as_view(), name='variant-detail'),
    
    # Dietary Tag URLs
    path('dietary-tags/', DietaryTagListCreateView.as_view(), name='dietary-tag-list-create'),
    path('dietary-tags/<int:pk>/', DietaryTagRetrieveUpdateDeleteView.as_view(), name='dietary-tag-detail'),
    
    # Modifier Group URLs
    path('modifier-groups/', ModifierGroupListCreateView.as_view(), name='modifier-group-list-create'),
    path('modifier-groups/<int:pk>/', ModifierGroupRetrieveUpdateDeleteView.as_view(), name='modifier-group-detail'),
    
    # Modifier Option URLs
    path('modifier-options/', ModifierOptionListCreateView.as_view(), name='modifier-option-list-create'),
    path('modifier-options/reorder/', ModifierOptionReorderView.as_view(), name='modifier-option-reorder'),
    path('modifier-options/<int:pk>/', ModifierOptionRetrieveUpdateDeleteView.as_view(), name='modifier-option-detail'),
    
    # Product Modifier Group URLs
    path('product-modifier-groups/', ProductModifierGroupListCreateView.as_view(), name='product-modifier-group-list-create'),
    path('product-modifier-groups/bulk/', ProductModifierGroupBulkCreateView.as_view(), name='product-modifier-group-bulk-create'),
    path('product-modifier-groups/<int:pk>/', ProductModifierGroupRetrieveUpdateDeleteView.as_view(), name='product-modifier-group-detail'),
    
    # Product Location URLs
    path('product-locations/', ProductLocationListCreateView.as_view(), name='product-location-list-create'),
    path('product-locations/bulk/', ProductLocationBulkAssignView.as_view(), name='product-location-bulk-assign'),
    path('product-locations/<int:pk>/', ProductLocationRetrieveUpdateDeleteView.as_view(), name='product-location-detail'),
    
    # Deal URLs
    path('deals/', DealListCreateView.as_view(), name='deal-list-create'),
    path('deals/<int:pk>/', DealRetrieveUpdateDeleteView.as_view(), name='deal-detail'),
    path('deals/<int:pk>/toggle/', DealToggleActiveView.as_view(), name='deal-toggle-active'),
    
    # Deal Item URLs
    path('deal-items/', DealItemListCreateView.as_view(), name='deal-item-list-create'),
    path('deal-items/<int:pk>/', DealItemRetrieveUpdateDeleteView.as_view(), name='deal-item-detail'),
    
    # Deal Location URLs
    path('deal-locations/', DealLocationListCreateView.as_view(), name='deal-location-list-create'),
    path('deal-locations/bulk/', DealLocationBulkAssignView.as_view(), name='deal-location-bulk-assign'),
    path('deal-locations/<int:pk>/', DealLocationRetrieveUpdateDeleteView.as_view(), name='deal-location-detail'),
]