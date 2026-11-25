from django.utils import timezone
from apps.orders.models.order import Order


def generate_order_number(location_id):
    """
    Next order number for a location: ORD-YYYYMMDD-XXXX

    - uses the *local* (Asia/Karachi) date, not UTC
    - counts soft-deleted orders too (their numbers stay reserved)
    - picks the numeric max, so it keeps working after 9999
    Uniqueness is enforced per location by a DB constraint; callers
    should retry on IntegrityError (see OrderSerializer.create).
    """
    today = timezone.localdate()
    prefix = f"ORD-{today.strftime('%Y%m%d')}"

    numbers = Order.all_objects.filter(
        location_id=location_id,
        order_number__startswith=f"{prefix}-",
    ).values_list("order_number", flat=True)

    max_seq = 0
    for number in numbers:
        try:
            max_seq = max(max_seq, int(number.rsplit("-", 1)[-1]))
        except ValueError:
            continue

    return f"{prefix}-{max_seq + 1:04d}"
