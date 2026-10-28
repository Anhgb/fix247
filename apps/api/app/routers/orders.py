"""
Order router – Fix 24/7.
FR-BOOK, FR-TRACK, UC-03, UC-04, UC-05, UC-06.
State machine transitions through app.services.order_state_machine.
Error responses formatted per SRS §7.4.
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_customer, require_technician
from app.core.redis import get_redis
from app.models import (
    ChatMessage,
    Diagnosis,
    ItemType,
    Order,
    OrderEvent,
    OrderItem,
    OrderMode,
    OrderStatus,
    QRLocation,
    User,
    UserRole,
    _uuid_default,
)
from app.schemas.orders import (
    CancelOrder,
    ChatMessage as ChatMessageIn,
    ChatMessageResponse,
    OrderCreate,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdate,
    QuoteRespond,
    QuoteSubmit,
)
from app.schemas.warranty import TechCompleteOrderRequest
from app.services.booking_rules import (
    apply_survey_fee,
    check_quote_threshold,
    get_cancellation_fee,
    get_night_surcharge,
)
from app.services.dispatch_worker import start_dispatch
from app.services.order_state_machine import InvalidTransitionError, transition_order
from app.services.platform_config import get_config

router = APIRouter(prefix="/orders", tags=["orders"])
_TZ_VN = ZoneInfo("Asia/Ho_Chi_Minh")
PHONE_REGEX = re.compile(r"(0[3|5|7|8|9]\d{8}|\b\d{10,11}\b)")


def mask_phone_number(text: str) -> tuple[str, bool]:
    """FR-TRACK-03: Hide phone numbers in chat text."""
    masked, count = PHONE_REGEX.subn("***", text)
    return masked, count > 0


# ── Create Order ───────────────────────────────────────────────────────────────

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    UC-03 / UC-04: Create a new order (emergency or scheduled).
    FR-BOOK-03, FR-BOOK-04, FR-BOOK-05, BR-04.
    """
    now_utc = datetime.now(timezone.utc)
    now_vn = now_utc.astimezone(_TZ_VN)

    # FR-BOOK-05: Check open emergency order
    if payload.mode == OrderMode.emergency:
        open_statuses = [
            OrderStatus.CREATED,
            OrderStatus.SEARCHING,
            OrderStatus.ACCEPTED,
            OrderStatus.ON_THE_WAY,
            OrderStatus.SURVEYING,
            OrderStatus.QUOTE_PENDING,
            OrderStatus.IN_REPAIR,
            OrderStatus.AWAITING_CONFIRM,
        ]
        stmt = select(Order).where(
            Order.customer_id == current_user.id,
            Order.mode == OrderMode.emergency,
            Order.status.in_(open_statuses),
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "OPEN_ORDER_EXISTS",
                        "message": "Bạn đang có một đơn cứu hộ khẩn cấp đang xử lý. Vui lòng hoàn thành hoặc hủy đơn trước.",
                    }
                },
            )

    # FR-BOOK-03: Validate scheduled order rules
    scheduled_at_val = payload.scheduled_at
    if payload.mode == OrderMode.scheduled:
        if not scheduled_at_val:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": {"code": "MISSING_SCHEDULED_AT", "message": "Vui lòng chọn thời gian hẹn."}},
            )
        sched_vn = scheduled_at_val.astimezone(_TZ_VN)
        # Must be >= 2 hours from now
        if sched_vn < now_vn + timedelta(hours=2):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_SCHEDULE_TIME",
                        "message": "Thời gian đặt lịch phải sau thời điểm hiện tại ít nhất 2 giờ.",
                    }
                },
            )
        # Must be within 7 days
        if sched_vn > now_vn + timedelta(days=7):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "SCHEDULE_TOO_FAR",
                        "message": "Chỉ có thể đặt lịch hẹn trong vòng 7 ngày tới.",
                    }
                },
            )
        # Must be between 07:00 and 21:00
        if not (7 <= sched_vn.hour < 21):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "OUTSIDE_WORKING_HOURS",
                        "message": "Thời gian hẹn phải trong khung giờ làm việc: 07:00 - 21:00.",
                    }
                },
            )

    # BR-04: Calculate night surcharge for emergency orders
    night_surcharge = 0
    if payload.mode == OrderMode.emergency:
        night_surcharge = get_night_surcharge(now_utc, config={"night_surcharge": 15000})

    # Estimate min/max from diagnosis if available
    est_min = None
    est_max = None
    if payload.diagnosis_id:
        d_res = await db.execute(select(Diagnosis).where(Diagnosis.id == str(payload.diagnosis_id)))
        diag = d_res.scalar_one_or_none()
        if diag and diag.ai_output and "candidates" in diag.ai_output:
            cands = diag.ai_output.get("candidates", [])
            if cands and isinstance(cands, list) and len(cands) > 0:
                top = cands[0]
                price_range = top.get("price_range")
                if price_range:
                    est_min = price_range.get("min")
                    est_max = price_range.get("max")

    order_id = _uuid_default()
    resolved_asset_id = (
        str(payload.asset_id)
        if payload.asset_id
        else (str(diag.asset_id) if diag and diag.asset_id else None)
    )

    # Resolve QR Location context (FR-QR-01, AT-08)
    resolved_qr_id = None
    if payload.qr_location_id:
        resolved_qr_id = str(payload.qr_location_id)
        q_loc = await db.get(QRLocation, resolved_qr_id)
        if q_loc:
            q_loc.order_count += 1
    elif payload.qr_code:
        q_res = await db.execute(select(QRLocation).where(QRLocation.code == payload.qr_code.strip()))
        q_loc = q_res.scalar_one_or_none()
        if q_loc:
            resolved_qr_id = str(q_loc.id)
            q_loc.order_count += 1
    elif diag and diag.qr_location_id:
        resolved_qr_id = str(diag.qr_location_id)
        q_loc = await db.get(QRLocation, resolved_qr_id)
        if q_loc:
            q_loc.order_count += 1

    new_order = Order(
        id=order_id,
        customer_id=current_user.id,
        diagnosis_id=str(payload.diagnosis_id) if payload.diagnosis_id else None,
        asset_id=resolved_asset_id,
        qr_location_id=resolved_qr_id,
        mode=payload.mode,
        status=OrderStatus.CREATED,
        address=payload.location.address,
        lat=payload.location.lat,
        lng=payload.location.lng,
        scheduled_at=payload.scheduled_at,
        est_min=est_min,
        est_max=est_max,
        night_surcharge=night_surcharge,
        customer_note=payload.note,
    )
    db.add(new_order)

    # Write initial creation event
    event = OrderEvent(
        id=_uuid_default(),
        order_id=order_id,
        from_status=None,
        to_status=OrderStatus.CREATED,
        actor_id=current_user.id,
        note="Khách hàng tạo đơn hàng",
    )
    db.add(event)
    await db.commit()

    # Re-query with items & events loaded
    res = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.events))
        .where(Order.id == order_id)
    )
    saved_order = res.scalar_one()

    # If emergency, kick off dispatch worker in background
    if payload.mode == OrderMode.emergency:
        async def run_dispatch_task(o_id: str):
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                o_stmt = await session.execute(select(Order).where(Order.id == o_id))
                o = o_stmt.scalar_one_or_none()
                if o:
                    await start_dispatch(db=session, order=o)
                    await session.commit()

        background_tasks.add_task(run_dispatch_task, order_id)

    return saved_order


# ── List Orders ────────────────────────────────────────────────────────────────

@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List orders for current user.
    Customer sees their placed orders.
    Technician sees orders assigned to them.
    Admin sees all orders.
    """
    query = select(Order).options(selectinload(Order.items), selectinload(Order.events))

    if current_user.role == UserRole.customer:
        query = query.where(Order.customer_id == current_user.id)
    elif current_user.role == UserRole.technician:
        query = query.where(Order.technician_id == current_user.id)

    # Count total
    count_stmt = select(func.count(Order.id))
    if current_user.role == UserRole.customer:
        count_stmt = count_stmt.where(Order.customer_id == current_user.id)
    elif current_user.role == UserRole.technician:
        count_stmt = count_stmt.where(Order.technician_id == current_user.id)

    total_count = (await db.execute(count_stmt)).scalar() or 0

    query = query.order_by(desc(Order.created_at)).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        items=orders,
        total=total_count,
        page=page,
        size=size,
    )


# ── Get Order ──────────────────────────────────────────────────────────────────

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full details of a specific order."""
    res = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.events))
        .where(Order.id == str(order_id))
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    # Authorization check
    if current_user.role != UserRole.admin:
        if order.customer_id != current_user.id and order.technician_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Bạn không có quyền xem đơn hàng này."}},
            )

    return order


# ── Cancel Order ───────────────────────────────────────────────────────────────

@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    payload: CancelOrder,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-BOOK-06, BR-06: Cancel an order.
    Calculates cancellation fee if technician is already ON_THE_WAY.
    """
    res = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.events))
        .where(Order.id == str(order_id))
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    # Permission check
    if current_user.role != UserRole.admin and order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Chỉ khách hàng hoặc admin mới có thể hủy đơn."}},
        )

    # BR-06: Calculate cancellation fee
    travel_fee_cfg = await get_config(db, "travel_fee", default="20000")
    cancel_fee = get_cancellation_fee(order, {"travel_fee": int(travel_fee_cfg)})

    try:
        await transition_order(
            db,
            order,
            OrderStatus.CANCELLED,
            actor_id=current_user.id,
            note=f"Hủy đơn: {payload.reason}. Phí hủy: {cancel_fee:,}đ",
        )
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e)}},
        )

    order.cancel_reason = payload.reason
    order.total = cancel_fee
    await db.commit()
    await db.refresh(order)
    return order


# ── Quote Flow ─────────────────────────────────────────────────────────────────

@router.post("/{order_id}/quote", response_model=OrderResponse)
async def submit_quote(
    order_id: UUID,
    payload: QuoteSubmit,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    UC-05, BR-05, BR-10: Technician submits formal quote with line items.
    Order must be in SURVEYING status. Transitions to QUOTE_PENDING.
    Requires reason if total exceeds price_max by >20%.
    """
    res = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.events))
        .where(Order.id == str(order_id))
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    if order.technician_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Bạn không phải thợ được phân công cho đơn này."}},
        )

    # Order must be SURVEYING
    if order.status != OrderStatus.SURVEYING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "INVALID_TRANSITION",
                    "message": f"Chỉ có thể lập báo giá khi đang khảo sát (trạng thái hiện tại: {order.status.value}).",
                }
            },
        )

    # Validate items and calculate subtotal
    subtotal = 0
    new_items: list[OrderItem] = []
    for item in payload.items:
        # BR-10: part > 100k requires photo
        if item.item_type == ItemType.part and item.unit_price > 100000 and not item.photo_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "MISSING_PART_PHOTO",
                        "message": f"Linh kiện '{item.name}' có giá trên 100.000đ yêu cầu phải có ảnh đính kèm (BR-10).",
                    }
                },
            )
        line_total = item.qty * item.unit_price
        subtotal += line_total
        new_items.append(
            OrderItem(
                id=_uuid_default(),
                order_id=order.id,
                item_type=item.item_type,
                name=item.name,
                qty=item.qty,
                unit_price=item.unit_price,
                photo_url=item.photo_url,
            )
        )

    # BR-05: Check threshold against est_max
    if order.est_max and check_quote_threshold(subtotal, order.est_max):
        if not payload.quote_reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "QUOTE_EXCEEDS_THRESHOLD",
                        "message": "Báo giá vượt quá 20% mức giá tham khảo tối đa. Bắt buộc phải nhập lý do giải trình.",
                    }
                },
            )

    # Add items to database
    for it in new_items:
        db.add(it)

    order.final_quote = subtotal
    order.total = subtotal + (order.night_surcharge or 0)

    try:
        await transition_order(
            db,
            order,
            OrderStatus.QUOTE_PENDING,
            actor_id=current_user.id,
            note=f"Thợ gửi báo giá: {subtotal:,}đ. {payload.quote_reason or ''}".strip(),
        )
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e)}},
        )

    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/quote/respond", response_model=OrderResponse)
async def respond_quote(
    order_id: UUID,
    payload: QuoteRespond,
    current_user: User = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    UC-05, BR-07: Customer accepts or rejects the technician's quote.
    Accept: QUOTE_PENDING -> IN_REPAIR
    Reject: QUOTE_PENDING -> QUOTE_REJECTED -> CLOSED (applies survey fee)
    """
    res = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.events))
        .where(Order.id == str(order_id))
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Bạn không có quyền phản hồi báo giá đơn này."}},
        )

    if order.status != OrderStatus.QUOTE_PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "INVALID_TRANSITION",
                    "message": f"Đơn hàng không ở trạng thái chờ duyệt giá (hiện tại: {order.status.value}).",
                }
            },
        )

    if payload.action == "accept":
        await transition_order(
            db,
            order,
            OrderStatus.IN_REPAIR,
            actor_id=current_user.id,
            note="Khách hàng chấp nhận báo giá",
        )
    else:
        # BR-07: Reject triggers survey fee, transition QUOTE_PENDING -> QUOTE_REJECTED -> CLOSED
        survey_fee_cfg = await get_config(db, "survey_fee", default="30000")
        s_fee = apply_survey_fee(order, {"survey_fee": int(survey_fee_cfg)})

        order.survey_fee = s_fee
        order.total = s_fee + (order.night_surcharge or 0)

        await transition_order(
            db,
            order,
            OrderStatus.QUOTE_REJECTED,
            actor_id=current_user.id,
            note=f"Khách hàng từ chối báo giá. Phí khảo sát: {s_fee:,}đ",
        )
        await transition_order(
            db,
            order,
            OrderStatus.CLOSED,
            actor_id=current_user.id,
            note="Đơn hàng đóng sau khi từ chối báo giá",
        )

    await db.commit()
    await db.refresh(order)
    return order


# ── Technician Status Update ───────────────────────────────────────────────────

@router.post("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    Technician moves order through workflow:
    ACCEPTED -> ON_THE_WAY
    ON_THE_WAY -> SURVEYING
    IN_REPAIR -> AWAITING_CONFIRM
    """
    res = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.events))
        .where(Order.id == str(order_id))
    )
    order = res.scalar_one_or_none()
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

    try:
        await transition_order(
            db,
            order,
            payload.to_status,
            actor_id=current_user.id,
            note=payload.note,
        )
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e)}},
        )

    await db.commit()
    await db.refresh(order)
    return order


# ── Customer Confirm Complete ──────────────────────────────────────────────────

@router.post("/{order_id}/confirm-complete", response_model=OrderResponse)
async def confirm_complete(
    order_id: UUID,
    current_user: User = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    UC-06, FR-PAY-03, FR-HEALTH-02:
    Customer confirms repair completed and paid.
    AWAITING_CONFIRM -> COMPLETED
    Auto-generates MaintenanceLog and records technician commission.
    """
    res = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.events))
        .where(Order.id == str(order_id))
    )
    order = res.scalar_one_or_none()
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

    try:
        await transition_order(
            db,
            order,
            OrderStatus.COMPLETED,
            actor_id=current_user.id,
            note="Khách hàng xác nhận hoàn thành",
        )
        order.completed_at = datetime.now(timezone.utc)
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e)}},
        )

    # FR-HEALTH-02: Auto-create maintenance log
    from app.services.auto_confirm import create_maintenance_log_for_order
    await create_maintenance_log_for_order(db, order)

    # FR-PAY-05: Record technician commission
    from app.services.commission import record_order_commission
    from app.services.invoice import calculate_invoice_breakdown
    comm_cfg = await get_config(db, "commission_rate", default="0.10")
    breakdown = calculate_invoice_breakdown(order, order.items or [], commission_rate=float(comm_cfg))
    order.commission_amount = breakdown["commission_amount"]
    order.commission_rate = breakdown["commission_rate"]

    if order.technician_id:
        from app.models import TechnicianProfile
        tp_stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == order.technician_id)
        tp_res = await db.execute(tp_stmt)
        profile = tp_res.scalar_one_or_none()
        if profile:
            await record_order_commission(
                db,
                profile,
                earned_amount=order.total or 0,
                commission_amount=breakdown["commission_amount"],
            )

    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/tech-complete", response_model=OrderResponse)
async def technician_complete_repair(
    order_id: UUID,
    payload: Optional[TechCompleteOrderRequest] = None,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    UC-06: Technician marks repair done with after-photos.
    IN_REPAIR -> AWAITING_CONFIRM
    """
    photo_after_urls = payload.photo_after_urls if payload else []
    summary = payload.summary if payload else None
    res = await db.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.events))
        .where(Order.id == str(order_id))
    )
    order = res.scalar_one_or_none()
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

    try:
        note_msg = f"Thợ hoàn thành sửa chữa: {summary or 'Đã sửa xong'}"
        if photo_after_urls:
            note_msg += f" (Đã chụp {len(photo_after_urls)} ảnh sau sửa)"
        await transition_order(
            db,
            order,
            OrderStatus.AWAITING_CONFIRM,
            actor_id=current_user.id,
            note=note_msg,
        )
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e)}},
        )

    await db.commit()
    await db.refresh(order)
    return order


# ── Chat & Messaging ───────────────────────────────────────────────────────────

@router.post("/{order_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    order_id: UUID,
    payload: ChatMessageIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-TRACK-03: Send in-order chat message.
    Phone numbers are automatically masked with '***'.
    """
    res = await db.execute(select(Order).where(Order.id == str(order_id)))
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    # Only customer, technician, or admin can participate
    if current_user.role != UserRole.admin:
        if order.customer_id != current_user.id and order.technician_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Bạn không tham gia đơn hàng này."}},
            )

    masked_content, is_masked = mask_phone_number(payload.content)

    msg = ChatMessage(
        id=_uuid_default(),
        order_id=str(order_id),
        sender_id=current_user.id,
        sender_role=current_user.role.value,
        content=masked_content,
        media_url=payload.media_url,
        is_phone_masked=is_masked,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Publish to Redis channel order:{order_id}
    try:
        redis = await get_redis()
        import json
        chat_event = {
            "type": "chat",
            "message": {
                "id": str(msg.id),
                "order_id": str(msg.order_id),
                "sender_id": str(msg.sender_id),
                "sender_role": msg.sender_role,
                "content": msg.content,
                "media_url": msg.media_url,
                "created_at": msg.created_at.isoformat(),
            },
        }
        await redis.publish(f"order:{order_id}", json.dumps(chat_event))
    except Exception:
        pass

    return msg


@router.get("/{order_id}/messages", response_model=list[ChatMessageResponse])
async def list_chat_messages(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """FR-TRACK-03: Retrieve chat history for order."""
    res = await db.execute(select(Order).where(Order.id == str(order_id)))
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    if current_user.role != UserRole.admin:
        if order.customer_id != current_user.id and order.technician_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Bạn không tham gia đơn hàng này."}},
            )

    msg_res = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.order_id == str(order_id))
        .order_by(ChatMessage.created_at.asc())
    )
    return msg_res.scalars().all()


# ── Polling Fallback ───────────────────────────────────────────────────────────

@router.get("/{order_id}/events")
async def get_order_events_stream(
    order_id: UUID,
    since: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """FR-TRACK-01: Polling fallback for status updates, events and messages."""
    res = await db.execute(
        select(Order)
        .options(selectinload(Order.events))
        .where(Order.id == str(order_id))
    )
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    # Filter events since timestamp
    events = order.events
    if since:
        events = [e for e in events if e.created_at > since]

    # Messages since
    msg_query = select(ChatMessage).where(ChatMessage.order_id == str(order_id))
    if since:
        msg_query = msg_query.where(ChatMessage.created_at > since)
    msg_res = await db.execute(msg_query.order_by(ChatMessage.created_at.asc()))
    new_messages = msg_res.scalars().all()

    return {
        "status": order.status.value,
        "technician_id": order.technician_id,
        "final_quote": order.final_quote,
        "total": order.total,
        "events": [
            {
                "id": str(e.id),
                "from_status": e.from_status.value if e.from_status else None,
                "to_status": e.to_status.value,
                "note": e.note,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        "messages": [
            {
                "id": str(m.id),
                "sender_id": str(m.sender_id),
                "sender_role": m.sender_role,
                "content": m.content,
                "media_url": m.media_url,
                "created_at": m.created_at.isoformat(),
            }
            for m in new_messages
        ],
    }

