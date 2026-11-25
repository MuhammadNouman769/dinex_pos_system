from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics import platform, services
from apps.catalog.utils import get_user_organization_id
from apps.organizations.models import Location
from apps.utils.helpers import get_accessible_location_ids, is_manager_or_owner, location_model_scope
from apps.utils.permissions import IsPlatformUser


class AnalyticsView(APIView):
    """Base: who may look (owner / branch manager), which branches, which dates."""
    permission_classes = [IsAuthenticated]

    def setup_scope(self, request):
        org = get_user_organization_id(request)
        if not org:
            raise PermissionDenied("User has no organization assigned.")
        qs = Location.objects.filter(**location_model_scope(request, org))
        if request.query_params.get("location"):
            try:
                qs = qs.filter(pk=int(request.query_params["location"]))
            except ValueError:
                raise ValidationError({"location": "Invalid branch."})
            if not qs.exists():
                get_object_or_404(Location, pk=-1)
        locations = [l for l in qs if is_manager_or_owner(request, l)]
        if not locations:
            raise PermissionDenied("Analytics are for owners and branch managers.")
        today = timezone.localdate()
        parse = lambda v, d: d if not v else self._date(v)
        end = min(parse(request.query_params.get("to"), today), today)
        start = parse(request.query_params.get("from"), end - timedelta(days=29))
        if start > end:
            raise ValidationError({"from": "Must not be after the end date."})
        if (end - start).days > 366:
            raise ValidationError({"to": "Choose a range of at most one year."})
        self.is_owner = get_accessible_location_ids(request, org) is None
        return locations, start, end

    @staticmethod
    def _date(value):
        from datetime import datetime
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError({"date": "Use the format YYYY-MM-DD."})


class OverviewView(AnalyticsView):
    def get(self, request):
        locations, start, end = self.setup_scope(request)
        return Response(services.overview(locations, start, end))


class MenuView(AnalyticsView):
    def get(self, request):
        locations, start, end = self.setup_scope(request)
        return Response(services.menu(locations, start, end))


class StaffView(AnalyticsView):
    def get(self, request):
        locations, start, end = self.setup_scope(request)
        return Response(services.staff(locations, start, end, include_labor=self.is_owner))   # payroll figures are the owner's only


class InventoryView(AnalyticsView):
    def get(self, request):
        locations, start, end = self.setup_scope(request)
        return Response(services.inventory(locations, start, end))


class CustomersView(AnalyticsView):
    def get(self, request):
        locations, start, end = self.setup_scope(request)
        return Response(services.customers(locations, start, end))


class PlatformView(APIView):
    permission_classes = [IsAuthenticated, IsPlatformUser]

    def get(self, request):
        return Response(platform.platform())
