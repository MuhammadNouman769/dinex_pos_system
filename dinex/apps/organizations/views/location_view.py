from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import Location, Organization
from apps.organizations.selectors.location_selector import LocationSelector
from apps.organizations.serializers.location_serializer import LocationSerializer
from apps.organizations.schemas.location_schema import (
    location_list_schema,
    location_create_schema,
    location_retrieve_schema,
    location_update_schema,
    location_delete_schema,
    location_set_primary_schema,
)
from apps.utils.helpers import get_user_organization_id
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly


""" ======================= Location List & Create View ======================= """
class LocationListCreateAPIView(APIView):

    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]

    @location_list_schema
    def get(self, request):
        organization_id = get_user_organization_id(request)

        if not organization_id:
            return Response(
                {"detail": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        only_active = request.query_params.get("active", "false").lower() == "true"
        locations = LocationSelector.get_all_locations(organization_id, only_active)

        serializer = LocationSerializer(locations, many=True)
        return Response(serializer.data)

    @location_create_schema
    def post(self, request):
        organization_id = get_user_organization_id(request)

        if not organization_id:
            return Response(
                {"detail": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        organization = get_object_or_404(Organization, pk=organization_id)

        from apps.billing.services import check_limit
        check_limit(organization, "locations")       # plan allows N branches

        serializer = LocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization=organization)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


""" ======================= Location Retrieve, Update & Delete View ======================= """
class LocationRetrieveUpdateDeleteAPIView(APIView):

    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]

    def _get_location(self, request, pk):
        organization_id = get_user_organization_id(request)

        if not organization_id:
            return None, Response(
                {"detail": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        location = get_object_or_404(
            Location,
            pk=pk,
            organization_id=organization_id,
        )
        return location, None

    @location_retrieve_schema
    def get(self, request, pk):
        location, error = self._get_location(request, pk)
        if error:
            return error

        serializer = LocationSerializer(location)
        return Response(serializer.data)

    @location_update_schema
    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    @location_update_schema
    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        location, error = self._get_location(request, pk)
        if error:
            return error

        serializer = LocationSerializer(location, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @location_delete_schema
    def delete(self, request, pk):
        location, error = self._get_location(request, pk)
        if error:
            return error

        with transaction.atomic():
            active_locations = Location.objects.filter(
                organization_id=location.organization_id,
                is_active=True,
            ).exclude(pk=location.pk)

            if not active_locations.exists():
                return Response(
                    {"detail": "Cannot delete the only location of an organization."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if location.is_primary:
                successor = active_locations.order_by("id").first()
                successor.is_primary = True
                successor.save(update_fields=["is_primary", "updated_at"])

            location.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


""" ======================= Location Set Primary View ======================= """
class LocationSetPrimaryAPIView(APIView):

    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]

    @location_set_primary_schema
    def post(self, request, pk):
        organization_id = get_user_organization_id(request)

        if not organization_id:
            return Response(
                {"detail": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        location = get_object_or_404(
            Location,
            pk=pk,
            organization_id=organization_id,
        )

        with transaction.atomic():
            Location.objects.filter(
                organization_id=organization_id,
                is_primary=True,
            ).exclude(pk=location.pk).update(is_primary=False)

            location.is_primary = True
            location.save(update_fields=["is_primary", "updated_at"])

        serializer = LocationSerializer(location)
        return Response(serializer.data)
