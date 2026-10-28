"""
Invoice calculation service – Fix 24/7.
FR-PAY-01, BR-01, BR-02, FR-PAY-06.
Exact integer VND arithmetic: labor + parts + night_surcharge = total.
Commission calculated strictly on (labor + parts); night surcharge is 100% to technician (BR-01).
"""
from __future__ import annotations

from app.models import ItemType, Order, OrderItem, ServiceGroup


def calculate_invoice_breakdown(
    order: Order,
    items: list[OrderItem],
    commission_rate: float = 0.10,
) -> dict:
    """
    FR-PAY-01, BR-01:
    - labor_subtotal = Σ (qty * unit_price) for labor items
    - parts_subtotal = Σ (qty * unit_price) for part items
    - night_surcharge = order.night_surcharge (0 if daytime)
    - total = labor_subtotal + parts_subtotal + night_surcharge
    - commission_amount = round((labor_subtotal + parts_subtotal) * commission_rate)
    """
    labor_subtotal = sum(
        it.qty * it.unit_price for it in items if it.item_type == ItemType.labor
    )
    parts_subtotal = sum(
        it.qty * it.unit_price for it in items if it.item_type == ItemType.part
    )
    night_surcharge = order.night_surcharge or 0

    # Total must equal the sum of its components
    total = labor_subtotal + parts_subtotal + night_surcharge

    # BR-01: commission is only on labor + parts, never surcharge
    commissionable_base = labor_subtotal + parts_subtotal
    commission_amount = int(round(commissionable_base * commission_rate))

    # FR-PAY-06: 7 days for motorbike, 30 days for home appliance
    warranty_days = 7
    if hasattr(order, "asset") and order.asset:
        if order.asset.asset_type.value == "appliance":
            warranty_days = 30
    elif hasattr(order, "mode") and order.mode.value == "scheduled":
        # Scheduled bookings are home repairs
        warranty_days = 30

    return {
        "labor_subtotal": labor_subtotal,
        "parts_subtotal": parts_subtotal,
        "night_surcharge": night_surcharge,
        "total": total,
        "commission_rate": commission_rate,
        "commission_amount": commission_amount,
        "warranty_days": warranty_days,
    }

