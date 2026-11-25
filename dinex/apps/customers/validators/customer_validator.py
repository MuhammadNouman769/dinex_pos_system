import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_customer_phone(value):
    """
    Validate phone number format for customers
    
    Rules:
    - Required field
    - Must be 10-15 digits
    - Must contain only digits
    - Must start with 03 or 0 (Pakistan format)
    
    Example:
    -  03001234567
    -  0300-1234567 (after cleaning)
    -  123456 (too short)
    -  abc123 (contains letters)
    """
    if not value:
        raise ValidationError(_("Phone number is required."))
    
    # Remove spaces, hyphens, parentheses, plus signs
    phone = re.sub(r'[\s\-\(\)\+]', '', str(value))
    
    # Check if only digits
    if not phone.isdigit():
        raise ValidationError(_("Phone number must contain only digits."))
    
    # Check length (10-15 digits)
    if len(phone) < 10:
        raise ValidationError(_("Phone number must be at least 10 digits."))
    
    if len(phone) > 15:
        raise ValidationError(_("Phone number cannot exceed 15 digits."))
    
    # Check if starts with valid prefix (for Pakistan)
    if not phone.startswith(('03', '0')):
        raise ValidationError(_("Phone number must start with 03 or 0."))
    
    return phone


def validate_customer_email(value):
    """
    Validate email format for customers
    
    Rules:
    - Optional field (can be blank)
    - Must be valid email format
    - Must contain @ and .
    
    Example:
    -  nouman@example.com
    -  ali.hassan@company.com
    -  invalid-email (no @)
    -  user@domain (no .)
    """
    if not value:
        return value  # Email is optional
    
    # Basic email validation
    if '@' not in value or '.' not in value:
        raise ValidationError(_("Please enter a valid email address."))
    
    # Check for valid email format using regex
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, value):
        raise ValidationError(_("Please enter a valid email address."))
    
    return value


def validate_customer_name(value, field_name="Name"):
    """
    Validate customer name
    
    Rules:
    - Required field
    - Minimum 2 characters
    - Maximum 100 characters
    - Only letters, spaces, hyphens, apostrophes
    
    Example:
    -  Muhammad Nouman
    -  Ali-Hassan
    -  O'Connor
    -  (empty)
    -  123 (numbers only)
    """
    if not value:
        raise ValidationError(_(f"{field_name} is required."))
    
    if len(value.strip()) < 2:
        raise ValidationError(_(f"{field_name} must be at least 2 characters."))
    
    if len(value) > 100:
        raise ValidationError(_(f"{field_name} cannot exceed 100 characters."))
    
    # Only letters, spaces, hyphens, apostrophes, dots
    if not re.match(r'^[a-zA-Z\s\-\.\']+$', value):
        raise ValidationError(_(f"{field_name} can only contain letters, spaces, hyphens, and apostrophes."))
    
    return value.strip()


def validate_customer_address(value):
    """
    Validate customer address
    
    Rules:
    - Optional field (except for delivery)
    - Minimum 5 characters
    - Maximum 500 characters
    
    Example:
    -  House #5, Street 12, Islamabad
    -  Office #3, Blue Area, Islamabad
    -  "Home" (too short)
    """
    if not value:
        return value  # Address is optional
    
    if len(value.strip()) < 5:
        raise ValidationError(_("Address must be at least 5 characters."))
    
    if len(value) > 500:
        raise ValidationError(_("Address cannot exceed 500 characters."))
    
    return value.strip()


def validate_customer_type(value):
    """
    Validate customer type
    
    Rules:
    - Must be one of: WALK_IN, REGULAR, CORPORATE
    
    Example:
    -  WALK_IN
    -  REGULAR
    -  CORPORATE
    -  VIP (invalid choice)
    """
    valid_types = ['WALK_IN', 'REGULAR', 'CORPORATE']
    if value not in valid_types:
        raise ValidationError(_(f"Invalid customer type. Must be one of: {', '.join(valid_types)}"))
    return value