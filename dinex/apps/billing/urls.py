from django.urls import path
from apps.billing import views as v

urlpatterns = [
    path("overview/", v.PlatformOverviewView.as_view(), name="platform-overview"),
    path("plans/", v.PlanListCreateView.as_view(), name="platform-plans"),
    path("plans/<int:pk>/", v.PlanDetailView.as_view(), name="platform-plan"),
    path("restaurants/", v.RestaurantListCreateView.as_view(), name="platform-restaurants"),
    path("restaurants/<int:pk>/", v.RestaurantDetailView.as_view(), name="platform-restaurant"),
    path("restaurants/<int:pk>/subscription/", v.SubscriptionActionView.as_view(), name="platform-subscription"),
    path("restaurants/<int:pk>/reset-password/", v.ResetOwnerPasswordView.as_view(), name="platform-reset-password"),
    path("restaurants/<int:pk>/invoices/", v.RestaurantInvoiceCreateView.as_view(), name="platform-invoice-create"),
    path("invoices/", v.InvoiceListView.as_view(), name="platform-invoices"),
    path("invoices/<int:pk>/pay/", v.InvoicePayView.as_view(), name="platform-invoice-pay"),
    path("invoices/<int:pk>/void/", v.InvoiceVoidView.as_view(), name="platform-invoice-void"),
    path("billing/me/", v.MyBillingView.as_view(), name="my-billing"),
    path("billing/me/payments/", v.MyPaymentsView.as_view(), name="my-payments"),
    path("billing/me/select-plan/", v.MySelectPlanView.as_view(), name="my-select-plan"),
    path("payments/", v.PaymentSubmissionListView.as_view(), name="platform-payments"),
    path("payments/<int:pk>/approve/", v.PaymentSubmissionApproveView.as_view(), name="platform-payment-approve"),
    path("payments/<int:pk>/reject/", v.PaymentSubmissionRejectView.as_view(), name="platform-payment-reject"),
    path("payment-accounts/", v.PaymentAccountListCreateView.as_view(), name="platform-payment-accounts"),
    path("payment-accounts/<int:pk>/", v.PaymentAccountDetailView.as_view(), name="platform-payment-account"),
]
