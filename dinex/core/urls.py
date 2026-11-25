from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from apps.accounts.views.health_view import HealthView
from apps.accounts.views.me_view import MeAPIView
from apps.accounts.views.password_view import ChangePasswordView
from apps.accounts.views.reset_view import ForgotPasswordView, ResetPasswordView, EmailRequestView, EmailConfirmView
from django.urls import include, path
from apps.billing.public import PublicPlansView, SignupView

from apps.accounts.schemas.auth_schema import LoginAPIView

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)


# ============================================================
# MAIN URL CONFIGURATION
# ============================================================

urlpatterns = [

    # ============================================================
    # DJANGO ADMIN
    # ============================================================
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    # ============================================================
    # AUTHENTICATION
    # ============================================================
    # Platform/User Login
    path("api/v1/auth/token/",LoginAPIView.as_view(),name="token-obtain",),
    # Refresh JWT
    path("api/v1/auth/me/", MeAPIView.as_view(), name="auth-me"),
    path("api/v1/auth/forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("api/v1/auth/reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("api/v1/auth/email/request/", EmailRequestView.as_view(), name="email-request"),
    path("api/v1/auth/email/confirm/", EmailConfirmView.as_view(), name="email-confirm"),
    path("api/v1/auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("api/v1/auth/token/refresh/",TokenRefreshView.as_view(),name="token-refresh",),
    # ============================================================
    # ORGANIZATIONS
    # ============================================================
    path("api/v1/organizations/",include("apps.organizations.urls"),),
    # ============================================================
    # ONBOARDING
    # ============================================================
    path("api/v1/onboarding/",include("apps.onboarding.urls"),),
    # ============================================================
    # CATALOG
    # ============================================================
    path("api/v1/catalog/",include("apps.catalog.urls"),),
    # ============================================================  
    # Customers
    # ============================================================
    path('api/v1/customers/', include('apps.customers.urls')),
    # ============================================================
    # Orders
    # ============================================================
    path('api/v1/orders/', include('apps.orders.urls')),

    path('api/v1/inventory/', include('apps.inventory.urls')),
    path('api/v1/cash/', include('apps.cash.urls')),
    path('api/v1/operations/', include('apps.operations.urls')),
    path('api/v1/loyalty/', include('apps.loyalty.urls')),
    path('api/v1/platform/', include('apps.billing.urls')),
    path('api/v1/public/plans/', PublicPlansView.as_view(), name='public-plans'),
    path('api/v1/public/signup/', SignupView.as_view(), name='public-signup'),
    path('api/v1/staff/', include('apps.staff.urls')),
    path('api/v1/payroll/', include('apps.payroll.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
]

if settings.ENABLE_API_DOCS:       # interactive API docs: development only unless explicitly enabled
    urlpatterns += [
        # ============================================================
        # API SCHEMA
        # ============================================================
        path("api/schema/",SpectacularAPIView.as_view(),name="schema",),
        # ============================================================
        # SWAGGER
        # ============================================================
        path("api/docs/",SpectacularSwaggerView.as_view(url_name="schema",),name="swagger-ui",),

    ]

# Uploaded product images (production serves /media/ from the proxy)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
