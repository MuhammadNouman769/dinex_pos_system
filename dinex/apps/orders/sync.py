"""
One-shot order placement used by the POS (online and offline).

The terminal sends the WHOLE order in a single request: items, deals and any payments already taken.
It carries a `client_uuid` made on the terminal, so if the request is repeated (flaky network, the
terminal retrying after a timeout) the server returns the order it already made instead of a second one.

Rules
- Prices always come from the catalog, never from the client.
- A deal is expanded into its items; the deal's discount is added to the order discount by the server.
- A manual discount still needs a manager / owner.
- A payment that cannot be recorded (no open shift, wrong amount) does NOT lose the order: the order is
  saved and the problem is returned as a warning.
- Payments taken offline go to the shift the cashier had open when the order was placed.
"""
import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.catalog.models import Deal, DealLocation
from apps.cash import services as cash
from apps.orders.models import Order, OrderItem
from apps.orders.serializers.order_item_serializer import OrderItemSerializer
from apps.orders.serializers.order_serializer import OrderSerializer
from apps.utils.helpers import is_manager_or_owner

MAX_OFFLINE_AGE = timedelta(days=14)
CENTS = Decimal("0.01")


class SyncItem(serializers.Serializer):
    product_variant = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=999)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
    modifiers = serializers.ListField(child=serializers.IntegerField(), required=False, max_length=20)


class SyncDeal(serializers.Serializer):
    deal = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=99)


class SyncPayment(serializers.Serializer):
    method = serializers.ChoiceField(choices=cash.PaymentMethod.choices)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    tendered = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    reference = serializers.CharField(required=False, allow_blank=True, max_length=100)


class SyncOrderSerializer(serializers.Serializer):
    client_uuid = serializers.UUIDField()
    location = serializers.IntegerField()
    order_type = serializers.CharField()
    table = serializers.IntegerField(required=False, allow_null=True)
    waiter = serializers.IntegerField(required=False, allow_null=True)
    customer_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    customer_phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=Decimal("0"))
    placed_at = serializers.DateTimeField(required=False, allow_null=True)
    offline = serializers.BooleanField(required=False, default=False)
    items = SyncItem(many=True, required=False)
    deals = SyncDeal(many=True, required=False)
    payments = SyncPayment(many=True, required=False)

    def validate(self, data):
        if not data.get("items") and not data.get("deals"):
            raise serializers.ValidationError({"items": "Add at least one item or deal."})
        return data


def _existing(location_id, client_uuid):
    return Order.all_objects.filter(location_id=location_id, client_uuid=client_uuid).first()


def _deal_for(deal_id, org_id, location_id, now):
    deal = (Deal.objects.filter(pk=deal_id, organization_id=org_id, is_active=True)
            .prefetch_related("items__product_variant__product", "locations").first())
    if deal is None:
        raise ValidationError({"deals": f"Deal {deal_id} is not available."})
    if not (deal.start_at <= now <= deal.end_at):
        raise ValidationError({"deals": f"Deal '{deal.name}' is not running right now."})
    rows = list(deal.locations.all())
    if rows and not any(r.location_id == location_id and r.is_enabled for r in rows):
        raise ValidationError({"deals": f"Deal '{deal.name}' is not available at this branch."})
    if not deal.items.exists():
        raise ValidationError({"deals": f"Deal '{deal.name}' has no items."})
    return deal


def deal_discount(deal):
    """Discount for ONE unit of the deal, from the catalog prices."""
    base = sum((di.product_variant.base_price * di.quantity for di in deal.items.all()), Decimal("0"))
    if deal.discount_type == Deal.DiscountType.PERCENTAGE:
        off = base * min(deal.discount_value, Decimal("100")) / Decimal("100")
    else:
        off = deal.discount_value
    return min(off, base).quantize(CENTS)


def _apply_options(item, option_ids):
    """Record the chosen dish options and add their prices to the line."""
    if not option_ids and not item.product_variant.product.modifier_group_links.filter(is_deleted=False, modifier_group__is_active=True).exists():
        return
    from apps.catalog.modifiers import resolve
    snapshot, extra = resolve(item.product_variant.product, option_ids)
    if snapshot:
        item.modifiers = snapshot
        item.unit_price = item.unit_price + extra
        item.save()


def place_order(request, organization_id, raw):
    """Returns (order, created, info). Raises DRF ValidationError for a bad order."""
    ser = SyncOrderSerializer(data=raw)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data

    from django.shortcuts import get_object_or_404
    from apps.organizations.models import Location
    from apps.utils.helpers import location_model_scope
    location = get_object_or_404(Location, id=d["location"], **location_model_scope(request, organization_id))

    found = _existing(location.id, d["client_uuid"])
    if found is not None:
        return found, False, {"stock_warnings": [], "payment_warnings": []}

    try:
        with transaction.atomic():
            return _create(request, organization_id, location, d)
    except IntegrityError:
        found = _existing(location.id, d["client_uuid"])      # two copies raced: keep the first
        if found is not None:
            return found, False, {"stock_warnings": [], "payment_warnings": []}
        raise


def _create(request, organization_id, location, d):
    user, now = request.user, timezone.now()
    placed_at = d.get("placed_at")
    if placed_at is not None and (placed_at > now or now - placed_at > MAX_OFFLINE_AGE):
        placed_at = None                                      # clock was wrong: use server time

    manual_discount = d.get("discount") or Decimal("0")
    if manual_discount > 0 and not is_manager_or_owner(request, location):
        raise ValidationError({"discount": "Only a manager or the owner can give a discount."})

    base = {k: d[k] for k in ("order_type", "customer_name", "customer_phone", "delivery_address", "notes") if k in d}
    base.update(location=location.id, table=d.get("table"), waiter=d.get("waiter"), discount=manual_discount)
    order_ser = OrderSerializer(data=base, context={"request": request})
    order_ser.is_valid(raise_exception=True)
    order = order_ser.save(client_uuid=d["client_uuid"], is_offline=d.get("offline", False))
    if d.get("customer_phone"):
        from apps.loyalty import services as loyalty
        if loyalty.get_settings(organization_id) and loyalty.get_settings(organization_id).enabled:
            c = loyalty.link_customer(location, d.get("customer_name", ""), d["customer_phone"], d.get("customer_email", ""))
            if c:
                Order.objects.filter(pk=order.pk).update(customer=c)
                order.customer = c

    for it in d.get("items", []):
        item_ser = OrderItemSerializer(data={"order": order.id, "product_variant": it["product_variant"],
                                             "quantity": it["quantity"], "notes": it.get("notes", "")},
                                       context={"request": request})
        item_ser.is_valid(raise_exception=True)
        item = item_ser.save()
        _apply_options(item, it.get("modifiers", []))

    deals_total = Decimal("0")
    deal_names = []
    for dd in d.get("deals", []):
        deal = _deal_for(dd["deal"], organization_id, location.id, now)
        for di in deal.items.all():
            item_ser = OrderItemSerializer(data={"order": order.id, "product_variant": di.product_variant_id,
                                                 "quantity": di.quantity * dd["quantity"]}, context={"request": request})
            item_ser.is_valid(raise_exception=True)
            item = item_ser.save()
            OrderItem.objects.filter(pk=item.pk).update(deal=deal, deal_name=deal.name[:255])
        deals_total += deal_discount(deal) * dd["quantity"]
        deal_names.append(f"{deal.name} x{dd['quantity']}")

    if deals_total > 0:
        order.discount = (order.discount or Decimal("0")) + deals_total
        order.save(update_fields=["discount", "updated_at"])
        cash.audit(user, location, "discount", order, order_number=order.order_number,
                   discount=order.discount, deals=deal_names)
    order.calculate_totals()

    order.update_status(Order.OrderStatus.CONFIRMED, user=user)
    info = {"stock_warnings": list(getattr(order, "stock_warnings", [])), "payment_warnings": []}

    if placed_at is not None:
        Order.all_objects.filter(pk=order.pk).update(created_at=placed_at, confirmed_at=placed_at)

    for p in d.get("payments", []):
        when = placed_at or now
        shift = cash.shift_at(user, location.id, when) if placed_at else cash.current_shift(user, location.id)
        shift = shift or cash.current_shift(user, location.id)
        try:
            cash.take_payment(order, user, p["method"], p["amount"], tendered=p.get("tendered"),
                              reference=p.get("reference", ""), shift=shift, at=placed_at)
        except Exception as exc:                              # CashError / APIException: never lose the order
            detail = getattr(exc, "detail", None)
            info["payment_warnings"].append(str(detail if detail is not None else exc))

    order.refresh_from_db()
    return order, True, info
