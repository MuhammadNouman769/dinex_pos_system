from django.urls import path
from apps.payroll import views as v

urlpatterns = [
    path("profiles/", v.ProfilesView.as_view(), name="pay-profiles"),
    path("employees/<int:pk>/profile/", v.ProfileView.as_view(), name="pay-profile"),
    path("runs/", v.RunsView.as_view(), name="payroll-runs"),
    path("runs/<int:pk>/", v.RunView.as_view(), name="payroll-run"),
    path("runs/<int:pk>/<slug:action>/", v.RunActionView.as_view(), name="payroll-run-action"),
    path("slips/<int:pk>/", v.SlipView.as_view(), name="payslip"),
    path("slips/<int:pk>/adjustments/", v.SlipAdjustmentsView.as_view(), name="payslip-adjustments"),
    path("slips/<int:pk>/pay/", v.SlipPayView.as_view(), name="payslip-pay"),
    path("adjustments/<int:pk>/", v.AdjustmentView.as_view(), name="payslip-adjustment"),
    path("advances/", v.AdvancesView.as_view(), name="advances"),
    path("advances/<int:pk>/", v.AdvanceView.as_view(), name="advance"),
    path("advances/<int:pk>/repay/", v.AdvanceRepayView.as_view(), name="advance-repay"),
    path("advances/<int:pk>/void/", v.AdvanceVoidView.as_view(), name="advance-void"),
]
