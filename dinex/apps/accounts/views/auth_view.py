from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenObtainPairView

@extend_schema(
    tags=["Authentication"],
    summary="Login and obtain JWT tokens",
    description="Authenticate a platform or restaurant user using username and password.",
)
class LoginAPIView(TokenObtainPairView):
    pass