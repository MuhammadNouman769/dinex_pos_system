from django.urls import path
from apps.accounts.views.auth_view import LoginAPIView, RefreshTokenAPIView

urlpatterns = [
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/refresh/', RefreshTokenAPIView.as_view(), name='token-refresh'),
]