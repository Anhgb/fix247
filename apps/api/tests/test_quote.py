"""
Unit tests for Quote Threshold (BR-05), Survey Fee (BR-07), and Night Surcharge (BR-04).
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.models import Order, OrderStatus
from app.services.booking_rules import (
    apply_survey_fee,
    check_quote_threshold,
    get_night_surcharge,
)

_TZ_VN = ZoneInfo("Asia/Ho_Chi_Minh")


# ── BR-05 Quote Threshold Tests ───────────────────────────────────────────────

def test_quote_under_or_equal_max():
    """Quotes below or equal to price_max do not trigger warning."""
    assert check_quote_threshold(quote_total=100000, price_max=100000) is False
    assert check_quote_threshold(quote_total=80000, price_max=100000) is False


def test_quote_exactly_20_percent():
    """Quote at exactly +20% does NOT trigger threshold (strict inequality)."""
    assert check_quote_threshold(quote_total=120000, price_max=100000) is False


def test_quote_over_20_percent():
    """Quote strictly >20% above price_max triggers warning."""
    assert check_quote_threshold(quote_total=120001, price_max=100000) is True
    assert check_quote_threshold(quote_total=150000, price_max=100000) is True


def test_quote_zero_or_negative_price_max():
    """Handles edge cases gracefully."""
    assert check_quote_threshold(quote_total=100000, price_max=0) is False
    assert check_quote_threshold(quote_total=100000, price_max=-50000) is False


# ── BR-07 Survey Fee Tests ────────────────────────────────────────────────────

def test_apply_survey_fee_default():
    """Default survey fee is 30,000 VND."""
    order = Order()
    fee = apply_survey_fee(order, {})
    assert fee == 30000


def test_apply_survey_fee_configured():
    """Survey fee can be configured by platform settings."""
    order = Order()
    fee = apply_survey_fee(order, {"survey_fee": 50000})
    assert fee == 50000


# ── BR-04 Night Surcharge Tests ───────────────────────────────────────────────

def test_night_surcharge_daytime():
    """Orders between 05:00 and 21:59 local have 0 surcharge."""
    # 14:00 VN time (UTC+7) = 07:00 UTC
    dt_day = datetime(2026, 10, 27, 7, 0, 0, tzinfo=timezone.utc)
    surcharge = get_night_surcharge(dt_day, {"night_surcharge": 15000})
    assert surcharge == 0


def test_night_surcharge_night():
    """Orders between 22:00 and 04:59 local get night surcharge."""
    # 23:00 VN time = 16:00 UTC
    dt_night = datetime(2026, 10, 27, 16, 0, 0, tzinfo=timezone.utc)
    surcharge = get_night_surcharge(dt_night, {"night_surcharge": 20000})
    assert surcharge == 20000

    # 02:00 VN time = 19:00 UTC previous day
    dt_late_night = datetime(2026, 10, 27, 19, 0, 0, tzinfo=timezone.utc)
    surcharge2 = get_night_surcharge(dt_late_night, {})
    assert surcharge2 == 15000  # Default 15000

