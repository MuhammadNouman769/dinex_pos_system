"""Things a waiter does to an order that is already open: move it to another table, or split the bill."""
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.cash import services as cash
from apps.orders.models import Order, OrderItem, Table
from apps.orders.models.choices import OrderStatus, OrderType, TableStatus

OPEN = (OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY)


def _open_dine_in(order):
    if order.status not in OPEN:
        raise ValidationError({"detail": "This order is already closed."})
    if order.order_type != OrderType.DINE_IN:
        raise ValidationError({"detail": "Only dine-in orders have a table."})


@transaction.atomic
def transfer_table(order, table_id, user):
    _open_dine_in(order)
    try:
        target = Table.objects.select_for_update().get(pk=table_id, location_id=order.location_id, is_active=True)
    except Table.DoesNotExist:
        raise ValidationError({"table": "Choose a table of this branch."})
    if target.pk == order.table_id:
        raise ValidationError({"table": "The order is already on this table."})
    if target.status != TableStatus.AVAILABLE:
        raise ValidationError({"table": f"Table {target.table_number} is {target.get_status_display().lower()}."})
    old = order.table
    order.table = target
    order.save(update_fields=["table", "updated_at"])
    target.status = TableStatus.OCCUPIED
    target.save(update_fields=["status", "updated_at"])
    if old is not None:
        still_open = Order.objects.filter(table=old, status__in=OPEN).exists()
        if not still_open and old.status == TableStatus.OCCUPIED:
            old.status = TableStatus.AVAILABLE
            old.save(update_fields=["status", "updated_at"])
    cash.audit(user, order.location, "table_transfer", order, order_number=order.order_number,
               from_table=old.table_number if old else None, to_table=target.table_number)
    return order


@transaction.atomic
def split_order(order, picks, user, request):
    """Move the chosen quantities of items to a NEW order (same table/waiter/customer). Returns (original, new)."""
    from apps.orders.serializers.order_serializer import OrderSerializer
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status not in OPEN:
        raise ValidationError({"detail": "This order is already closed."})
    if order.payments.exists():
        raise ValidationError({"detail": "A payment was already taken on this order. Split the bill before taking payment."})
    if not picks:
        raise ValidationError({"items": "Choose what goes on the new bill."})

    items = {i.pk: i for i in order.items.filter(is_deleted=False)}
    move = {}
    for p in picks:
        item = items.get(p["item"])
        qty = int(p["quantity"])
        if item is None:
            raise ValidationError({"items": "An item does not belong to this order."})
        if item.deal_id:
            raise ValidationError({"items": f"{item.product_name} is part of a deal and cannot be split."})
        if qty < 1 or qty > item.quantity or p["item"] in move:
            raise ValidationError({"items": f"Wrong quantity for {item.product_name}."})
        move[item.pk] = qty
    remaining = sum(i.quantity - move.get(pk, 0) for pk, i in items.items())
    if remaining < 1:
        raise ValidationError({"items": "Leave at least one item on the original bill."})

    base = {"location": order.location_id, "order_type": order.order_type, "table": order.table_id, "waiter": order.waiter_id,
            "customer_name": order.customer_name, "customer_phone": order.customer_phone, "delivery_address": order.delivery_address,
            "notes": order.notes}
    ser = OrderSerializer(data=base, context={"request": request})
    ser.is_valid(raise_exception=True)
    new = ser.save()
    for pk, qty in move.items():
        item = items[pk]
        if qty == item.quantity:
            item.order = new
            item.save()
        else:
            item.quantity -= qty
            item.save()
            OrderItem.objects.create(order=new, product_variant=item.product_variant, product_name=item.product_name, variant_name=item.variant_name,
                                     quantity=qty, unit_price=item.unit_price, total_price=item.unit_price * qty, notes=item.notes, modifiers=item.modifiers)
    new.calculate_totals()
    order.calculate_totals()
    # the new bill goes through the same kitchen stages as the one it came from
    path = [OrderStatus.CONFIRMED, OrderStatus.PREPARING, OrderStatus.READY]
    for st in path[: path.index(order.status) + 1] if order.status in path else [OrderStatus.CONFIRMED]:
        new.update_status(st, user=user)
    cash.audit(user, order.location, "order_split", order, order_number=order.order_number, new_order=new.order_number,
               moved={str(k): v for k, v in move.items()})
    order.refresh_from_db(); new.refresh_from_db()
    return order, new
