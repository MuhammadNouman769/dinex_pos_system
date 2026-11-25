from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import Organization, LocationMembership
from apps.organizations.selectors.location_membership_selector import (
    LocationMembershipSelector,
)
from apps.organizations.serializers.location_membership_serializer import (
    LocationMembershipSerializer,
    LocationMembershipAssignSerializer,
    LocationMembershipUpdateSerializer,
)
from apps.organizations.schemas.location_membership_schema import (
    location_membership_list_schema,
    location_membership_assign_schema,
    location_membership_retrieve_schema,
    location_membership_update_schema,
    location_membership_delete_schema,
)
from apps.utils.helpers import get_user_organization_id
from apps.utils.permissions import IsOrganizationOwner


""" ======================= Location Staff List & Assign View ======================= """
class LocationMembershipListCreateAPIView(APIView):

    permission_classes = [IsAuthenticated, IsOrganizationOwner]

    @location_membership_list_schema
    def get(self, request):
        organization_id = get_user_organization_id(request)

        if not organization_id:
            return Response(
                {"detail": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        location_id = request.query_params.get("location_id")
        if location_id:
            try:
                location_id = int(location_id)
            except (TypeError, ValueError):
                return Response({"error": "Invalid location_id."}, status=status.HTTP_400_BAD_REQUEST)
        assignments = LocationMembershipSelector.get_all(organization_id, location_id)

        serializer = LocationMembershipSerializer(assignments, many=True)
        return Response(serializer.data)

    @location_membership_assign_schema
    def post(self, request):
        organization_id = get_user_organization_id(request)

        if not organization_id:
            return Response(
                {"detail": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        organization = get_object_or_404(Organization, pk=organization_id)
        self.check_object_permissions(request, organization)

        serializer = LocationMembershipAssignSerializer(
            data=request.data, context={"organization": organization},
        )
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()

        return Response(
            LocationMembershipSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


""" ======================= Location Staff Retrieve, Update & Delete View ======================= """
class LocationMembershipRetrieveUpdateDeleteAPIView(APIView):

    permission_classes = [IsAuthenticated, IsOrganizationOwner]

    def _get_assignment(self, request, pk):
        organization_id = get_user_organization_id(request)

        if not organization_id:
            return None, Response(
                {"detail": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        assignment = get_object_or_404(
            LocationMembership.objects.select_related(
                "organization_membership__user", "location",
            ),
            pk=pk,
            organization_membership__organization_id=organization_id,
        )
        self.check_object_permissions(request, assignment)
        return assignment, None

    @location_membership_retrieve_schema
    def get(self, request, pk):
        assignment, error = self._get_assignment(request, pk)
        if error:
            return error

        return Response(LocationMembershipSerializer(assignment).data)

    @location_membership_update_schema
    def patch(self, request, pk):
        assignment, error = self._get_assignment(request, pk)
        if error:
            return error

        serializer = LocationMembershipUpdateSerializer(
            assignment, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(LocationMembershipSerializer(assignment).data)

    @location_membership_delete_schema
    def delete(self, request, pk):
        assignment, error = self._get_assignment(request, pk)
        if error:
            return error

        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
