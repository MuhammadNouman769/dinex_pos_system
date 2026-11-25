from django.urls import path
from apps.cash import views

urlpatterns = [
    path("shifts/current/", views.CurrentShiftView.as_view(), name="shift-current"),
    path("shifts/open/", views.OpenShiftView.as_view(), name="shift-open"),
    path("shifts/", views.ShiftListView.as_view(), name="shift-list"),
    path("shifts/<int:pk>/", views.ShiftDetailView.as_view(), name="shift-detail"),
    path("shifts/<int:pk>/close/", views.CloseShiftView.as_view(), name="shift-close"),
    path("shifts/<int:pk>/reopen/", views.ReopenShiftView.as_view(), name="shift-reopen"),
    path("shifts/<int:pk>/movements/", views.MovementView.as_view(), name="shift-movement"),
    path("orders/<int:pk>/payments/", views.OrderPaymentsView.as_view(), name="order-payments"),
    path("orders/<int:pk>/refund/", views.OrderRefundView.as_view(), name="order-refund"),
    path("reports/sales/", views.SalesReportView.as_view(), name="report-sales"),
    path("audit/", views.AuditLogView.as_view(), name="audit-log"),
]
