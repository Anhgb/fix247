"""
Commission & Debt Ledger Service – Fix 24/7.
BR-01, BR-09, FR-PAY-05, FR-TECH-04.
Technician debt tracking, weekly settlement, blocking rule (>500k VND or overdue 7 days).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TechnicianProfile

DEBT_LIMIT_VND = 500_000
OVERDUE_DAYS_LIMIT = 7


def is_technician_blocked_by_debt(profile: TechnicianProfile, now: datetime | None = None) -> tuple[bool, str | None]:
    """
    BR-09: Technician debt blocking rule:
    - Block if debt_amount > 500,000 VND
    - Block if debt is overdue by more than 7 days
    Returns (is_blocked, reason)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    debt = profile.debt_amount or 0
    if debt > DEBT_LIMIT_VND:
        return True, f"Công nợ nền tảng ({debt:,.0f}đ) vượt quá giới hạn 500.000đ (BR-09)"

    if profile.debt_overdue_at and debt > 0:
        overdue_limit = profile.debt_overdue_at + timedelta(days=OVERDUE_DAYS_LIMIT)
        if now > overdue_limit:
            return True, f"Công nợ nền tảng ({debt:,.0f}đ) đã quá hạn thanh toán 7 ngày (BR-09)"

    return False, None


async def record_order_commission(
    db: AsyncSession,
    profile: TechnicianProfile,
    earned_amount: int,
    commission_amount: int,
) -> None:
    """
    FR-PAY-05: Record earnings, platform commission, and update technician debt.
    """
    profile.total_earned = (profile.total_earned or 0) + earned_amount
    profile.total_commission = (profile.total_commission or 0) + commission_amount
    profile.debt_amount = (profile.debt_amount or 0) + commission_amount

    # If first time incurring debt, start overdue clock
    if profile.debt_amount > 0 and not profile.debt_overdue_at:
        profile.debt_overdue_at = datetime.now(timezone.utc)

    await db.flush()


async def settle_technician_debt(
    db: AsyncSession,
    profile: TechnicianProfile,
    amount_paid: int,
) -> int:
    """
    Settle technician's commission debt.
    Returns remaining debt.
    """
    current_debt = profile.debt_amount or 0
    new_debt = max(0, current_debt - amount_paid)
    profile.debt_amount = new_debt

    if new_debt == 0:
        profile.debt_overdue_at = None

    await db.flush()
    return new_debt

