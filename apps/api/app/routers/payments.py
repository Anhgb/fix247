"""
Payments & Invoicing Router – Fix 24/7.
FR-PAY-01..05, BR-01, BR-02, BR-08, BR-09, AT-05, AT-06.
Invoice breakdown, VietQR, cash confirmation, webhook idempotency, technician wallet.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_customer, require_technician
from app.core.redis import get_redis
from app.models import (
    Order,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    TechnicianProfile,
    User,
    UserRole,
    _uuid_default,
)
from app.providers.payment import get_payment_provider
from app.schemas.payments import (
    CashPaymentConfirm,
    InvoiceItem,
    InvoiceResponse,
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentWebhookPayload,
    WalletInfoResponse,
)
from app.services.auto_confirm import auto_confirm_expired_orders, create_maintenance_log_for_order
from app.services.commission import (
    is_technician_blocked_by_debt,
    record_order_commission,
    settle_technician_debt,
)
from app.services.invoice import calculate_invoice_breakdown
from app.services.order_state_machine import transition_order
from app.services.platform_config import get_config

router = APIRouter(tags=["payments"])


# ── Invoice Generation (FR-PAY-01) ─────────────────────────────────────────────

@router.get("/orders/{order_id}/invoice", response_model=InvoiceResponse)
async def get_order_invoice(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-PAY-01, BR-01, BR-02:
    Generate itemized electronic invoice with exact integer arithmetic.
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.customer),
            selectinload(Order.payment),
            selectinload(Order.asset),
        )
        .where(Order.id == str(order_id))
    )
    res = await db.execute(stmt)
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    # Authorization
    if current_user.role != UserRole.admin:
        if order.customer_id != current_user.id and order.technician_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Bạn không có quyền xem hóa đơn này."}},
            )

    # Get technician name & phone
    tech_name = None
    tech_phone = None
    if order.technician_id:
        t_user = (await db.execute(select(User).where(User.id == order.technician_id))).scalar_one_or_none()
        if t_user:
            tech_name = t_user.name
            tech_phone = t_user.phone

    comm_cfg = await get_config(db, "commission_rate", default="0.10")
    commission_rate = float(comm_cfg)

    items = order.items or []
    breakdown = calculate_invoice_breakdown(order, items, commission_rate=commission_rate)

    invoice_items = [
        InvoiceItem(
            name=it.name,
            item_type=it.item_type.value,
            qty=it.qty,
            unit_price=it.unit_price,
            line_total=it.qty * it.unit_price,
        )
        for it in items
    ]

    return InvoiceResponse(
        order_id=order.id,
        customer_name=order.customer.name if order.customer else None,
        customer_phone=order.customer.phone if order.customer else "",
        technician_name=tech_name,
        technician_phone=tech_phone,
        address=order.address,
        items=invoice_items,
        labor_subtotal=breakdown["labor_subtotal"],
        parts_subtotal=breakdown["parts_subtotal"],
        night_surcharge=breakdown["night_surcharge"],
        total=breakdown["total"],
        commission_rate=breakdown["commission_rate"],
        commission_amount=breakdown["commission_amount"],
        warranty_days=breakdown["warranty_days"],
        created_at=order.created_at,
        paid_at=order.payment.paid_at if order.payment else None,
        payment_method=order.payment.method if order.payment else None,
    )


# ── Create Payment (VietQR / Cash) ─────────────────────────────────────────────

@router.post("/orders/{order_id}/pay", response_model=PaymentCreateResponse)
async def create_order_payment(
    order_id: UUID,
    payload: PaymentCreateRequest,
    current_user: User = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-PAY-01, FR-PAY-02:
    Create payment request.
    For VietQR: generates dynamic QR code with exact amount.
    For Cash: marks pending cash collection.
    """
    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.payment))
        .where(Order.id == str(order_id))
    )
    res = await db.execute(stmt)
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

    comm_cfg = await get_config(db, "commission_rate", default="0.10")
    breakdown = calculate_invoice_breakdown(order, order.items or [], commission_rate=float(comm_cfg))
    total_amount = breakdown["total"]

    payment = order.payment
    if not payment:
        payment = Payment(
            id=_uuid_default(),
            order_id=order.id,
            method=payload.method,
            amount=total_amount,
            commission_amount=breakdown["commission_amount"],
            status=PaymentStatus.pending,
        )
        db.add(payment)
    else:
        payment.method = payload.method
        payment.amount = total_amount
        payment.commission_amount = breakdown["commission_amount"]

    provider = get_payment_provider()
    qr_data = None
    if payload.method == PaymentMethod.vietqr:
        qr_info = await provider.create_payment_request(
            order_id=str(order.id),
            amount=total_amount,
            description=f"FIX247 {str(order.id)[:8]}",
        )
        payment.provider_ref = qr_info["provider_ref"]
        qr_data = qr_info
    else:
        payment.provider_ref = f"cash_{str(order.id)[:8]}"

    await db.commit()
    await db.refresh(payment)

    return PaymentCreateResponse(
        payment_id=payment.id,
        order_id=order.id,
        method=payment.method,
        amount=payment.amount,
        status=payment.status,
        provider_ref=payment.provider_ref,
        qr_url=qr_data.get("qr_url") if qr_data else None,
        account_name=qr_data.get("account_name") if qr_data else None,
        account_number=qr_data.get("account_number") if qr_data else None,
        bank_name=qr_data.get("bank_name") if qr_data else None,
    )


# ── Cash Payment Confirmation (FR-PAY-03) ──────────────────────────────────────

@router.post("/orders/{order_id}/cash-confirm")
async def confirm_cash_collected(
    order_id: UUID,
    payload: CashPaymentConfirm,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-PAY-03: Technician confirms cash collected from customer.
    Records cash payment and updates technician commission debt.
    """
    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.payment))
        .where(Order.id == str(order_id))
    )
    res = await db.execute(stmt)
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

    comm_cfg = await get_config(db, "commission_rate", default="0.10")
    breakdown = calculate_invoice_breakdown(order, order.items or [], commission_rate=float(comm_cfg))

    payment = order.payment
    if not payment:
        payment = Payment(
            id=_uuid_default(),
            order_id=order.id,
            method=PaymentMethod.cash,
            amount=payload.amount_collected,
            commission_amount=breakdown["commission_amount"],
            status=PaymentStatus.completed,
            provider_ref=f"cash_{str(order.id)[:8]}",
            paid_at=datetime.now(timezone.utc),
        )
        db.add(payment)
    else:
        payment.status = PaymentStatus.completed
        payment.paid_at = datetime.now(timezone.utc)
        payment.amount = payload.amount_collected

    # Update technician wallet debt
    tp_stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == current_user.id)
    tp_res = await db.execute(tp_stmt)
    profile = tp_res.scalar_one_or_none()
    if profile:
        await record_order_commission(
            db,
            profile,
            earned_amount=payload.amount_collected,
            commission_amount=breakdown["commission_amount"],
        )

    await db.commit()

    return {
        "status": "completed",
        "amount_collected": payload.amount_collected,
        "message": "Thợ đã xác nhận thu tiền mặt thành công.",
    }


# ── Payment Webhook & Idempotency (AT-06, FR-PAY-02) ───────────────────────────

@router.post("/payments/webhook")
async def payment_gateway_webhook(
    payload: PaymentWebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    FR-PAY-02, AT-06:
    Payment gateway webhook with signature verification and idempotency by provider_ref.
    Sending webhook twice for the same provider_ref records only once.
    """
    provider = get_payment_provider()

    # 1. Verify signature
    is_valid = await provider.verify_webhook_signature(
        payload=json.dumps(payload.model_dump()).encode("utf-8"),
        signature=payload.signature,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_SIGNATURE", "message": "Chữ ký webhook không hợp lệ."}},
        )

    # 2. AT-06 Idempotency Check: query payment by provider_ref
    stmt = (
        select(Payment)
        .options(selectinload(Payment.order))
        .where(Payment.provider_ref == payload.provider_ref)
    )
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    # If already completed, return 200 without double processing
    if payment and payment.status == PaymentStatus.completed:
        return {
            "status": "already_processed",
            "provider_ref": payload.provider_ref,
            "message": "Giao dịch đã được ghi nhận trước đó (Idempotent).",
        }

    # 3. Locate order
    o_stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.events))
        .where(Order.id == payload.order_id)
    )
    o_res = await db.execute(o_stmt)
    order = o_res.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    comm_cfg = await get_config(db, "commission_rate", default="0.10")
    breakdown = calculate_invoice_breakdown(order, order.items or [], commission_rate=float(comm_cfg))

    if not payment:
        payment = Payment(
            id=_uuid_default(),
            order_id=order.id,
            method=PaymentMethod.vietqr,
            amount=payload.amount,
            commission_amount=breakdown["commission_amount"],
            status=PaymentStatus.completed,
            provider_ref=payload.provider_ref,
            paid_at=datetime.now(timezone.utc),
        )
        db.add(payment)
    else:
        payment.status = PaymentStatus.completed
        payment.paid_at = datetime.now(timezone.utc)

    # Transition order to COMPLETED if in AWAITING_CONFIRM
    if order.status == OrderStatus.AWAITING_CONFIRM:
        await transition_order(
            db,
            order,
            OrderStatus.COMPLETED,
            note=f"Thanh toán trực tuyến thành công ({payload.provider_ref})",
        )
        order.completed_at = datetime.now(timezone.utc)
        await create_maintenance_log_for_order(db, order)

    # Record technician earnings & platform commission
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
                earned_amount=payload.amount,
                commission_amount=breakdown["commission_amount"],
            )

    await db.commit()

    return {
        "status": "success",
        "provider_ref": payload.provider_ref,
        "order_id": str(order.id),
        "amount": payload.amount,
    }


# ── Technician Wallet & Debt (BR-09, FR-TECH-04) ───────────────────────────────

@router.get("/tech/wallet", response_model=WalletInfoResponse)
async def get_technician_wallet(
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    BR-09, FR-TECH-04:
    Get technician wallet stats, accumulated commission debt, and blocking status.
    """
    tp_stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == current_user.id)
    tp_res = await db.execute(tp_stmt)
    profile = tp_res.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "PROFILE_NOT_FOUND", "message": "Không tìm thấy hồ sơ thợ."}},
        )

    is_blocked, reason = is_technician_blocked_by_debt(profile)

    return WalletInfoResponse(
        technician_id=profile.id,
        total_earned=profile.total_earned or 0,
        total_commission=profile.total_commission or 0,
        debt_amount=profile.debt_amount or 0,
        debt_overdue_at=profile.debt_overdue_at,
        is_blocked=is_blocked,
        block_reason=reason,
    )


@router.post("/tech/wallet/settle-debt")
async def settle_debt_endpoint(
    amount: int,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    BR-09: Technician settles platform commission debt.
    """
    tp_stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == current_user.id)
    tp_res = await db.execute(tp_stmt)
    profile = tp_res.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "PROFILE_NOT_FOUND", "message": "Không tìm thấy hồ sơ thợ."}},
        )

    remaining_debt = await settle_technician_debt(db, profile, amount)
    await db.commit()

    return {
        "status": "success",
        "settled_amount": amount,
        "remaining_debt": remaining_debt,
        "message": f"Đã thanh toán công nợ {amount:,.0f}đ thành công.",
    }


# ── Auto-Confirm Trigger (AT-05, BR-08) ────────────────────────────────────────

@router.post("/orders/auto-confirm")
async def trigger_auto_confirm(
    cutoff_hours: int = 24,
    db: AsyncSession = Depends(get_db),
):
    """
    FR-PAY-04, BR-08, AT-05:
    Job endpoint to auto-confirm orders that have been in AWAITING_CONFIRM for >24h.
    """
    confirmed = await auto_confirm_expired_orders(db, cutoff_hours=cutoff_hours)
    return {
        "status": "ok",
        "confirmed_count": len(confirmed),
        "confirmed_order_ids": confirmed,
    }

