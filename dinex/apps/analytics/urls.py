from django.urls import path
from apps.analytics import views as v

urlpatterns = [
    path("overview/", v.OverviewView.as_view(), name="analytics-overview"),
    path("menu/", v.MenuView.as_view(), name="analytics-menu"),
    path("staff/", v.StaffView.as_view(), name="analytics-staff"),
    path("inventory/", v.InventoryView.as_view(), name="analytics-inventory"),
    path("customers/", v.CustomersView.as_view(), name="analytics-customers"),
    path("platform/", v.PlatformView.as_view(), name="analytics-platform"),
]
