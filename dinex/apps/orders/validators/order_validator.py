import re
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.orders.models.choices import OrderStatus, OrderType


def validate_order_status_transition(current_status, new_status):
    """
    Validate if status transition is allowed
    
    Rules:
    - PENDING → CONFIRMED or CANCELLED
    - CONFIRMED → PREPARING or CANCELLED
    - PREPARING → READY or CANCELLED
    - READY → OUT_FOR_DELIVERY, COMPLETED, or CANCELLED
    - OUT_FOR_DELIVERY → COMPLETED or CANCELLED
    - COMPLETED → No transitions
    - CANCELLED → No transitions
    
    Example:
    -  PENDING → CONFIRMED (allowed)
    -  PENDING → COMPLETED (not allowed)
    -  COMPLETED → CANCELLED (not allowed)
    """
    valid_transitions = {
        OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
        OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
        OrderStatus.PREPARING: [OrderStatus.READY, OrderStatus.CANCELLED],
        OrderStatus.READY: [OrderStatus.OUT_FOR_DELIVERY, OrderStatus.COMPLETED, OrderStatus.CANCELLED],
        OrderStatus.OUT_FOR_DELIVERY: [OrderStatus.COMPLETED, OrderStatus.CANCELLED],
        OrderStatus.COMPLETED: [],
        OrderStatus.CANCELLED: [],
    }
    
    allowed = valid_transitions.get(current_status, [])
    
    if new_status not in allowed:
        raise ValidationError(
            _(f"Cannot transition from {current_status} to {new_status}. "
              f"Allowed transitions: {', '.join(allowed) if allowed else 'None'}")
        )
    
    return True


def validate_order_type(order_type, table=None, delivery_address=None):
    """
    Validate order type specific requirements
    
    Rules:
    - DINE_IN: Table is required
    - DELIVERY: Delivery address is required
    - TAKEAWAY: No additional requirements
    
    Example:
    -  DINE_IN with table T-5
    -  DELIVERY with address
    -  DINE_IN without table
    -  DELIVERY without address
    """
    if order_type == OrderType.DINE_IN:
        if not table:
            raise ValidationError(_("Table is required for Dine In orders."))
    
    elif order_type == OrderType.DELIVERY:
        if not delivery_address:
            raise ValidationError(_("Delivery address is required for Delivery orders."))
        if len(delivery_address.strip()) < 5:
            raise ValidationError(_("Delivery address must be at least 5 characters."))
    
    elif order_type == OrderType.TAKEAWAY:
        # Takeaway only needs customer name
        pass
    
    return True


def validate_order_dates(start_date, end_date):
    """
    Validate order dates
    
    Rules:
    - Start date cannot be after end date
    - Start date cannot be in future
    - End date must be after now
    
    Example:
    -  start: 2026-09-08, end: 2026-09-10
    -  start: 2026-09-10, end: 2026-09-08 (start > end)
    -  start: 2026-09-10 (future date)
    """
    if start_date and end_date:
        if start_date > end_date:
            raise ValidationError(_("Start date cannot be after end date."))
    
    if start_date and start_date > timezone.now():
        raise ValidationError(_("Start date cannot be in the future."))
    
    return True


def validate_order_discount(discount_value, subtotal):
    """
    Validate discount
    
    Rules:
    - Discount cannot be negative
    - Discount cannot exceed subtotal
    
    Example:
    -  discount: 50, subtotal: 1000
    -  discount: 0
    -  discount: -10 (negative)
    -  discount: 2000, subtotal: 1000 (exceeds)
    """
    if discount_value < 0:
        raise ValidationError(_("Discount cannot be negative."))
    
    if subtotal and discount_value > subtotal:
        raise ValidationError(_("Discount cannot exceed subtotal amount."))
    
    return discount_value


def validate_order_amount(amount):
    """
    Validate order amount
    
    Rules:
    - Amount cannot be negative
    - Amount cannot be zero
    
    Example:
    -  1000.00
    -  50.00
    -  -100 (negative)
    -  0 (zero)
    """
    if amount < 0:
        raise ValidationError(_("Order amount cannot be negative."))
    
    if amount == 0:
        raise ValidationError(_("Order amount cannot be zero."))
    
    return amount


def validate_customer_phone_for_order(phone, order_type):
    """
    Validate customer phone for order
    
    Rules:
    - Required for delivery orders
    - Optional for dine in orders
    
    Example:
    -  DELIVERY with phone
    -  DINE_IN without phone
    -  DELIVERY without phone
    """
    if order_type == OrderType.DELIVERY:
        if not phone:
            raise ValidationError(_("Phone number is required for delivery orders."))
        
        # Basic phone validation
        phone_clean = re.sub(r'[\s\-\(\)\+]', '', str(phone))
        if len(phone_clean) < 10:
            raise ValidationError(_("Phone number must be at least 10 digits."))
        if not phone_clean.isdigit():
            raise ValidationError(_("Phone number must contain only digits."))
    
    return phone


def validate_delivery_address_for_order(address):
    """
    Validate delivery address
    
    Rules:
    - Required for delivery orders
    - Minimum 5 characters
    
    Example:
    -  House #5, Street 12, Islamabad
    -  "Home" (too short)
    """
    if not address or len(address.strip()) < 5:
        raise ValidationError(_("Delivery address must be at least 5 characters."))
    
    return address.strip()


def validate_order_number(order_number):
    """
    Validate order number format
    
    Rules:
    - Format: ORD-YYYYMMDD-XXXX
    - Must be unique
    
    Example:
    -  ORD-20260908-0042
    -  ORD-2026-09-08-0042 (wrong format)
    -  ORDER-20260908-0042 (wrong prefix)
    """
    import re
    pattern = r'^ORD-\d{8}-\d{4}$'
    if not re.match(pattern, order_number):
        raise ValidationError(_("Order number must be in format: ORD-YYYYMMDD-XXXX"))
    return order_number