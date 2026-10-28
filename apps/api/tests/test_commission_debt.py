"""
Unit tests for Commission & Debt Ledger Rules (BR-09, FR-TECH-04).
- Block technician from new jobs when debt > 500,000 VND
- Block technician when debt overdue > 7 days
- Debt settlement flow
"""
from datetime import datetime, timedelta, timezone

from app.models import TechnicianProfile
from app.services.commission import is_technician_blocked_by_debt, settle_technician_debt


def test_technician_debt_below_limit():
    """Technician with <= 500k debt and not overdue is not blocked."""
    profile = TechnicianProfile(
        debt_amount=300000,
        debt_overdue_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    is_blocked, reason = is_technician_blocked_by_debt(profile)
    assert is_blocked is False
    assert reason is None


def test_technician_debt_exceeds_500k_blocked():
    """BR-09: Debt > 500,000 VND blocks technician immediately."""
    profile = TechnicianProfile(
        debt_amount=500001,
        debt_overdue_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    is_blocked, reason = is_technician_blocked_by_debt(profile)
    assert is_blocked is True
    assert "500.000đ" in reason


def test_technician_debt_overdue_7_days_blocked():
    """BR-09: Debt overdue > 7 days blocks technician even if debt <= 500k."""
    profile = TechnicianProfile(
        debt_amount=150000,
        debt_overdue_at=datetime.now(timezone.utc) - timedelta(days=8),
    )
    is_blocked, reason = is_technician_blocked_by_debt(profile)
    assert is_blocked is True
    assert "7 ngày" in reason


def test_technician_debt_zero_not_blocked():
    """Technician with 0 debt is never blocked."""
    profile = TechnicianProfile(
        debt_amount=0,
        debt_overdue_at=datetime.now(timezone.utc) - timedelta(days=30),
    )
    is_blocked, reason = is_technician_blocked_by_debt(profile)
    assert is_blocked is False

