"""
Unit tests for Cancellation Rules (BR-06).
- Cancel before technician has started (ON_THE_WAY not yet reached): 0 VND
- Cancel after ON_THE_WAY: travel fee applies
"""
from unittest.mock import MagicMock

from app.models import Order, OrderStatus
from app.services.booking_rules import get_cancellation_fee


def test_cancellation_fee_before_departure():
    """Cancelling before tech starts on the way costs 0 VND."""
    order = MagicMock(spec=Order)
    for st in [OrderStatus.CREATED, OrderStatus.SEARCHING, OrderStatus.SCHEDULED, OrderStatus.ACCEPTED]:
        order.status = st
        fee = get_cancellation_fee(order, {"travel_fee": 20000})
        assert fee == 0, f"Expected 0 fee for status {st}"


def test_cancellation_fee_after_departure():
    """Cancelling after tech is ON_THE_WAY or SURVEYING incurs travel_fee."""
    order = MagicMock(spec=Order)
    for st in [OrderStatus.ON_THE_WAY, OrderStatus.SURVEYING, OrderStatus.QUOTE_PENDING]:
        order.status = st
        fee = get_cancellation_fee(order, {"travel_fee": 25000})
        assert fee == 25000, f"Expected 25000 fee for status {st}"


def test_cancellation_fee_custom_config():
    """Custom travel_fee in platform config is respected."""
    order = MagicMock(spec=Order)
    order.status = OrderStatus.ON_THE_WAY
    fee = get_cancellation_fee(order, {"travel_fee": 50000})
    assert fee == 50000

