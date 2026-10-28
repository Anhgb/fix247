"""
Technician router – Fix 24/7.
FR-TECH-02/03, FR-BOOK-01/02, FR-TRACK-02.
Technician status toggle, live location reporting, accept/decline job invites.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_technician
from app.core.encryption import encrypt
from app.core.redis import get_redis
from app.models import (
    ApprovalStatus,
    Diagnosis,
    Order,
    OrderStatus,
    Review,
    TechnicianProfile,
    User,
    VerifiedLabel,
    _uuid_default,
)
from app.schemas.diagnosis import DiagnosisAccuracyStats, TechDiagnosisLabelRequest
from app.schemas.orders import TechLocationUpdate
from app.schemas.technician import (
    TechApprovalRequest,
    TechOrderHistoryItem,
    TechOrderHistoryResponse,
    TechProfileOnboardingRequest,
    TechProfileResponse,
)
from app.services.technician_location import update_technician_location
from app.services.technician_service import compute_technician_badges, mask_id_number

router = APIRouter(tags=["technician"])


class TechStatusUpdate(BaseModel):
    is_online: bool


# ── Toggle Online/Offline ──────────────────────────────────────────────────────

@router.patch("/tech/status")
async def toggle_technician_status(
    payload: TechStatusUpdate,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-TECH-03, AT-07: Toggle technician online/offline status.
    Technician MUST be approved to go online.
    """
    res = await db.execute(
        select(TechnicianProfile).where(TechnicianProfile.user_id == current_user.id)
    )
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "PROFILE_NOT_FOUND", "message": "Chưa tìm thấy hồ sơ thợ."}},
        )

    # AT-07: Unapproved technician cannot go online
    if payload.is_online and profile.approval_status != ApprovalStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "NOT_APPROVED",
                    "message": "Tài khoản của bạn chưa được duyệt nên không thể bật trạng thái trực tuyến (AT-07).",
                }
            },
        )

    profile.is_online = payload.is_online
    if not payload.is_online:
        profile.location_updated_at = None
    else:
        profile.location_updated_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "is_online": profile.is_online,
        "approval_status": profile.approval_status.value,
        "message": "Đã chuyển sang trực tuyến" if profile.is_online else "Đã tắt trực tuyến",
    }


# ── Report Location ────────────────────────────────────────────────────────────

@router.post("/tech/location")
async def report_technician_location(
    payload: TechLocationUpdate,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-TECH-03, FR-TRACK-02: Update technician's current GPS location.
    If technician has an active order in ON_THE_WAY status, publishes position to stream.
    """
    res = await db.execute(
        select(TechnicianProfile).where(TechnicianProfile.user_id == current_user.id)
    )
    profile = res.scalar_one_or_none()
    if not profile or not profile.is_online:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "NOT_ONLINE", "message": "Bạn đang ngoại tuyến. Vui lòng bật trực tuyến trước."}},
        )

    await update_technician_location(db, current_user.id, payload.lat, payload.lng)
    await db.commit()

    # FR-TRACK-02: If assigned order is in ON_THE_WAY, publish location
    active_order_res = await db.execute(
        select(Order).where(
            Order.technician_id == current_user.id,
            Order.status == OrderStatus.ON_THE_WAY,
        )
    )
    active_order = active_order_res.scalar_one_or_none()
    if active_order:
        try:
            redis = await get_redis()
            loc_msg = json.dumps({
                "type": "location",
                "order_id": str(active_order.id),
                "lat": payload.lat,
                "lng": payload.lng,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            await redis.publish(f"loc:{active_order.id}", loc_msg)
            await redis.publish(f"order:{active_order.id}", loc_msg)
        except Exception:
            pass

    return {"status": "ok", "lat": payload.lat, "lng": payload.lng}


# ── Accept Job Invite ──────────────────────────────────────────────────────────

@router.post("/orders/{order_id}/accept")
async def accept_order_invite(
    order_id: UUID,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-BOOK-01/02, BR-09:
    Technician accepts sequential job invite within 60s window.
    Checks BR-09 debt limit: blocks if debt > 500k or overdue 7 days.
    """
    # BR-09: Check debt blocking
    tp_stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == current_user.id)
    tp_res = await db.execute(tp_stmt)
    profile = tp_res.scalar_one_or_none()
    if profile:
        from app.services.commission import is_technician_blocked_by_debt
        is_blocked, reason = is_technician_blocked_by_debt(profile)
        if is_blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "DEBT_BLOCKED", "message": f"Không thể nhận đơn mới: {reason}"}},
            )

    redis = await get_redis()
    o_id = str(order_id)
    tech_id = str(current_user.id)

    # Set response in Redis for worker
    await redis.setex(f"dispatch:{o_id}:response:{tech_id}", 120, "accepted")

    return {
        "status": "accepted",
        "order_id": o_id,
        "message": "Đã chấp nhận yêu cầu sửa chữa.",
    }


# ── Decline Job Invite ─────────────────────────────────────────────────────────

@router.post("/orders/{order_id}/decline")
async def decline_order_invite(
    order_id: UUID,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-BOOK-01/02: Technician declines job invite.
    Sets Redis response key so worker can immediately move to next candidate.
    """
    redis = await get_redis()
    o_id = str(order_id)
    tech_id = str(current_user.id)

    await redis.setex(f"dispatch:{o_id}:response:{tech_id}", 120, "declined")

    return {
        "status": "declined",
        "order_id": o_id,
        "message": "Đã từ chối yêu cầu sửa chữa.",
    }


# ── Technician Profile / Dashboard Stats ──────────────────────────────────────

@router.get("/tech/dashboard-info")
async def get_tech_dashboard_info(
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """Get technician profile info and active order for dashboard."""
    res = await db.execute(
        select(TechnicianProfile).where(TechnicianProfile.user_id == current_user.id)
    )
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Không tìm thấy hồ sơ thợ."}},
        )

    # Active assigned order
    active_statuses = [
        OrderStatus.ACCEPTED,
        OrderStatus.ON_THE_WAY,
        OrderStatus.SURVEYING,
        OrderStatus.QUOTE_PENDING,
        OrderStatus.IN_REPAIR,
    ]
    o_res = await db.execute(
        select(Order).where(
            Order.technician_id == current_user.id,
            Order.status.in_(active_statuses),
        )
    )
    active_order = o_res.scalar_one_or_none()

    return {
        "is_online": profile.is_online,
        "approval_status": profile.approval_status.value,
        "rating_avg": float(profile.rating_avg) if profile.rating_avg else 5.0,
        "rating_count": profile.rating_count,
        "total_earned": profile.total_earned,
        "debt_amount": profile.debt_amount,
        "active_order_id": str(active_order.id) if active_order else None,
    }


# ── Technician Profile Onboarding & View ──────────────────────────────────────

@router.get("/tech/profile", response_model=TechProfileResponse)
async def get_technician_profile(
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-TECH-01, FR-TECH-04, UC-08:
    Get detailed profile of current technician with masked CCCD and earned badges.
    """
    res = await db.execute(
        select(TechnicianProfile).where(TechnicianProfile.user_id == current_user.id)
    )
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "PROFILE_NOT_FOUND", "message": "Chưa có hồ sơ thợ."}},
        )

    badges = compute_technician_badges(profile)
    masked_id = mask_id_number(profile.id_number_encrypted)

    return TechProfileResponse(
        id=UUID(profile.id),
        user_id=UUID(profile.user_id),
        id_number_masked=masked_id,
        portrait_url=profile.portrait_url,
        certificate_urls=profile.certificate_urls or [],
        specialties=profile.specialties or [],
        service_areas=profile.service_areas or [],
        approval_status=profile.approval_status,
        approval_note=profile.approval_note,
        approved_at=profile.approved_at,
        is_online=bool(profile.is_online),
        rating_avg=float(profile.rating_avg) if profile.rating_avg else 5.0,
        rating_count=profile.rating_count or 0,
        total_earned=profile.total_earned or 0,
        debt_amount=profile.debt_amount or 0,
        badges=badges,
        created_at=profile.created_at or datetime.now(timezone.utc),
        updated_at=profile.updated_at or datetime.now(timezone.utc),
    )


@router.post("/tech/profile", response_model=TechProfileResponse)
async def register_or_update_technician_profile(
    payload: TechProfileOnboardingRequest,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-TECH-01, FR-TECH-02, UC-08:
    Technician onboarding / profile update.
    National ID (CCCD) is securely encrypted with AES-256 (NFR-04).
    Max 5 certificates (A-11).
    """
    if len(payload.certificate_urls) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "TOO_MANY_CERTIFICATES", "message": "Tối đa 5 chứng chỉ nghề (A-11)."}},
        )

    encrypted_cccd = encrypt(payload.id_number.strip())

    res = await db.execute(
        select(TechnicianProfile).where(TechnicianProfile.user_id == current_user.id)
    )
    profile = res.scalar_one_or_none()

    if not profile:
        profile = TechnicianProfile(
            id=_uuid_default(),
            user_id=current_user.id,
            id_number_encrypted=encrypted_cccd,
            portrait_url=payload.portrait_url.strip(),
            certificate_urls=payload.certificate_urls,
            specialties=payload.specialties,
            service_areas=payload.service_areas,
            approval_status=ApprovalStatus.pending,
            is_online=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(profile)
    else:
        profile.id_number_encrypted = encrypted_cccd
        profile.portrait_url = payload.portrait_url.strip()
        profile.certificate_urls = payload.certificate_urls
        profile.specialties = payload.specialties
        profile.service_areas = payload.service_areas
        # If rejected or new submission, reset to pending
        if profile.approval_status == ApprovalStatus.rejected:
            profile.approval_status = ApprovalStatus.pending
            profile.approval_note = None

    await db.commit()
    await db.refresh(profile)

    badges = compute_technician_badges(profile)
    masked_id = mask_id_number(profile.id_number_encrypted)

    return TechProfileResponse(
        id=UUID(profile.id),
        user_id=UUID(profile.user_id),
        id_number_masked=masked_id,
        portrait_url=profile.portrait_url,
        certificate_urls=profile.certificate_urls or [],
        specialties=profile.specialties or [],
        service_areas=profile.service_areas or [],
        approval_status=profile.approval_status,
        approval_note=profile.approval_note,
        approved_at=profile.approved_at,
        is_online=bool(profile.is_online),
        rating_avg=float(profile.rating_avg) if profile.rating_avg else 5.0,
        rating_count=profile.rating_count or 0,
        total_earned=profile.total_earned or 0,
        debt_amount=profile.debt_amount or 0,
        badges=badges,
        created_at=profile.created_at or datetime.now(timezone.utc),
        updated_at=profile.updated_at or datetime.now(timezone.utc),
    )


# ── Technician Order History ───────────────────────────────────────────────────

@router.get("/tech/orders/history", response_model=TechOrderHistoryResponse)
async def get_technician_order_history(
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-TECH-04, UC-08:
    Get historical jobs completed or handled by this technician with earnings and ratings.
    """
    history_statuses = [OrderStatus.COMPLETED, OrderStatus.CANCELLED, OrderStatus.WARRANTY]
    stmt = (
        select(Order)
        .where(
            Order.technician_id == current_user.id,
            Order.status.in_(history_statuses),
        )
        .order_by(Order.updated_at.desc())
    )
    res = await db.execute(stmt)
    orders = res.scalars().all()

    items: list[TechOrderHistoryItem] = []
    total_earnings = 0

    for o in orders:
        cust_name = "Khách hàng"
        if o.customer_id:
            cust_user = await db.get(User, o.customer_id)
            if cust_user:
                cust_name = f"Khách {cust_user.phone[-4:]}"

        # Get review if exists
        rev_stmt = select(Review).where(Review.order_id == str(o.id), Review.from_user_id == o.customer_id)
        rev = (await db.execute(rev_stmt)).scalar_one_or_none()

        # Tech earnings = labor + parts (night surcharge 100% to tech, commission 10% deducted from base)
        order_total = o.total or 0
        from app.services.invoice import calculate_invoice_breakdown
        breakdown = calculate_invoice_breakdown(o, o.items or [])
        commission = breakdown.get("commission_amount", 0)
        tech_earnings = max(0, order_total - commission)

        if o.status == OrderStatus.COMPLETED:
            total_earnings += tech_earnings

        items.append(
            TechOrderHistoryItem(
                order_id=UUID(o.id),
                code=f"#{str(o.id)[:8]}",
                service_name=o.mode.value,
                status=o.status.value,
                customer_name=cust_name,
                address=o.address or "Thành phố Huế",
                completed_at=o.completed_at or o.updated_at,
                total_amount=order_total,
                tech_earnings=tech_earnings,
                customer_rating=rev.stars if rev else None,
                customer_comment=rev.comment if rev else None,
            )
        )

    return TechOrderHistoryResponse(
        total=len(items),
        items=items,
        total_earnings=total_earnings,
    )


# ── DIAG-9: Technician Diagnosis Accuracy Feedback ───────────────────────────

@router.post("/orders/{order_id}/diagnosis-feedback")
async def submit_technician_diagnosis_feedback(
    order_id: UUID,
    payload: TechDiagnosisLabelRequest,
    current_user: User = Depends(require_technician),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-DIAG-09: Technician labels diagnosis accuracy after the job.
    Label: correct / partial / incorrect.
    Stored in diagnoses.verified_label for accuracy tracking.
    """
    stmt = select(Order).where(Order.id == str(order_id))
    order = (await db.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ORDER_NOT_FOUND", "message": "Không tìm thấy đơn hàng."}},
        )

    if order.technician_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Bạn không phải thợ của đơn hàng này."}},
        )

    if not order.diagnosis_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "NO_DIAGNOSIS", "message": "Đơn hàng này không có kết quả chẩn đoán AI."}},
        )

    diag = await db.get(Diagnosis, order.diagnosis_id)
    if not diag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DIAGNOSIS_NOT_FOUND", "message": "Không tìm thấy bản ghi chẩn đoán."}},
        )

    diag.verified_label = VerifiedLabel(payload.verified_label)
    diag.verified_by_id = current_user.id
    diag.verified_at = datetime.now(timezone.utc)
    if payload.notes:
        diag.customer_feedback_notes = f"[Thợ nhận xét]: {payload.notes}"

    await db.commit()

    return {
        "ok": True,
        "order_id": str(order_id),
        "diagnosis_id": str(diag.id),
        "verified_label": diag.verified_label.value,
        "message": "Đã ghi nhận đánh giá độ chính xác chẩn đoán AI thành công (FR-DIAG-09).",
    }


# ── Admin Approval Endpoints ──────────────────────────────────────────────────

@router.post("/admin/technicians/{tech_user_id}/approve")
async def admin_approve_technician(
    tech_user_id: UUID,
    payload: TechApprovalRequest = TechApprovalRequest(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin approves technician profile (FR-TECH-01)."""
    stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == str(tech_user_id))
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "PROFILE_NOT_FOUND", "message": "Không tìm thấy hồ sơ thợ."}},
        )

    profile.approval_status = ApprovalStatus.approved
    profile.approved_by_id = current_user.id
    profile.approved_at = datetime.now(timezone.utc)
    profile.approval_note = payload.note
    await db.commit()

    return {
        "ok": True,
        "user_id": str(tech_user_id),
        "approval_status": profile.approval_status.value,
        "message": "Đã duyệt thợ thành công. Thợ hiện có thể bật trực tuyến để nhận việc.",
    }


@router.post("/admin/technicians/{tech_user_id}/reject")
async def admin_reject_technician(
    tech_user_id: UUID,
    payload: TechApprovalRequest = TechApprovalRequest(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin rejects technician profile."""
    stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == str(tech_user_id))
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "PROFILE_NOT_FOUND", "message": "Không tìm thấy hồ sơ thợ."}},
        )

    profile.approval_status = ApprovalStatus.rejected
    profile.approval_note = payload.note or "Hồ sơ chưa đạt yêu cầu"
    profile.is_online = False
    await db.commit()

    return {
        "ok": True,
        "user_id": str(tech_user_id),
        "approval_status": profile.approval_status.value,
        "message": "Đã từ chối duyệt hồ sơ thợ.",
    }


@router.post("/admin/technicians/{tech_user_id}/suspend")
async def admin_suspend_technician(
    tech_user_id: UUID,
    payload: TechApprovalRequest = TechApprovalRequest(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin suspends technician account (FR-TECH-05)."""
    stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == str(tech_user_id))
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "PROFILE_NOT_FOUND", "message": "Không tìm thấy hồ sơ thợ."}},
        )

    profile.approval_status = ApprovalStatus.suspended
    profile.approval_note = payload.note or "Tài khoản bị tạm đình chỉ do vi phạm quy chế hoặc điểm thấp"
    profile.is_online = False
    await db.commit()

    return {
        "ok": True,
        "user_id": str(tech_user_id),
        "approval_status": profile.approval_status.value,
        "message": "Đã tạm đình chỉ tài khoản thợ.",
    }


@router.get("/admin/technicians/pending")
async def admin_list_pending_technicians(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin lists all technicians waiting for approval."""
    stmt = (
        select(TechnicianProfile)
        .where(TechnicianProfile.approval_status == ApprovalStatus.pending)
        .order_by(TechnicianProfile.created_at.asc())
    )
    res = await db.execute(stmt)
    profiles = res.scalars().all()

    items = []
    for p in profiles:
        user = await db.get(User, p.user_id)
        items.append({
            "profile_id": str(p.id),
            "user_id": str(p.user_id),
            "phone": user.phone if user else "",
            "id_number_masked": mask_id_number(p.id_number_encrypted),
            "portrait_url": p.portrait_url,
            "certificate_urls": p.certificate_urls or [],
            "specialties": p.specialties or [],
            "service_areas": p.service_areas or [],
            "created_at": p.created_at,
        })
    return {"total": len(items), "items": items}


@router.get("/admin/diagnoses/accuracy", response_model=DiagnosisAccuracyStats)
async def admin_get_diagnosis_accuracy(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-DIAG-09: Expose AI diagnosis accuracy metrics based on technician labels.
    """
    stmt = select(Diagnosis).where(Diagnosis.verified_label.is_not(None))
    res = await db.execute(stmt)
    records = res.scalars().all()

    total = len(records)
    correct = sum(1 for r in records if r.verified_label == VerifiedLabel.correct)
    partial = sum(1 for r in records if r.verified_label == VerifiedLabel.partial)
    incorrect = sum(1 for r in records if r.verified_label == VerifiedLabel.incorrect)

    acc = round((correct + 0.5 * partial) / total * 100, 1) if total > 0 else 0.0

    return DiagnosisAccuracyStats(
        total_verified=total,
        correct_count=correct,
        partial_count=partial,
        incorrect_count=incorrect,
        accuracy_percentage=acc,
    )


