"""
Warranty Claims Router – Fix 24/7.
FR-PAY-06, SRS §6.
7 days (motorbike) / 30 days (home appliance) warranty validity window.
Order transitions from COMPLETED to WARRANTY.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_customer
from app.models import (
    Notification,
    NotificationChannel,
    Order,
    OrderStatus,
    User,
    WarrantyClaim,
    WarrantyStatus,
    _uuid_default,
)
from app.schemas.warranty import WarrantyClaimCreate, WarrantyClaimResponse
from app.services.invoice import calculate_invoice_breakdown
from app.services.order_state_machine import transition_order

router = APIRouter(tags=["warranty"])


@router.post("/orders/{order_id}/warranty", response_model=WarrantyClaimResponse)
async def submit_warranty_claim(
    order_id: UUID,
    payload: WarrantyClaimCreate,
    current_user: User = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-PAY-06, SRS §6:
    Submit warranty claim for a completed order.
    Validates eligibility window: 7 days for motorbike, 30 days for home appliance.
    Transitions order to WARRANTY and notifies technician.
    """
    stmt = (
        select(Order)
        .options(selectinload(Order.asset), selectinload(Order.items))
        .where(Order.id == str(order_id))
    )
    order = (await db.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Bạn không phải chủ đơn hàng này."}},
        )

    # Order must be COMPLETED
    if order.status != OrderStatus.COMPLETED and order.status != OrderStatus.WARRANTY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_STATUS_FOR_WARRANTY",
                    "message": "Chỉ có thể yêu cầu bảo hành cho đơn hàng đã hoàn tất (COMPLETED).",
                }
            },
        )

    # Calculate warranty days (7 for motorbike, 30 for home appliance)
    breakdown = calculate_invoice_breakdown(order, order.items or [])
    warranty_days = breakdown["warranty_days"]

    now = datetime.now(timezone.utc)
    completed_at = order.completed_at or order.updated_at
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)

    if now > completed_at + timedelta(days=warranty_days):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "WARRANTY_EXPIRED",
                    "message": f"Thời hạn bảo hành ({warranty_days} ngày) đã hết hạn.",
                }
            },
        )

    # Transition order to WARRANTY if currently COMPLETED
    if order.status == OrderStatus.COMPLETED:
        await transition_order(
            db,
            order,
            OrderStatus.WARRANTY,
            actor_id=current_user.id,
            note=f"Yêu cầu bảo hành: {payload.reason}",
        )

    claim = WarrantyClaim(
        id=_uuid_default(),
        order_id=str(order_id),
        opened_by_id=current_user.id,
        reason=payload.reason,
        media_urls=payload.media_urls,
        status=WarrantyStatus.open,
    )
    db.add(claim)

    # Notify technician if assigned
    if order.technician_id:
        notif = Notification(
            id=_uuid_default(),
            user_id=order.technician_id,
            notification_type="warranty_claim",
            title="Yêu cầu bảo hành mới",
            body=f"Khách hàng đã gửi yêu cầu bảo hành cho đơn #{str(order.id)[:8]}: {payload.reason}",
            channel=NotificationChannel.in_app,
        )
        db.add(notif)

    await db.commit()
    await db.refresh(claim)

    return claim


@router.get("/orders/{order_id}/warranty", response_model=list[WarrantyClaimResponse])
async def list_order_warranty_claims(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List warranty claims for an order."""
    stmt = (
        select(WarrantyClaim)
        .where(WarrantyClaim.order_id == str(order_id))
        .order_by(WarrantyClaim.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()

