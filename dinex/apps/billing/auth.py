from rest_framework.permissions import SAFE_METHODS
from rest_framework_simplejwt.authentication import JWTAuthentication


class SubscriptionAwareJWTAuthentication(JWTAuthentication):
    """
    JWT login, plus: a restaurant whose subscription is suspended / cancelled / trial-expired
    can still SEE its data but any change is refused with HTTP 402.
    XverLabs platform users are never blocked.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, _ = result
        if request.method in SAFE_METHODS or user.role == "PLATFORM":
            return result
        # A blocked restaurant must still be able to PAY and pick a plan, otherwise it could never come back.
        if request.path.startswith("/api/v1/platform/billing/me/"):
            return result

        from apps.billing.services import SubscriptionBlocked, block_reason, subscription_of
        from apps.organizations.models import OrganizationMembership

        membership = (OrganizationMembership.objects
                      .filter(user=user, is_active=True, organization__is_active=True)
                      .select_related("organization").order_by("id").first())
        if membership is not None:
            reason = block_reason(subscription_of(membership.organization))
            if reason:
                raise SubscriptionBlocked(f"{reason} You can view your data, but changes are disabled. Contact XverLabs.")
        return result
