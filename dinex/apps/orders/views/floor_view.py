from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.utils import get_user_organization_id
from apps.utils.helpers import location_scope
from apps.utils.pagination import StandardResultsSetPagination
from apps.utils.permissions import IsOrganizationOwnerOrReadOnly
from apps.orders.models import Floor
from apps.orders.serializers.floor_serializer import FloorSerializer


def _org(request):
    return get_user_organization_id(request)


class FloorListCreateView(APIView):
    """Floors of the caller's restaurant. Owner creates/edits; staff can read."""
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]

    def get(self, request):
        org = _org(request)
        if not org:
            return Response({"error": "No organization."}, status=status.HTTP_403_FORBIDDEN)
        qs = Floor.objects.filter(**location_scope(request, org)).select_related("location")
        location_id = request.query_params.get("location")
        if location_id:
            try:
                qs = qs.filter(location_id=int(location_id))
            except ValueError:
                return Response({"error": "Invalid location id."}, status=status.HTTP_400_BAD_REQUEST)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            FloorSerializer(page, many=True, context={"request": request}).data
        )

    def post(self, request):
        serializer = FloorSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FloorDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationOwnerOrReadOnly]

    def _get(self, request, pk):
        org = _org(request)
        return get_object_or_404(Floor, pk=pk, **location_scope(request, org))

    def get(self, request, pk):
        return Response(FloorSerializer(self._get(request, pk), context={"request": request}).data)

    def patch(self, request, pk):
        floor = self._get(request, pk)
        serializer = FloorSerializer(floor, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @transaction.atomic
    def delete(self, request, pk):
        floor = self._get(request, pk)
        if floor.tables.filter(is_deleted=False).exists():
            return Response(
                {"error": "Move or delete this floor's tables first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        floor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
