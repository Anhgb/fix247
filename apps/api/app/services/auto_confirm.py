"""
Auto-confirm Service – Fix 24/7.
FR-PAY-04, BR-08, AT-05, FR-HEALTH-02.
Auto-confirm orders after 24 hours in AWAITING_CONFIRM without customer dispute.
Generates MaintenanceLog and records technician commission.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ItemType,
    MaintenanceLog,
    Order,
    OrderStatus,
    TechnicianProfile,
    _uuid_default,
)
from app.services.commission import record_order_commission
from app.services.invoice import calculate_invoice_breakdown
from app.services.order_state_machine import transition_order


async def create_maintenance_log_for_order(db: AsyncSession, order: Order) -> MaintenanceLog | None:
    """FR-HEALTH-02: Auto-create maintenance log from completed order."""
    if not order.asset_id:
        return None

    items = order.items or []
    parts_replaced = [
        {"name": it.name, "qty": it.qty, "unit_price": it.unit_price}
        for it in items
        if it.item_type == ItemType.part
    ]
    labor_cost = sum(it.qty * it.unit_price for it in items if it.item_type == ItemType.labor)
    parts_cost = sum(it.qty * it.unit_price for it in items if it.item_type == ItemType.part)

    log = MaintenanceLog(
        id=_uuid_default(),
        asset_id=order.asset_id,
        order_id=order.id,
        summary=f"Sửa chữa hoàn tất theo đơn hàng #{str(order.id)[:8]}",
        parts_replaced=parts_replaced,
        labor_cost=labor_cost,
        parts_cost=parts_cost,
        total_cost=order.total or (labor_cost + parts_cost),
        technician_id=order.technician_id,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(log)
    await db.flush()
    return log


async def auto_confirm_expired_orders(
    db: AsyncSession,
    cutoff_hours: int = 24,
    now: datetime | None = None,
) -> list[str]:
    """
    FR-PAY-04, BR-08, AT-05:
    Find all orders in AWAITING_CONFIRM that have exceeded cutoff_hours (default 24h).
    Transition to COMPLETED, create maintenance log, and update commission ledger.
    Returns list of confirmed order IDs.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    cutoff_time = now - timedelta(hours=cutoff_hours)

    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.events))
        .where(
            Order.status == OrderStatus.AWAITING_CONFIRM,
            Order.updated_at <= cutoff_time,
        )
    )

    result = await db.execute(stmt)
    orders = result.scalars().all()
    confirmed_ids = []

    for order in orders:
        # Transition state machine
        await transition_order(
            db,
            order,
            OrderStatus.COMPLETED,
            note="Tự động xác nhận sau 24 giờ không có khiếu nại (BR-08 / AT-05)",
        )
        order.completed_at = now

        # Create health log
        await create_maintenance_log_for_order(db, order)

        # Update commission ledger
        breakdown = calculate_invoice_breakdown(order, order.items or [])
        order.commission_amount = breakdown["commission_amount"]
        order.commission_rate = breakdown["commission_rate"]

        if order.technician_id:
            tp_stmt = select(TechnicianProfile).where(
                TechnicianProfile.user_id == order.technician_id
            )
            tp_res = await db.execute(tp_stmt)
            profile = tp_res.scalar_one_or_none()
            if profile:
                await record_order_commission(
                    db,
                    profile,
                    earned_amount=order.total or 0,
                    commission_amount=breakdown["commission_amount"],
                )

        confirmed_ids.append(str(order.id))

    await db.commit()
    return confirmed_ids

