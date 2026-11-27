"""Module-level aliases of the role choice sets, so the API docs can give each one a clear name."""
from apps.accounts.models.user_model import User
from apps.organizations.models.location_membership import LocationMembership
from apps.organizations.models.membership import OrganizationMembership
from apps.staff.models import Role as StaffRole

PLATFORM_USER_ROLES = User.Role.choices
ORGANIZATION_ROLES = OrganizationMembership.Role.choices
BRANCH_ROLES = LocationMembership.Role.choices
STAFF_ROLES = StaffRole.choices
