from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.selectors.membership_selector import MembershipSelector
from apps.organizations.serializers.membership_serializer import (
    MembershipSerializer,
    MembershipInviteSerializer,
    MembershipUpdateSerializer,
)
from apps.organizations.schemas.membership_schema import (
    membership_list_schema,
    membership_invite_schema,
    membership_retrieve_schema,
    membership_update_schema,
    membership_delete_schema,
)
from apps.utils.helpers import get_user_organization_id
from apps.utils.permissions import IsOrganizationOwner


""" ======================= Membership List & Invite View ======================= """
class MembershipListCreateAPIView(APIView):

    permission_classes = [IsAuthenticated, IsOrganizationOwner]

    @membership_list_schema
    def get(self, request):
        organization_id = get_user_organization_id(request)

        if not organization_id:
            return Response(
                {"detail": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        members = MembershipSelector.get_all_members(organization_id)
        serializer = MembershipSerializer(members, many=True)
        return Response(serializer.data)

    @membership_invite_schema
    def post(self, request):
        organization_id = get_user_organization_id(request)

        if not organization_id:
            return Response(
                {"detail": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        organization = get_object_or_404(Organization, pk=organization_id)
        self.check_object_permissions(request, organization)

        serializer = MembershipInviteSerializer(
            data=request.data, context={"organization": organization},
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()

        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )


""" ======================= Membership Retrieve, Update & Delete View ======================= """
class MembershipRetrieveUpdateDeleteAPIView(APIView):

    permission_classes = [IsAuthenticated, IsOrganizationOwner]

    def _get_membership(self, request, pk):
        organization_id = get_user_organization_id(request)

        if not organization_id:
            return None, Response(
                {"detail": "User has no organization assigned."},
                status=status.HTTP_403_FORBIDDEN,
            )

        membership = get_object_or_404(
            OrganizationMembership.objects.select_related("user"),
            pk=pk,
            organization_id=organization_id,
        )
        self.check_object_permissions(request, membership)
        return membership, None

    def _is_last_active_owner(self, membership):
        if membership.role != OrganizationMembership.Role.OWNER:
            return False
        if not membership.is_active:
            return False
        return MembershipSelector.count_active_owners(membership.organization_id) <= 1

    @membership_retrieve_schema
    def get(self, request, pk):
        membership, error = self._get_membership(request, pk)
        if error:
            return error

        return Response(MembershipSerializer(membership).data)

    @membership_update_schema
    def patch(self, request, pk):
        membership, error = self._get_membership(request, pk)
        if error:
            return error

        will_lose_owner = self._is_last_active_owner(membership) and (
            request.data.get("is_active") is False
            or (
                "role" in request.data
                and request.data["role"] != OrganizationMembership.Role.OWNER
            )
        )

        if will_lose_owner:
            return Response(
                {"detail": "Cannot remove owner role/status from the organization's last active owner."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MembershipUpdateSerializer(
            membership, data=request.data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(MembershipSerializer(membership).data)

    @membership_delete_schema
    def delete(self, request, pk):
        membership, error = self._get_membership(request, pk)
        if error:
            return error

        if self._is_last_active_owner(membership):
            return Response(
                {"detail": "Cannot remove the organization's last active owner."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
