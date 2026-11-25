import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.orders.models.choices import TableStatus


def validate_table_number(value):
    """
    Validate table number format
    
    Rules:
    - Required field
    - Format: T-1, T-2, T-5, etc.
    - Number must be positive
    
    Example:
    - ✅ T-1
    - ✅ T-5
    - ✅ T-12
    - ❌ T1 (missing hyphen)
    - ❌ T-0 (zero)
    - ❌ T- (no number)
    """
    if not value:
        raise ValidationError(_("Table number is required."))
    
    # Remove spaces
    value = value.strip()
    
    # Check format: T-1, T-2, T-5, etc.
    if not re.match(r'^[Tt]\-\d+$', value):
        raise ValidationError(_("Table number must be in format: T-1, T-2, T-5, etc."))
    
    # Extract number
    try:
        number = int(value.split('-')[1])
        if number <= 0:
            raise ValidationError(_("Table number must be a positive number."))
    except (IndexError, ValueError):
        raise ValidationError(_("Invalid table number format."))
    
    return value.upper()


def validate_table_capacity(value):
    """
    Validate table capacity
    
    Rules:
    - Minimum 1 person
    - Maximum 20 persons
    
    Example:
    - ✅ 2
    - ✅ 4
    - ✅ 10
    - ❌ 0 (zero)
    - ❌ 25 (too high)
    """
    if value < 1:
        raise ValidationError(_("Table capacity must be at least 1."))
    
    if value > 20:
        raise ValidationError(_("Table capacity cannot exceed 20 persons."))
    
    return value


def validate_table_status_transition(current_status, new_status):
    """
    Validate table status transition
    
    Rules:
    - AVAILABLE → OCCUPIED or RESERVED
    - OCCUPIED → AVAILABLE or CLEANING
    - RESERVED → OCCUPIED or AVAILABLE
    - CLEANING → AVAILABLE
    
    Example:
    - ✅ AVAILABLE → OCCUPIED (allowed)
    - ✅ OCCUPIED → AVAILABLE (allowed)
    - ❌ AVAILABLE → CLEANING (not allowed)
    - ❌ CLEANING → OCCUPIED (not allowed)
    """
    valid_transitions = {
        TableStatus.AVAILABLE: [TableStatus.OCCUPIED, TableStatus.RESERVED],
        TableStatus.OCCUPIED: [TableStatus.AVAILABLE, TableStatus.CLEANING],
        TableStatus.RESERVED: [TableStatus.OCCUPIED, TableStatus.AVAILABLE],
        TableStatus.CLEANING: [TableStatus.AVAILABLE],
    }
    
    allowed = valid_transitions.get(current_status, [])
    
    if new_status not in allowed:
        raise ValidationError(
            _(f"Cannot transition from {current_status} to {new_status}. "
              f"Allowed transitions: {', '.join(allowed) if allowed else 'None'}")
        )
    
    return True


def validate_table_occupancy(table, force=False):
    """
    Validate table occupancy
    
    Rules:
    - Cannot occupy already occupied table
    - Cannot free already free table
    
    Example:
    - ✅ Occupy available table
    - ✅ Free occupied table
    - ❌ Occupy occupied table
    - ❌ Free available table
    """
    if not force:
        if table.status == TableStatus.OCCUPIED:
            raise ValidationError(_(f"Table {table.table_number} is already occupied."))
        
        if table.status == TableStatus.AVAILABLE:
            raise ValidationError(_(f"Table {table.table_number} is already available."))
    
    return True


def validate_table_location(table, location):
    """
    Validate table belongs to location
    
    Rules:
    - Table must belong to same location
    
    Example:
    - ✅ Table in same location
    - ❌ Table in different location
    """
    if table.location_id != location.id:
        raise ValidationError(_("Table does not belong to this location."))
    
    return True