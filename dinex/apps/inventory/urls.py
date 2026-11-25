from django.urls import path
from apps.inventory import views

urlpatterns = [
    path("ingredients/", views.IngredientListCreateView.as_view(), name="ingredient-list-create"),
    path("ingredients/<int:pk>/", views.IngredientDetailView.as_view(), name="ingredient-detail"),
    path("stock/", views.StockListView.as_view(), name="stock-list"),
    path("stock/movements/", views.StockMovementListCreateView.as_view(), name="stock-movements"),
    path("recipes/variant/<int:pk>/", views.VariantRecipeView.as_view(), name="variant-recipe"),
    path("recipes/ingredient/<int:pk>/", views.PreparedIngredientRecipeView.as_view(), name="prepared-recipe"),
]
