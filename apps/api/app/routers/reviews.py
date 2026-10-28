"""
Reviews & Disputes Router – Fix 24/7.
FR-RATE-01..03, FR-TECH-05, ADM-3.
Customer & technician reviews, time-weighted ratings, auto-suspension, dispute handling.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_customer, require_technician
from app.models import (
    Dispute,
    DisputeStatus,
    Order,
    OrderStatus,
    Review,
    User,
    UserRole,
    _uuid_default,
)
from app.schemas.reviews import (
    DisputeCreate,
    DisputeResponse,
    ReviewCreate,
    ReviewResponse,
)
from app.services.order_state_machine import transition_order
from app.services.review_service import update_technician_rating_stats

router = APIRouter(tags=["reviews"])


# ── Customer Review (FR-RATE-01) ───────────────────────────────────────────────

@router.post("/orders/{order_id}/review", response_model=ReviewResponse)
async def submit_customer_review(
    order_id: UUID,
    payload: ReviewCreate,
    current_user: User = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-RATE-01, FR-RATE-03, FR-TECH-05:
    Customer reviews technician after order is COMPLETED.
    Only 1 review per side per order.
    Updates time-weighted rating and checks auto-suspension rule.
    """
    stmt = select(Order).where(Order.id == str(order_id))
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

    # FR-RATE-01: Only COMPLETED orders can be reviewed
    if order.status != OrderStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "ORDER_NOT_COMPLETED",
                    "message": "Chỉ có thể đánh giá khi đơn hàng đã hoàn thành (COMPLETED).",
                }
            },
        )

    if not order.technician_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "NO_TECHNICIAN", "message": "Đơn hàng chưa có thợ được phân công."}},
        )

    # Check for duplicate review
    existing_stmt = select(Review).where(
        Review.order_id == str(order_id),
        Review.from_user_id == current_user.id,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "REVIEW_ALREADY_EXISTS", "message": "Bạn đã gửi đánh giá cho đơn hàng này."}},
        )

    review = Review(
        id=_uuid_default(),
        order_id=str(order_id),
        from_user_id=current_user.id,
        to_user_id=order.technician_id,
        from_role="customer",
        stars=payload.stars,
        tags=payload.tags,
        comment=payload.comment,
    )
    db.add(review)
    await db.commit()

    # FR-RATE-03 & FR-TECH-05: Update rating stats & check auto-suspension
    await update_technician_rating_stats(db, order.technician_id)
    await db.commit()

    return review


# ── Technician Reviews Customer (FR-RATE-02) ───────────────────────────────────

@router.post("/orders/{order_id}/review-customer", response_model=ReviewResponse)
async def submit_technician_review(
    order_id: UUID,
    payload: ReviewCreate,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-RATE-02: Technician rates customer privately to detect order-bombing.
    """
    stmt = select(Order).where(Order.id == str(order_id))
    order = (await db.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    if order.technician_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Bạn không phải thợ của đơn hàng này."}},
        )

    existing_stmt = select(Review).where(
        Review.order_id == str(order_id),
        Review.from_user_id == current_user.id,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "REVIEW_ALREADY_EXISTS", "message": "Bạn đã gửi đánh giá cho đơn hàng này."}},
        )

    review = Review(
        id=_uuid_default(),
        order_id=str(order_id),
        from_user_id=current_user.id,
        to_user_id=order.customer_id,
        from_role="technician",
        stars=payload.stars,
        tags=payload.tags,
        comment=payload.comment,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    return review


# ── Disputes (ADM-3) ───────────────────────────────────────────────────────────

@router.post("/orders/{order_id}/dispute", response_model=DisputeResponse)
async def open_order_dispute(
    order_id: UUID,
    payload: DisputeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ADM-3, SRS §6:
    Customer opens dispute on order. Transitions order to DISPUTED.
    """
    stmt = select(Order).where(Order.id == str(order_id))
    order = (await db.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    if order.customer_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Chỉ khách hàng hoặc admin mới có thể mở khiếu nại."}},
        )

    # Transition order to DISPUTED
    await transition_order(
        db,
        order,
        OrderStatus.DISPUTED,
        actor_id=current_user.id,
        note=f"Khiếu nại: {payload.reason}",
    )

    dispute = Dispute(
        id=_uuid_default(),
        order_id=str(order_id),
        opened_by_id=current_user.id,
        reason=payload.reason,
        status=DisputeStatus.open,
    )
    db.add(dispute)
    await db.commit()
    await db.refresh(dispute)

    return dispute

