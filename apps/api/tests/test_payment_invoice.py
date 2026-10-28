"""
Unit tests for Invoice Calculation and Commission Arithmetic.
FR-PAY-01, BR-01, BR-02, FR-PAY-06.
Exact integer VND arithmetic: labor + parts + surcharge = total.
Commission is calculated strictly on (labor + parts), excluding night surcharge.
"""
from unittest.mock import MagicMock

from app.models import Asset, AssetType, ItemType, Order, OrderItem, OrderMode


def test_invoice_arithmetic_exact_zero_error():
    """FR-PAY-01: Total = labor_subtotal + parts_subtotal + night_surcharge with 0 error."""
    from app.services.invoice import calculate_invoice_breakdown

    order = MagicMock(spec=Order)
    order.night_surcharge = 15000
    order.asset = None
    order.mode = OrderMode.emergency

    items = [
        OrderItem(item_type=ItemType.labor, qty=1, unit_price=80000, name="Công sửa"),
        OrderItem(item_type=ItemType.labor, qty=2, unit_price=30000, name="Công kiểm tra"),
        OrderItem(item_type=ItemType.part, qty=1, unit_price=120000, name="Bugi NGK"),
        OrderItem(item_type=ItemType.part, qty=4, unit_price=15000, name="Ốc vít"),
    ]

    breakdown = calculate_invoice_breakdown(order, items, commission_rate=0.10)

    expected_labor = 80000 + 60000  # 140,000
    expected_parts = 120000 + 60000  # 180,000
    expected_surcharge = 15000
    expected_total = expected_labor + expected_parts + expected_surcharge  # 335,000

    assert breakdown["labor_subtotal"] == expected_labor
    assert breakdown["parts_subtotal"] == expected_parts
    assert breakdown["night_surcharge"] == expected_surcharge
    assert breakdown["total"] == expected_total


def test_commission_excludes_night_surcharge():
    """BR-01: Commission is strictly on labor + parts; night surcharge is 0% commission."""
    from app.services.invoice import calculate_invoice_breakdown

    order = MagicMock(spec=Order)
    order.night_surcharge = 20000
    order.asset = None
    order.mode = OrderMode.emergency

    items = [
        OrderItem(item_type=ItemType.labor, qty=1, unit_price=100000, name="Công sửa"),
        OrderItem(item_type=ItemType.part, qty=1, unit_price=200000, name="Linh kiện"),
    ]

    # Commissionable base = 300,000. Total = 320,000.
    # At 10%: commission = 30,000 (NOT 32,000)
    breakdown = calculate_invoice_breakdown(order, items, commission_rate=0.10)
    assert breakdown["commission_amount"] == 30000

    # At 12%: commission = 36,000
    breakdown_12 = calculate_invoice_breakdown(order, items, commission_rate=0.12)
    assert breakdown_12["commission_amount"] == 36000


def test_warranty_days_by_category():
    """FR-PAY-06: 7 days for motorbike vs 30 days for home appliance."""
    from app.services.invoice import calculate_invoice_breakdown

    # Motorbike emergency order
    order_mb = MagicMock(spec=Order)
    order_mb.night_surcharge = 0
    order_mb.asset = MagicMock(spec=Asset)
    order_mb.asset.asset_type = AssetType.vehicle
    order_mb.mode = OrderMode.emergency

    b_mb = calculate_invoice_breakdown(order_mb, [])
    assert b_mb["warranty_days"] == 7

    # Home appliance order
    order_home = MagicMock(spec=Order)
    order_home.night_surcharge = 0
    order_home.asset = MagicMock(spec=Asset)
    order_home.asset.asset_type = AssetType.appliance
    order_home.mode = OrderMode.scheduled

    b_home = calculate_invoice_breakdown(order_home, [])
    assert b_home["warranty_days"] == 30

