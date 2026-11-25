from .category_view import (
    CategoryListCreateView,
    CategoryRetrieveUpdateDeleteView,
    CategoryTreeView,
    CategoryReorderView
)
from .product_view import (
    ProductListCreateView,
    ProductRetrieveUpdateDeleteView,
    ProductBulkCreateView
)
from .variant_view import (
    VariantListCreateView,
    VariantRetrieveUpdateDeleteView,
    VariantBulkCreateView
)
from .dietary_tag_view import (
    DietaryTagListCreateView,
    DietaryTagRetrieveUpdateDeleteView
)
from .modifier_group_view import (
    ModifierGroupListCreateView,
    ModifierGroupRetrieveUpdateDeleteView
)
from .modifier_option_view import (
    ModifierOptionListCreateView,
    ModifierOptionRetrieveUpdateDeleteView,
    ModifierOptionReorderView
)
from .product_modifier_group_view import (
    ProductModifierGroupListCreateView,
    ProductModifierGroupRetrieveUpdateDeleteView,
    ProductModifierGroupBulkCreateView
)
from .product_location_view import (
    ProductLocationListCreateView,
    ProductLocationRetrieveUpdateDeleteView,
    ProductLocationBulkAssignView
)
from .deal_view import (
    DealListCreateView,
    DealRetrieveUpdateDeleteView,
    DealToggleActiveView
)
from .deal_item_view import (
    DealItemListCreateView,
    DealItemRetrieveUpdateDeleteView
)
from .deal_location_view import (
    DealLocationListCreateView,
    DealLocationRetrieveUpdateDeleteView,
    DealLocationBulkAssignView
)

__all__ = [
    'CategoryListCreateView',
    'CategoryRetrieveUpdateDeleteView',
    'CategoryTreeView',
    'CategoryReorderView',
    'ProductListCreateView',
    'ProductRetrieveUpdateDeleteView',
    'ProductBulkCreateView',
    'VariantListCreateView',
    'VariantRetrieveUpdateDeleteView',
    'VariantBulkCreateView',
    'DietaryTagListCreateView',
    'DietaryTagRetrieveUpdateDeleteView',
    'ModifierGroupListCreateView',
    'ModifierGroupRetrieveUpdateDeleteView',
    'ModifierOptionListCreateView',
    'ModifierOptionRetrieveUpdateDeleteView',
    'ModifierOptionReorderView',
    'ProductModifierGroupListCreateView',
    'ProductModifierGroupRetrieveUpdateDeleteView',
    'ProductModifierGroupBulkCreateView',
    'ProductLocationListCreateView',
    'ProductLocationRetrieveUpdateDeleteView',
    'ProductLocationBulkAssignView',
    'DealListCreateView',
    'DealRetrieveUpdateDeleteView',
    'DealToggleActiveView',
    'DealItemListCreateView',
    'DealItemRetrieveUpdateDeleteView',
    'DealLocationListCreateView',
    'DealLocationRetrieveUpdateDeleteView',
    'DealLocationBulkAssignView',
]