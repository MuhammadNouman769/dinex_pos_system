
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def validate_positive_number(value):
    """
    Validate that a number is greater than zero.

    Examples:
    - 5       -> valid
    - 0.5     -> valid
    - 0       -> invalid
    - -1      -> invalid
    """

    if value <= 0:
        raise ValidationError(
            _("Value must be greater than 0.")
        )

    return value


def validate_non_negative_number(value):
    """
    Validate that a number is zero or greater.

    Examples:
    - 0       -> valid
    - 5       -> valid
    - -1      -> invalid
    """

    if value < 0:
        raise ValidationError(
            _("Value cannot be negative.")
        )

    return value


def validate_future_date(value):
    """
    Validate that a date/datetime is not in the past.

    Examples:
    - Tomorrow -> valid
    - Next week -> valid
    - Yesterday -> invalid
    """

    if not value:
        return value

    now = timezone.now()

    if isinstance(value, datetime):
        # Handle timezone-aware datetime
        if timezone.is_naive(value):
            value = timezone.make_aware(value)

        if value < now:
            raise ValidationError(
                _("Date cannot be in the past.")
            )

    elif isinstance(value, date):
        if value < timezone.localdate():
            raise ValidationError(
                _("Date cannot be in the past.")
            )

    return value


def validate_past_date(value):
    """
    Validate that a date/datetime is not in the future.

    Examples:
    - Yesterday -> valid
    - Last week -> valid
    - Tomorrow -> invalid
    """

    if not value:
        return value

    now = timezone.now()

    if isinstance(value, datetime):
        # Handle timezone-aware datetime
        if timezone.is_naive(value):
            value = timezone.make_aware(value)

        if value > now:
            raise ValidationError(
                _("Date cannot be in the future.")
            )

    elif isinstance(value, date):
        if value > timezone.localdate():
            raise ValidationError(
                _("Date cannot be in the future.")
            )

    return value


def validate_required_if(value, condition, field_name="Field"):
    """
    Validate that a field is required when condition is True.

    Example:
        validate_required_if(
            address,
            order_type == "DELIVERY",
            "Address"
        )
    """

    if condition and not value:
        raise ValidationError(
            _(f"{field_name} is required.")
        )

    return value


def validate_slug_format(value):
    """
    Validate slug format.

    Rules:
    - Lowercase letters only
    - Numbers allowed
    - Hyphens allowed
    - No spaces
    - No underscores
    - Cannot start or end with a hyphen

    Examples:
    - main-menu              -> valid
    - chicken-burger-001     -> valid
    - Main Menu              -> invalid
    - main_menu              -> invalid
    - -main-menu             -> invalid
    - main-menu-             -> invalid
    """

    if not value:
        return value

    if not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*",
        value,
    ):
        raise ValidationError(
            _(
                "Slug can only contain lowercase letters, "
                "numbers, and hyphens."
            )
        )

    return value


def validate_currency(value):
    """
    Validate currency code.

    Supported currencies:
    - PKR
    - USD
    - EUR
    - GBP
    - AED
    - SAR
    """

    valid_currencies = {
        "PKR",
        "USD",
        "EUR",
        "GBP",
        "AED",
        "SAR",
    }

    if value not in valid_currencies:
        raise ValidationError(
            _(
                f"Invalid currency. Valid options: "
                f"{', '.join(sorted(valid_currencies))}"
            )
        )

    return value


def validate_timezone(value):
    """
    Validate timezone using Python's zoneinfo.

    Examples:
    - Asia/Karachi
    - America/New_York
    - Europe/London
    """

    if not value:
        return value

    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        raise ValidationError(
            _(f"Invalid timezone: {value}")
        )

    return value


def validate_decimal_places(
    value,
    max_digits=12,
    decimal_places=2,
):
    """
    Validate decimal places and maximum digits.

    Examples:
    - 10.50      -> valid
    - 100.00     -> valid
    - 10.555     -> invalid
    """

    if value is None:
        return value

    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(
            _("Value must be a valid number.")
        )

    # Validate decimal places
    exponent = decimal_value.as_tuple().exponent

    if isinstance(exponent, int):
        actual_decimal_places = max(0, -exponent)

        if actual_decimal_places > decimal_places:
            raise ValidationError(
                _(
                    f"Value cannot have more than "
                    f"{decimal_places} decimal places."
                )
            )

    # Validate maximum digits
    digits = len(decimal_value.as_tuple().digits)

    if digits > max_digits:
        raise ValidationError(
            _(
                f"Value cannot have more than "
                f"{max_digits} digits."
            )
        )

    return value


def validate_max_length(
    value,
    max_length,
    field_name="Field",
):
    """
    Validate maximum string length.

    Example:
        validate_max_length(name, 100, "Name")
    """

    if value and len(value) > max_length:
        raise ValidationError(
            _(
                f"{field_name} cannot exceed "
                f"{max_length} characters."
            )
        )

    return value


def validate_min_length(
    value,
    min_length,
    field_name="Field",
):
    """
    Validate minimum string length.

    Example:
        validate_min_length(address, 5, "Address")
    """

    if value and len(value) < min_length:
        raise ValidationError(
            _(
                f"{field_name} must be at least "
                f"{min_length} characters."
            )
        )

    return value


def validate_phone_number(value):
    """
    Basic phone number validation.

    Allows:
    - Spaces
    - Hyphens
    - Parentheses
    - Plus sign

    Examples:
    - +92 300 1234567 -> valid
    - 0300-1234567    -> valid
    - abc123          -> invalid
    """

    if not value:
        return value

    phone_clean = re.sub(
        r"[\s\-\(\)\+]",
        "",
        str(value),
    )

    if not phone_clean.isdigit():
        raise ValidationError(
            _("Phone number must contain only digits and valid separators.")
        )

    if len(phone_clean) < 10:
        raise ValidationError(
            _("Phone number must be at least 10 digits.")
        )

    return value


def validate_percentage(value):
    """
    Validate percentage between 0 and 100.

    Examples:
    - 0       -> valid
    - 50      -> valid
    - 100     -> valid
    - 101     -> invalid
    - -1      -> invalid
    """

    if value < 0 or value > 100:
        raise ValidationError(
            _("Percentage must be between 0 and 100.")
        )

    return value


def validate_order_number(order_number):
    """
    Validate order number format.

    Required format:
        ORD-YYYYMMDD-XXXX

    Examples:
    - ORD-20260908-0042 -> valid
    - ORD-20260908-0001 -> valid
    - ORD-2026-09-08-42  -> invalid
    - ORDER-20260908-0042 -> invalid
    """

    if not order_number:
        raise ValidationError(
            _("Order number is required.")
        )

    pattern = r"^ORD-\d{8}-\d{4}$"

    if not re.fullmatch(pattern, order_number):
        raise ValidationError(
            _(
                "Order number must be in format: "
                "ORD-YYYYMMDD-XXXX"
            )
        )

    return order_number
