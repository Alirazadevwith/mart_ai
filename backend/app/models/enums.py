"""Domain enumerations shared by models, schemas and services.

These are stored as native PostgreSQL enum types. Adding a member needs an
Alembic migration, which is deliberate: the order and payment state machines
are business rules, not free-text columns.
"""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    PLATFORM_ADMIN = "platform_admin"  # runs the SaaS itself; not tenant-scoped
    MERCHANT_OWNER = "merchant_owner"  # owns one mart
    STAFF = "staff"  # packs orders for one mart
    CUSTOMER = "customer"  # shops across any mart


class ProductUnit(StrEnum):
    """How a product is sold, which decides whether quantities are fractional."""

    KG = "kg"
    GRAM = "gram"
    LITRE = "litre"
    MILLILITRE = "millilitre"
    PIECE = "piece"
    PACK = "pack"
    DOZEN = "dozen"
    BAG = "bag"

    @property
    def allows_fractional_quantity(self) -> bool:
        return self in {
            ProductUnit.KG,
            ProductUnit.GRAM,
            ProductUnit.LITRE,
            ProductUnit.MILLILITRE,
        }


class StockStatus(StrEnum):
    """Derived from quantity vs. threshold; never stored."""

    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"


class InventoryMovementReason(StrEnum):
    """Why stock changed. Every movement is appended, never updated."""

    INITIAL = "initial"
    RESTOCK = "restock"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    ORDER_RESERVED = "order_reserved"
    ORDER_RELEASED = "order_released"
    ORDER_COLLECTED = "order_collected"
    DAMAGE = "damage"
    EXPIRY = "expiry"
