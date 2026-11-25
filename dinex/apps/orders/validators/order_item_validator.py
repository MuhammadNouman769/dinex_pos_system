from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_order_item_quantity(value):
    """
    Validate quantity
    
    Rules:
    - Must be greater than 0
    - Maximum 999 (reasonable limit)
    
    Example:
    - ✅ 1
    - ✅ 5
    - ✅ 100
    - ❌ 0 (zero)
    - ❌ -1 (negative)
    - ❌ 1000 (too high)
    """
    if value <= 0:
        raise ValidationError(_("Quantity must be greater than 0."))
    
    if value > 999:
        raise ValidationError(_("Quantity cannot exceed 999."))
    
    return value


def validate_order_item_price(value):
    """
    Validate price
    
    Rules:
    - Cannot be negative
    - Maximum 999,999.99
    
    Example:
    - ✅ 10.00
    - ✅ 100.50
    - ✅ 999.99
    - ❌ -10 (negative)
    - ❌ 1000000 (too high)
    """
    if value < 0:
        raise ValidationError(_("Price cannot be negative."))
    
    if value > 999999.99:
        raise ValidationError(_("Price cannot exceed 999,999.99."))
    
    return value


def validate_order_item_total_price(quantity, unit_price, total_price):
    """
    Validate total price calculation
    
    Rules:
    - Total price should equal quantity * unit_price
    - Cannot be negative
    
    Example:
    - ✅ quantity: 2, unit_price: 10, total: 20
    - ❌ quantity: 2, unit_price: 10, total: 15 (mismatch)
    """
    calculated_total = quantity * unit_price
    
    if total_price != calculated_total:
        raise ValidationError(
            _(f"Total price ({total_price}) does not match quantity * unit_price ({calculated_total}).")
        )
    
    if total_price < 0:
        raise ValidationError(_("Total price cannot be negative."))
    
    return total_price


def validate_order_item_discount(discount_value, unit_price, quantity):
    """
    Validate discount on item
    
    Rules:
    - Discount cannot be negative
    - Discount cannot exceed total item price
    
    Example:
    - ✅ discount: 10, unit_price: 50, quantity: 2 (total: 100)
    - ❌ discount: -10 (negative)
    - ❌ discount: 200, unit_price: 50, quantity: 2 (exceeds)
    """
    if discount_value < 0:
        raise ValidationError(_("Discount cannot be negative."))
    
    total_price = unit_price * quantity
    if discount_value > total_price:
        raise ValidationError(_("Discount cannot exceed item total price."))
    
    return discount_value


def validate_order_item_tax(value):
    """
    Validate tax
    
    Rules:
    - Cannot be negative
    - Maximum 50% (reasonable)
    
    Example:
    - ✅ 0
    - ✅ 5.00
    - ✅ 10.00
    - ❌ -10 (negative)
    - ❌ 60 (too high)
    """
    if value < 0:
        raise ValidationError(_("Tax cannot be negative."))
    
    if value > 50:
        raise ValidationError(_("Tax cannot exceed 50%."))
    
    return value


def validate_order_item_notes(value):
    """
    Validate order item notes
    
    Rules:
    - Optional
    - Maximum 500 characters
    - No harmful content
    
    Example:
    - ✅ "Extra sauce"
    - ✅ "No onions"
    - ❌ "<script>alert('xss')</script>" (harmful content)
    """
    if not value:
        return value
    
    if len(value) > 500:
        raise ValidationError(_("Notes cannot exceed 500 characters."))
    
    # Check for harmful HTML/script tags
    import re
    if re.search(r'<[^>]*>', value):
        raise ValidationError(_("Notes cannot contain HTML tags."))
    
    return value


def validate_order_item_product_variant(product_variant, order):
    """
    Validate product variant belongs to same organization as order
    
    Rules:
    - Product variant must belong to same organization as order
    - Product variant must be active
    
    Example:
    - ✅ Product variant from same organization
    - ❌ Product variant from different organization
    """
    from apps.catalog.models import ProductVariant
    
    if not product_variant:
        return
    
    # Check if product variant belongs to same organization
    if product_variant.product.organization_id != order.location.organization_id:
        raise ValidationError(
            _("Product variant does not belong to this organization.")
        )
    
    # Check if product variant is active
    if not product_variant.is_active:
        raise ValidationError(_("Product variant is not active."))
    
    return product_variant