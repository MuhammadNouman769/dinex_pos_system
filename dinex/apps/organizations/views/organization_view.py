from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.utils.permissions import IsOrganizationOwner, IsPlatformUser
from apps.utils.helpers import get_user_organization_id
from apps.organizations.models import Organization
from apps.organizations.selectors import get_platform_organizations
from apps.organizations.serializers.organization_serializer import (
    OrganizationListSerializer,
    OrganizationDetailSerializer,
)
from apps.organizations.schemas.organization_schema import (
    organization_list_schema,
    organization_retrieve_schema,
    organization_update_schema,
    organization_me_schema,
    organization_toggle_active_schema,
)


@organization_list_schema
class OrganizationListAPIView(ListAPIView):
    """
    Platform organization list API.
    Only PLATFORM users can access this endpoint.
    """
    serializer_class = OrganizationListSerializer
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get_queryset(self):
        return get_platform_organizations()


""" ======================= Organization Retrieve & Update View ======================= """
class OrganizationRetrieveUpdateAPIView(APIView):
    """
    Accessible by platform users (any organization) or the
    organization's own owner (their organization only).
    """

    permission_classes = [IsAuthenticated, IsOrganizationOwner]

    def _get_organization(self, request, pk):
        organization = get_object_or_404(Organization, pk=pk)
        self.check_object_permissions(request, organization)
        return organization

    @organization_retrieve_schema
    def get(self, request, pk):
        organization = self._get_organization(request, pk)
        serializer = OrganizationDetailSerializer(organization)
        return Response(serializer.data)

    @organization_update_schema
    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    @organization_update_schema
    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        organization = self._get_organization(request, pk)
        serializer = OrganizationDetailSerializer(
            organization, data=request.data, partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


""" ======================= My Organization View ======================= """
class OrganizationMeAPIView(APIView):
    """
    Returns the organization the current (owner) user belongs to.
    """

    permission_classes = [IsAuthenticated]

    @organization_me_schema
    def get(self, request):
        organization_id = get_user_organization_id(request)

        if not organization_id:
            return Response(
                {"detail": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        organization = get_object_or_404(Organization, pk=organization_id)
        serializer = OrganizationDetailSerializer(organization)
        return Response(serializer.data)


""" ======================= Organization Toggle Active View ======================= """
class OrganizationToggleActiveAPIView(APIView):
    """
    Platform-only. Activates/deactivates an organization.
    """

    permission_classes = [IsAuthenticated, IsPlatformUser]

    @organization_toggle_active_schema
    def post(self, request, pk):
        organization = get_object_or_404(Organization, pk=pk)

        if "is_active" in request.data:
            value = request.data["is_active"]
            if isinstance(value, str):
                value = value.strip().lower() in ("true", "1", "yes")
            organization.is_active = bool(value)
        else:
            organization.is_active = not organization.is_active

        organization.save(update_fields=["is_active", "updated_at"])

        serializer = OrganizationDetailSerializer(organization)
        return Response(serializer.data)