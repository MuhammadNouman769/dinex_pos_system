from django.urls import path
from apps.operations import views as v

urlpatterns = [
    path("reservations/", v.ReservationListView.as_view()),
    path("reservations/<int:pk>/", v.ReservationDetailView.as_view()),
    path("reservations/<int:pk>/<str:action>/", v.ReservationActionView.as_view()),
    path("suppliers/", v.SupplierListView.as_view()),
    path("suppliers/<int:pk>/", v.SupplierDetailView.as_view()),
    path("purchases/", v.PurchaseListView.as_view()),
    path("purchases/<int:pk>/pay/", v.PurchasePayView.as_view()),
    path("expenses/", v.ExpenseListView.as_view()),
    path("expenses/<int:pk>/", v.ExpenseDetailView.as_view()),
    path("reports/day/", v.DayReportView.as_view()),
]
