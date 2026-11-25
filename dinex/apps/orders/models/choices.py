from django.db import models


class OrderType(models.TextChoices):
    """Order Type Choices"""
    DINE_IN = "DINE_IN", "Dine In"
    TAKEAWAY = "TAKEAWAY", "Takeaway"
    DELIVERY = "DELIVERY", "Delivery"


class OrderStatus(models.TextChoices):
    """Order Status Choices"""
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    PREPARING = "PREPARING", "Preparing"
    READY = "READY", "Ready"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentStatus(models.TextChoices):
    """Payment Status Choices"""
    PENDING = "PENDING", "Pending"
    PARTIAL = "PARTIAL", "Partially paid"
    PAID = "PAID", "Paid"
    REFUNDED = "REFUNDED", "Refunded"
    FAILED = "FAILED", "Failed"


class PaymentMethod(models.TextChoices):
    """Payment Method Choices"""
    CASH = "CASH", "Cash"
    CARD = "CARD", "Card"
    ONLINE = "ONLINE", "Online"
    COD = "COD", "Cash on Delivery"


class TableStatus(models.TextChoices):
    """Table Status Choices"""
    AVAILABLE = "AVAILABLE", "Available"
    OCCUPIED = "OCCUPIED", "Occupied"
    RESERVED = "RESERVED", "Reserved"
    CLEANING = "CLEANING", "Cleaning"


class TableShape(models.TextChoices):
    """How a table (and its chairs) is drawn on the floor plan"""
    SQUARE = "SQUARE", "Square (seats on 4 sides)"
    ROUND = "ROUND", "Round"
    LONG = "LONG", "Long (seats on 2 sides)"
    WALL = "WALL", "Against a wall (seats on 3 sides)"
