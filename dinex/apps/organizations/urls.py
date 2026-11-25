from django.urls import path
from apps.organizations.branding import BrandingImageView, BrandingView

from apps.organizations.views import (
    OrganizationListAPIView,
    OrganizationRetrieveUpdateAPIView,
    OrganizationMeAPIView,
    OrganizationToggleActiveAPIView,
    LocationListCreateAPIView,
    LocationRetrieveUpdateDeleteAPIView,
    LocationSetPrimaryAPIView,
    MembershipListCreateAPIView,
    MembershipRetrieveUpdateDeleteAPIView,
    LocationMembershipListCreateAPIView,
    LocationMembershipRetrieveUpdateDeleteAPIView,
)


urlpatterns = [
    # Organization URLs
    path("", OrganizationListAPIView.as_view(), name="organization-list"),
    path("me/branding/", BrandingView.as_view(), name="organization-branding"),
    path("me/branding/<str:kind>/", BrandingImageView.as_view(), name="organization-branding-image"),
    path("me/", OrganizationMeAPIView.as_view(), name="organization-me"),
    path("<int:pk>/", OrganizationRetrieveUpdateAPIView.as_view(), name="organization-detail"),
    path("<int:pk>/toggle/", OrganizationToggleActiveAPIView.as_view(), name="organization-toggle-active"),

    # Location URLs
    path("locations/", LocationListCreateAPIView.as_view(), name="location-list-create"),
    path("locations/<int:pk>/", LocationRetrieveUpdateDeleteAPIView.as_view(), name="location-detail"),
    path("locations/<int:pk>/set-primary/", LocationSetPrimaryAPIView.as_view(), name="location-set-primary"),

    # Organization Membership (Members) URLs
    path("members/", MembershipListCreateAPIView.as_view(), name="membership-list-create"),
    path("members/<int:pk>/", MembershipRetrieveUpdateDeleteAPIView.as_view(), name="membership-detail"),

    # Location Membership (Location Staff) URLs
    path("location-staff/", LocationMembershipListCreateAPIView.as_view(), name="location-membership-list-create"),
    path("location-staff/<int:pk>/", LocationMembershipRetrieveUpdateDeleteAPIView.as_view(), name="location-membership-detail"),
]
