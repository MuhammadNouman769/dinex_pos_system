from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.utils.models import BaseModel
from apps.orders.models.choices import OrderType, OrderStatus, PaymentStatus, PaymentMethod, TableStatus


class Order(BaseModel):
    # Expose enums on the class so Order.OrderStatus.X works everywhere
    OrderType = OrderType
    OrderStatus = OrderStatus
    PaymentStatus = PaymentStatus
    PaymentMethod = PaymentMethod

    """
    Order Model - Linked to Location
    """
    
    # Location is required for every order
    location = models.ForeignKey(
        "organizations.Location",
        on_delete=models.PROTECT,
        related_name="orders",
        help_text="Location where order is placed"
    )

    # Customer is optional (for walk-in customers)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="Customer who placed the order"
    )

    # Order Number (Unique per location)
    order_number = models.CharField(
        max_length=50,
        help_text="Order number (e.g., ORD-20260908-0042), unique per location"
    )

    # Order Type
    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
        db_index=True,
        help_text="Order type"
    )

    # For Dine In
    table = models.ForeignKey(
        "orders.Table",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="Table number for dine in"
    )

    # Customer details (denormalized for order snapshot)
    customer_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Customer name (snapshot)"
    )

    customer_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Customer phone (snapshot)"
    )

    delivery_address = models.TextField(
        blank=True,
        help_text="Delivery address"
    )

    # Order details
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Subtotal before tax/discount"
    )

    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Tax amount"
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Discount amount"
    )

    waiter = models.ForeignKey(
        "staff.Employee", null=True, blank=True, on_delete=models.SET_NULL, related_name="served_orders",
        help_text="Waiter who took the order",
    )
    rider = models.ForeignKey(
        "staff.Employee", null=True, blank=True, on_delete=models.SET_NULL, related_name="delivered_orders",
        help_text="Rider who delivers it",
    )
    dispatched_at = models.DateTimeField(null=True, blank=True, help_text="Rider left with the order")
    delivered_at = models.DateTimeField(null=True, blank=True, help_text="Order reached the customer")

    cancel_reason = models.CharField(max_length=255, blank=True)
    cancelled_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )

    client_uuid = models.UUIDField(
        null=True, blank=True, editable=False,
        help_text="Id made by the POS terminal. Lets an order that was saved offline be sent twice without duplicating it",
    )
    is_offline = models.BooleanField(default=False, help_text="Taken while the terminal had no internet, then synced")

    stock_deducted = models.BooleanField(
        default=False, help_text="Ingredients for this order were deducted from stock",
    )

    service_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Service charge (location rate x subtotal)",
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total amount"
    )

    # Status
    status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True,
        help_text="Order status"
    )

    # Payment
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        help_text="Payment status"
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        blank=True,
        help_text="Payment method"
    )

    # Staff/User who created
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders_created",
        help_text="Staff who created order"
    )

    # Timestamps
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Order confirmed timestamp"
    )

    preparing_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Order preparing timestamp"
    )

    ready_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Order ready timestamp"
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Order completed timestamp"
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Order cancelled timestamp"
    )

    estimated_time = models.PositiveIntegerField(
        default=30,
        help_text="Estimated preparation time in minutes"
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "order_number"],
                name="unique_order_number_per_location",
            ),
            models.UniqueConstraint(
                fields=["location", "client_uuid"],
                condition=models.Q(client_uuid__isnull=False),
                name="unique_client_uuid_per_location",
            ),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.order_type} - {self.status}"

    def update_status(self, new_status, user=None, reason=""):
        """
        Update order status with timestamp
        
        ✅ Fixed: Using OrderStatus directly instead of self.OrderStatus
        """
        valid_transitions = {
            OrderStatus.PENDING: [
                OrderStatus.CONFIRMED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.CONFIRMED: [
                OrderStatus.PREPARING,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.PREPARING: [
                OrderStatus.READY,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.READY: [
                OrderStatus.OUT_FOR_DELIVERY,
                OrderStatus.COMPLETED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.OUT_FOR_DELIVERY: [
                OrderStatus.COMPLETED,
                OrderStatus.CANCELLED,
            ],
            OrderStatus.COMPLETED: [],
            OrderStatus.CANCELLED: [],
        }

        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")

        # Order-type rules: only delivery orders go out for delivery, and a
        # delivery order must be handed over (OUT_FOR_DELIVERY) before completing.
        if new_status == OrderStatus.OUT_FOR_DELIVERY and self.order_type != OrderType.DELIVERY:
            raise ValueError("Only delivery orders can be sent out for delivery.")
        if (
            new_status == OrderStatus.COMPLETED
            and self.order_type == OrderType.DELIVERY
            and self.status == OrderStatus.READY
        ):
            raise ValueError("A delivery order must go out for delivery before it is completed.")

        from django.db import transaction
        from apps.cash import services as cash
        from apps.inventory.services import sync_stock_for_order

        reason = (reason or "").strip()
        if new_status == OrderStatus.CANCELLED:
            if len(reason) < 3:
                raise ValueError("A reason is required to cancel an order.")
            paid, refunded = cash.paid_and_refunded(self)
            if paid - refunded > 0:
                raise ValueError("This order has been paid. Refund the payment first, then cancel.")
        if new_status == OrderStatus.OUT_FOR_DELIVERY and not self.rider_id:
            raise ValueError("Assign a rider before sending the order out for delivery.")
        # Cash-on-delivery: the rider collects the money, so a delivered order may complete unpaid
        # (the rider then owes that cash until a cashier settles it).
        cod_with_rider = (self.order_type == OrderType.DELIVERY and self.status == OrderStatus.OUT_FOR_DELIVERY and bool(self.rider_id))
        if new_status == OrderStatus.COMPLETED and self.total_amount > 0 and cash.amount_due(self) > 0 and not cod_with_rider:
            raise ValueError("Take payment before completing the order.")

        previous = self.status
        with transaction.atomic():
            self.status = new_status
            fields = ["status", "updated_at"] + self._set_status_timestamp(new_status)
            if new_status == OrderStatus.CANCELLED:
                self.cancel_reason = reason[:255]
                self.cancelled_by = user if getattr(user, "is_authenticated", False) else None
                fields += ["cancel_reason", "cancelled_by"]
            # Save ONLY what a status change touches. A full save() would write back this object's
            # (possibly stale) payment_status / totals / stock flag and undo a payment taken a moment ago.
            self.save(update_fields=fields)

            if new_status == OrderStatus.CANCELLED:
                cash.audit(user, self.location, "order_cancelled", self, order_number=self.order_number,
                           total=self.total_amount, reason=reason, was=previous)
            if new_status == OrderStatus.COMPLETED and self.customer_id:
                self.customer.add_order(self.total_amount)

            # Stock: confirm sends the order to the kitchen -> deduct ingredients.
            # Cancelling before cooking started gives them back.
            self.stock_warnings = []
            if new_status == OrderStatus.CONFIRMED:
                self.stock_warnings = sync_stock_for_order(self)
            elif new_status == OrderStatus.CANCELLED and previous in (
                OrderStatus.PENDING, OrderStatus.CONFIRMED
            ):
                sync_stock_for_order(self, release_all=True)

        # Closing an order frees its table (unless another open order uses it)
        if new_status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
            self.release_table_if_unused()
        return True

    def release_table_if_unused(self):
        table = self.table
        if table is None:
            return
        still_open = Order.objects.filter(table=table).exclude(
            status__in=[OrderStatus.COMPLETED, OrderStatus.CANCELLED]
        ).exclude(pk=self.pk).exists()
        if not still_open and table.status == TableStatus.OCCUPIED:
            table.status = TableStatus.AVAILABLE
            table.save(update_fields=["status", "updated_at"])

    def _set_status_timestamp(self, status):
        """Set timestamp for status change"""
        timestamp_mapping = {
            OrderStatus.CONFIRMED: "confirmed_at",
            OrderStatus.PREPARING: "preparing_at",
            OrderStatus.READY: "ready_at",
            OrderStatus.COMPLETED: "completed_at",
            OrderStatus.CANCELLED: "cancelled_at",
        }
        fields = []
        field = timestamp_mapping.get(status)
        if field:
            fields.append(field)
        if status == OrderStatus.OUT_FOR_DELIVERY:
            fields.append("dispatched_at")
        if status == OrderStatus.COMPLETED and self.order_type == OrderType.DELIVERY:
            fields.append("delivered_at")
        now = timezone.now()
        for f in fields:
            setattr(self, f, now)
        return fields

    def calculate_totals(self):
        """
        Calculate order totals from items
        
        Fixed: Decimal multiplication with Decimal (not float)
        """
        items = self.items.filter(is_deleted=False)
        subtotal = sum((item.total_price for item in items), Decimal('0.00'))

        cents = Decimal('0.01')
        hundred = Decimal('100')
        tax_rate = Decimal(self.location.tax_rate) / hundred
        service_rate = Decimal(self.location.service_charge_rate) / hundred
        self.subtotal = subtotal.quantize(cents)
        self.tax = (subtotal * tax_rate).quantize(cents)
        self.service_charge = (subtotal * service_rate).quantize(cents)
        gross = self.subtotal + self.tax + self.service_charge
        # A discount can never push the bill below zero
        discount = min(self.discount or Decimal('0.00'), gross)
        self.total_amount = (gross - discount).quantize(cents)
        self.save(update_fields=['subtotal', 'tax', 'service_charge', 'total_amount', 'updated_at'])

        from apps.cash.services import sync_payment_status
        sync_payment_status(self)   # total changed -> paid / partially paid may change

        # Items changed on an order that already used stock -> move the difference
        if self.stock_deducted:
            from apps.inventory.services import sync_stock_for_order
            sync_stock_for_order(self)
 