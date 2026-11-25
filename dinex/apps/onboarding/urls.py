from django.urls import path

from .views.restaurant_views import (
    RestaurantOnboardingAPIView,
)

""" ======================= Onboarding URL Configuration ======================= """
urlpatterns = [
    path(
        "restaurant/",
        RestaurantOnboardingAPIView.as_view(),
        name="restaurant-onboarding",
    ),
]