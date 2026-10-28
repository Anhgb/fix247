"""
Admin API Router – Fix 24/7 (Phase P5)
Requirements: UC-10, UC-11, UC-12, FR-ADM-01..04, FR-QR-01..02, AT-07, AT-08.
All endpoints protected by require_admin.
"""
import csv
import io
import math
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import desc, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.config import get_settings
from app.models import (
    AdminActionLog,
    ApprovalStatus,
    Dispute,
    DisputeStatus,
    FaultCatalog,
    Order,
    OrderEvent,
    OrderItem,
    OrderMode,
    OrderStatus,
    Payment,
    QRLocation,
    ServiceCategory,
    TechnicianProfile,
    User,
    UserRole,
    Diagnosis,
    VerifiedLabel,
)
from app.schemas.admin import (
    AdminActionLogListResponse,
    AdminActionLogResponse,
    AdminDashboardStats,
    DisputeListResponse,
    DisputeResolveRequest,
    DisputeResponse,
    FaultCatalogCreate,
    FaultCatalogListResponse,
    FaultCatalogResponse,
    FaultCatalogUpdate,
    OrderInterventionCancelRequest,
    OrderInterventionNoteRequest,
    OrderInterventionReassignRequest,
    OrderInterventionTransitionRequest,
    PlatformSettingsResponse,
    PlatformSettingsUpdate,
)
from app.schemas.qr import (
    QRLocationCreate,
    QRLocationListResponse,
    QRLocationResponse,
    QRLocationUpdate,
)
from app.schemas.technician import TechApprovalRequest
from app.services.audit_service import log_admin_action
from app.services.order_state_machine import transition_order
from app.services.platform_config import get_config, set_config
from app.services.technician_service import compute_technician_badges, mask_id_number

router = APIRouter(prefix="/admin", tags=["admin"])


# ── 1. Admin Dashboard (UC-10, FR-ADM-01) ────────────────────────────────────

@router.get("/dashboard", response_model=AdminDashboardStats)
async def get_admin_dashboard_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    UC-10, FR-ADM-01: Realtime KPIs, GMV, commission, median time-to-accept,
    AI accuracy, AI & Maps spend and budget alerts.
    """
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # Orders stats
    total_orders_stmt = select(func.count(Order.id))
    orders_total = (await db.execute(total_orders_stmt)).scalar() or 0

    today_orders_stmt = select(func.count(Order.id)).where(Order.created_at >= today_start)
    orders_today = (await db.execute(today_orders_stmt)).scalar() or 0

    # GMV & Commission (Completed orders)
    gmv_stmt = select(func.sum(Order.total)).where(Order.status == OrderStatus.COMPLETED)
    gmv_total = (await db.execute(gmv_stmt)).scalar() or 0

    gmv_today_stmt = select(func.sum(Order.total)).where(
        Order.status == OrderStatus.COMPLETED,
        Order.completed_at >= today_start,
    )
    gmv_today = (await db.execute(gmv_today_stmt)).scalar() or 0

    commission_stmt = select(func.sum(Order.commission_amount)).where(Order.status == OrderStatus.COMPLETED)
    commission_total = (await db.execute(commission_stmt)).scalar() or 0

    # Completion Rate & Dispute Rate
    completed_stmt = select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED)
    completed_count = (await db.execute(completed_stmt)).scalar() or 0
    completion_rate = round(completed_count / orders_total * 100, 1) if orders_total > 0 else 0.0

    disputes_stmt = select(func.count(Dispute.id))
    disputes_count = (await db.execute(disputes_stmt)).scalar() or 0
    dispute_rate = round(disputes_count / orders_total * 100, 1) if orders_total > 0 else 0.0

    # Median Time-to-Accept for emergency orders
    times_stmt = (
        select(Order.created_at, Order.accepted_at)
        .where(
            Order.mode == OrderMode.emergency,
            Order.accepted_at.is_not(None),
        )
    )
    times_res = await db.execute(times_stmt)
    durations = [
        int((accepted - created).total_seconds())
        for created, accepted in times_res.all()
        if accepted and created and accepted >= created
    ]
    median_time_sec = None
    if durations:
        durations.sort()
        n = len(durations)
        median_time_sec = durations[n // 2] if n % 2 != 0 else int((durations[n // 2 - 1] + durations[n // 2]) / 2)

    # AI Stats
    ai_diag_stmt = select(func.count(Diagnosis.id))
    ai_calls_total = (await db.execute(ai_diag_stmt)).scalar() or 0

    ai_verified_stmt = select(Diagnosis).where(Diagnosis.verified_label.is_not(None))
    verified_records = (await db.execute(ai_verified_stmt)).scalars().all()
    correct_count = sum(1 for r in verified_records if r.verified_label == VerifiedLabel.correct)
    partial_count = sum(1 for r in verified_records if r.verified_label == VerifiedLabel.partial)
    ai_top3_accuracy = (
        round((correct_count + 0.5 * partial_count) / len(verified_records) * 100, 1)
        if verified_records
        else 0.0
    )

    # Budgets & Spend calculation
    ai_cost_per_call = 150  # 150 VND per Gemini API call average
    daily_ai_calls = (
        await db.execute(select(func.count(Diagnosis.id)).where(Diagnosis.created_at >= today_start))
    ).scalar() or 0
    monthly_ai_calls = (
        await db.execute(select(func.count(Diagnosis.id)).where(Diagnosis.created_at >= month_start))
    ).scalar() or 0

    ai_daily_spend = daily_ai_calls * ai_cost_per_call
    ai_monthly_spend = monthly_ai_calls * ai_cost_per_call

    monthly_ai_budget = int(await get_config(db, "monthly_ai_budget_vnd", "5000000"))
    monthly_maps_budget = int(await get_config(db, "monthly_maps_budget_vnd", "3000000"))

    # Maps spend (estimated ~100 VND per geocode/distance call, ~3 calls per emergency order)
    maps_cost_per_order = 300
    maps_daily_spend = orders_today * maps_cost_per_order
    maps_monthly_orders = (
        await db.execute(select(func.count(Order.id)).where(Order.created_at >= month_start))
    ).scalar() or 0
    maps_monthly_spend = maps_monthly_orders * maps_cost_per_order

    ai_alert = ai_monthly_spend >= (0.8 * monthly_ai_budget)
    maps_alert = maps_monthly_spend >= (0.8 * monthly_maps_budget)

    return AdminDashboardStats(
        orders_total=orders_total,
        orders_today=orders_today,
        gmv_total=gmv_total,
        gmv_today=gmv_today,
        commission_total=commission_total,
        median_time_to_accept_sec=median_time_sec,
        completion_rate_pct=completion_rate,
        dispute_rate_pct=dispute_rate,
        ai_top3_accuracy_pct=ai_top3_accuracy,
        ai_calls_total=ai_calls_total,
        ai_cost_per_call_vnd=ai_cost_per_call,
        ai_daily_spend_vnd=ai_daily_spend,
        ai_monthly_spend_vnd=ai_monthly_spend,
        ai_monthly_budget_vnd=monthly_ai_budget,
        ai_budget_alert=ai_alert,
        maps_daily_spend_vnd=maps_daily_spend,
        maps_monthly_spend_vnd=maps_monthly_spend,
        maps_monthly_budget_vnd=monthly_maps_budget,
        maps_budget_alert=maps_alert,
    )


# ── 2. Technician Review Queue (FR-TECH-01, FR-TECH-05, AT-07) ───────────────

@router.get("/technicians")
async def admin_list_technicians(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all technicians with optional status filter."""
    stmt = select(TechnicianProfile).order_by(TechnicianProfile.created_at.desc())
    if status_filter:
        try:
            enum_status = ApprovalStatus(status_filter)
            stmt = stmt.where(TechnicianProfile.approval_status == enum_status)
        except ValueError:
            pass

    profiles = (await db.execute(stmt)).scalars().all()
    items = []
    for p in profiles:
        user = await db.get(User, p.user_id)
        items.append({
            "profile_id": str(p.id),
            "user_id": str(p.user_id),
            "phone": user.phone if user else "",
            "name": user.name if user and user.name else "Đối tác thợ",
            "id_number_masked": mask_id_number(p.id_number_encrypted),
            "portrait_url": p.portrait_url,
            "certificate_urls": p.certificate_urls or [],
            "specialties": p.specialties or [],
            "service_areas": p.service_areas or [],
            "approval_status": p.approval_status.value,
            "approval_note": p.approval_note,
            "is_online": bool(p.is_online),
            "rating_avg": float(p.rating_avg) if p.rating_avg else 5.0,
            "rating_count": p.rating_count,
            "total_earned": p.total_earned,
            "debt_amount": p.debt_amount,
            "badges": [b.dict() for b in compute_technician_badges(p)],
            "created_at": p.created_at,
        })
    return {"total": len(items), "items": items}


@router.post("/technicians/{tech_user_id}/approve")
async def admin_approve_technician(
    tech_user_id: str,
    payload: TechApprovalRequest = TechApprovalRequest(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """AT-07: Admin approves technician and logs audit trail."""
    stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == str(tech_user_id))
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ thợ.")

    profile.approval_status = ApprovalStatus.approved
    profile.approved_by_id = current_user.id
    profile.approved_at = datetime.now(timezone.utc)
    profile.approval_note = payload.note or "Hồ sơ đã được xác thực"

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="technician_approved",
        entity_type="technician_profile",
        entity_id=str(profile.id),
        detail={"tech_user_id": str(tech_user_id), "note": profile.approval_note},
    )
    await db.commit()

    return {
        "ok": True,
        "user_id": str(tech_user_id),
        "approval_status": "approved",
        "message": "Đã phê duyệt đối tác thợ thành công.",
    }


@router.post("/technicians/{tech_user_id}/reject")
async def admin_reject_technician(
    tech_user_id: str,
    payload: TechApprovalRequest = TechApprovalRequest(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """AT-07: Admin rejects technician with reason and logs audit trail."""
    stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == str(tech_user_id))
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ thợ.")

    profile.approval_status = ApprovalStatus.rejected
    profile.approval_note = payload.note or "Hồ sơ chưa đạt tiêu chuẩn"
    profile.is_online = False

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="technician_rejected",
        entity_type="technician_profile",
        entity_id=str(profile.id),
        detail={"tech_user_id": str(tech_user_id), "reason": profile.approval_note},
    )
    await db.commit()

    return {
        "ok": True,
        "user_id": str(tech_user_id),
        "approval_status": "rejected",
        "message": "Đã từ chối hồ sơ đối tác thợ.",
    }


@router.post("/technicians/{tech_user_id}/suspend")
async def admin_suspend_technician(
    tech_user_id: str,
    payload: TechApprovalRequest = TechApprovalRequest(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """AT-07: Admin suspends technician with reason and logs audit trail."""
    stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == str(tech_user_id))
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ thợ.")

    profile.approval_status = ApprovalStatus.suspended
    profile.approval_note = payload.note or "Tạm đình chỉ tài khoản đối tác"
    profile.is_online = False

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="technician_suspended",
        entity_type="technician_profile",
        entity_id=str(profile.id),
        detail={"tech_user_id": str(tech_user_id), "reason": profile.approval_note},
    )
    await db.commit()

    return {
        "ok": True,
        "user_id": str(tech_user_id),
        "approval_status": "suspended",
        "message": "Đã tạm đình chỉ tài khoản thợ.",
    }


# ── 3. Fault Catalog Management & CSV Import (FR-ADM-02) ──────────────────────

@router.get("/fault-catalog", response_model=FaultCatalogListResponse)
async def admin_list_fault_catalog(
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """FR-ADM-02: List catalog items with category details and search."""
    stmt = select(FaultCatalog, ServiceCategory.name.label("cat_name")).join(
        ServiceCategory, FaultCatalog.category_id == ServiceCategory.id
    ).order_by(FaultCatalog.fault_code.asc())

    if search:
        search_filter = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                FaultCatalog.fault_code.ilike(search_filter),
                FaultCatalog.name.ilike(search_filter),
            )
        )
    if category_id:
        stmt = stmt.where(FaultCatalog.category_id == str(category_id))

    rows = (await db.execute(stmt)).all()
    items = []
    for fc, cat_name in rows:
        items.append(
            FaultCatalogResponse(
                id=str(fc.id),
                category_id=str(fc.category_id),
                category_name=cat_name,
                fault_code=fc.fault_code,
                name=fc.name,
                description=fc.description,
                labor_min=fc.labor_min,
                labor_max=fc.labor_max,
                parts_min=fc.parts_min or 0,
                parts_max=fc.parts_max or 0,
                safety_notes=fc.safety_notes,
                is_active=fc.is_active,
                version=fc.version,
                created_at=fc.created_at or datetime.now(timezone.utc),
                updated_at=fc.updated_at or datetime.now(timezone.utc),
            )
        )
    return FaultCatalogListResponse(total=len(items), items=items)


@router.post("/fault-catalog", response_model=FaultCatalogResponse)
async def admin_create_fault_catalog(
    payload: FaultCatalogCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """FR-ADM-02: Create new fault catalog item with version 1."""
    # Check duplicate fault code
    existing = (
        await db.execute(select(FaultCatalog).where(FaultCatalog.fault_code == payload.fault_code))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "DUPLICATE_CODE", "message": f"Mã lỗi '{payload.fault_code}' đã tồn tại."}},
        )

    fc = FaultCatalog(
        id=str(uuid.uuid4()),
        category_id=str(payload.category_id),
        fault_code=payload.fault_code.strip(),
        name=payload.name.strip(),
        description=payload.description,
        labor_min=payload.labor_min,
        labor_max=payload.labor_max,
        parts_min=payload.parts_min,
        parts_max=payload.parts_max,
        safety_notes=payload.safety_notes,
        is_active=payload.is_active,
        version=1,
    )
    db.add(fc)
    await db.flush()

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="fault_catalog_created",
        entity_type="fault_catalog",
        entity_id=str(fc.id),
        detail={"fault_code": fc.fault_code, "name": fc.name, "version": fc.version},
    )
    await db.commit()

    cat = await db.get(ServiceCategory, fc.category_id)
    return FaultCatalogResponse(
        id=str(fc.id),
        category_id=str(fc.category_id),
        category_name=cat.name if cat else "",
        fault_code=fc.fault_code,
        name=fc.name,
        description=fc.description,
        labor_min=fc.labor_min,
        labor_max=fc.labor_max,
        parts_min=fc.parts_min or 0,
        parts_max=fc.parts_max or 0,
        safety_notes=fc.safety_notes,
        is_active=fc.is_active,
        version=fc.version,
        created_at=fc.created_at or datetime.now(timezone.utc),
        updated_at=fc.updated_at or datetime.now(timezone.utc),
    )


@router.patch("/fault-catalog/{id}", response_model=FaultCatalogResponse)
async def admin_update_fault_catalog(
    id: str,
    payload: FaultCatalogUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-ADM-02: Update fault catalog item. Increments version by 1.
    Existing orders keep the prices quoted at their creation.
    """
    fc = await db.get(FaultCatalog, str(id))
    if not fc:
        raise HTTPException(status_code=404, detail="Không tìm thấy mục lỗi chuẩn.")

    changes = {}
    if payload.name is not None:
        changes["name"] = payload.name.strip()
        fc.name = payload.name.strip()
    if payload.description is not None:
        changes["description"] = payload.description
        fc.description = payload.description
    if payload.labor_min is not None:
        changes["labor_min"] = payload.labor_min
        fc.labor_min = payload.labor_min
    if payload.labor_max is not None:
        changes["labor_max"] = payload.labor_max
        fc.labor_max = payload.labor_max
    if payload.parts_min is not None:
        changes["parts_min"] = payload.parts_min
        fc.parts_min = payload.parts_min
    if payload.parts_max is not None:
        changes["parts_max"] = payload.parts_max
        fc.parts_max = payload.parts_max
    if payload.safety_notes is not None:
        changes["safety_notes"] = payload.safety_notes
        fc.safety_notes = payload.safety_notes
    if payload.is_active is not None:
        changes["is_active"] = payload.is_active
        fc.is_active = payload.is_active

    # Increment version
    fc.version += 1
    changes["version"] = fc.version

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="fault_catalog_updated",
        entity_type="fault_catalog",
        entity_id=str(fc.id),
        detail=changes,
    )
    await db.commit()

    cat = await db.get(ServiceCategory, fc.category_id)
    return FaultCatalogResponse(
        id=str(fc.id),
        category_id=str(fc.category_id),
        category_name=cat.name if cat else "",
        fault_code=fc.fault_code,
        name=fc.name,
        description=fc.description,
        labor_min=fc.labor_min,
        labor_max=fc.labor_max,
        parts_min=fc.parts_min or 0,
        parts_max=fc.parts_max or 0,
        safety_notes=fc.safety_notes,
        is_active=fc.is_active,
        version=fc.version,
        created_at=fc.created_at or datetime.now(timezone.utc),
        updated_at=fc.updated_at or datetime.now(timezone.utc),
    )


@router.post("/fault-catalog/import-csv")
async def admin_import_fault_catalog_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-ADM-02: Bulk CSV import for fault catalog with versioning.
    Headers: fault_code, name, category_group_or_name, labor_min, labor_max, parts_min, parts_max, safety_notes
    """
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except Exception:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    created_count = 0
    updated_count = 0

    # Cache categories
    cats = (await db.execute(select(ServiceCategory))).scalars().all()
    default_cat_id = str(cats[0].id) if cats else None

    for row in reader:
        code = row.get("fault_code", "").strip()
        name = row.get("name", "").strip()
        if not code or not name:
            continue

        l_min = int(row.get("labor_min", 0) or 0)
        l_max = int(row.get("labor_max", l_min) or l_min)
        p_min = int(row.get("parts_min", 0) or 0)
        p_max = int(row.get("parts_max", p_min) or p_min)
        notes = row.get("safety_notes", "") or None
        cat_id = row.get("category_id", "").strip() or default_cat_id

        existing = (
            await db.execute(select(FaultCatalog).where(FaultCatalog.fault_code == code))
        ).scalar_one_or_none()

        if existing:
            existing.name = name
            existing.labor_min = l_min
            existing.labor_max = l_max
            existing.parts_min = p_min
            existing.parts_max = p_max
            existing.safety_notes = notes
            existing.version += 1
            updated_count += 1
        else:
            fc = FaultCatalog(
                id=str(uuid.uuid4()),
                category_id=cat_id,
                fault_code=code,
                name=name,
                labor_min=l_min,
                labor_max=l_max,
                parts_min=p_min,
                parts_max=p_max,
                safety_notes=notes,
                is_active=True,
                version=1,
            )
            db.add(fc)
            created_count += 1

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="fault_catalog_csv_imported",
        entity_type="fault_catalog",
        detail={"created": created_count, "updated": updated_count, "filename": file.filename},
    )
    await db.commit()

    return {
        "ok": True,
        "message": f"Nhập CSV thành công: Thêm mới {created_count} mục, Cập nhật phiên bản {updated_count} mục.",
        "created_count": created_count,
        "updated_count": updated_count,
    }


# ── 4. Order Explorer & Intervention (FR-ADM-03) ─────────────────────────────

@router.get("/orders")
async def admin_list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    mode_filter: Optional[str] = Query(None, alias="mode"),
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """FR-ADM-03: Order explorer with filters."""
    stmt = select(Order).order_by(Order.created_at.desc()).limit(limit).offset(offset)
    if status_filter:
        try:
            stmt = stmt.where(Order.status == OrderStatus(status_filter))
        except ValueError:
            pass
    if mode_filter:
        try:
            stmt = stmt.where(Order.mode == OrderMode(mode_filter))
        except ValueError:
            pass
    if search:
        search_filter = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Order.address.ilike(search_filter),
                Order.customer_note.ilike(search_filter),
            )
        )

    orders = (await db.execute(stmt)).scalars().all()
    items = []
    for o in orders:
        cust = await db.get(User, o.customer_id)
        tech = await db.get(User, o.technician_id) if o.technician_id else None
        items.append({
            "id": str(o.id),
            "mode": o.mode.value,
            "status": o.status.value,
            "address": o.address,
            "customer_id": str(o.customer_id),
            "customer_phone": cust.phone if cust else "",
            "customer_name": cust.name if cust and cust.name else "Khách hàng",
            "technician_id": str(o.technician_id) if o.technician_id else None,
            "technician_phone": tech.phone if tech else None,
            "technician_name": tech.name if tech and tech.name else None,
            "final_quote": o.final_quote,
            "total": o.total,
            "commission_amount": o.commission_amount,
            "created_at": o.created_at,
            "scheduled_at": o.scheduled_at,
            "completed_at": o.completed_at,
        })

    total = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    return {"total": total, "items": items}


@router.get("/orders/{order_id}")
async def admin_get_order_detail(
    order_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Full order detail including events timeline, items, and interventions."""
    order = await db.get(Order, str(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")

    cust = await db.get(User, order.customer_id)
    tech = await db.get(User, order.technician_id) if order.technician_id else None

    # Line items
    items_stmt = select(OrderItem).where(OrderItem.order_id == str(order_id))
    items = (await db.execute(items_stmt)).scalars().all()

    # Events timeline
    events_stmt = (
        select(OrderEvent)
        .where(OrderEvent.order_id == str(order_id))
        .order_by(OrderEvent.created_at.asc())
    )
    events = (await db.execute(events_stmt)).scalars().all()

    # Payment
    payment_stmt = select(Payment).where(Payment.order_id == str(order_id))
    payment = (await db.execute(payment_stmt)).scalar_one_or_none()

    # Dispute if any
    dispute_stmt = select(Dispute).where(Dispute.order_id == str(order_id))
    dispute = (await db.execute(dispute_stmt)).scalar_one_or_none()

    return {
        "id": str(order.id),
        "mode": order.mode.value,
        "status": order.status.value,
        "address": order.address,
        "lat": float(order.lat) if order.lat else None,
        "lng": float(order.lng) if order.lng else None,
        "customer": {
            "id": str(cust.id),
            "phone": cust.phone,
            "name": cust.name,
        } if cust else None,
        "technician": {
            "id": str(tech.id),
            "phone": tech.phone,
            "name": tech.name,
        } if tech else None,
        "est_min": order.est_min,
        "est_max": order.est_max,
        "final_quote": order.final_quote,
        "total": order.total,
        "commission_amount": order.commission_amount,
        "night_surcharge": order.night_surcharge,
        "survey_fee": order.survey_fee,
        "cancel_reason": order.cancel_reason,
        "created_at": order.created_at,
        "accepted_at": order.accepted_at,
        "completed_at": order.completed_at,
        "items": [
            {
                "id": str(i.id),
                "item_type": i.item_type.value,
                "name": i.name,
                "qty": i.qty,
                "unit_price": i.unit_price,
            }
            for i in items
        ],
        "events": [
            {
                "id": str(e.id),
                "from_status": e.from_status.value if e.from_status else None,
                "to_status": e.to_status.value,
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "note": e.note,
                "created_at": e.created_at,
            }
            for e in events
        ],
        "payment": {
            "method": payment.method.value,
            "amount": payment.amount,
            "status": payment.status.value,
            "provider_ref": payment.provider_ref,
            "paid_at": payment.paid_at,
        } if payment else None,
        "dispute": {
            "id": str(dispute.id),
            "reason": dispute.reason,
            "status": dispute.status.value,
            "resolution": dispute.resolution,
        } if dispute else None,
    }


@router.post("/orders/{order_id}/transition")
async def admin_intervene_order_status(
    order_id: str,
    payload: OrderInterventionTransitionRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-ADM-03: Admin changes order status via State Machine.
    Always validated by transition_order and writes order_events.
    """
    order = await db.get(Order, str(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")

    try:
        target_enum = OrderStatus(payload.target_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Trạng thái '{payload.target_status}' không hợp lệ.")

    note = f"[Admin can thiệp]: {payload.reason or 'Admin đổi trạng thái'}"
    await transition_order(
        db,
        order,
        target_enum,
        actor_id=current_user.id,
        note=note,
    )

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="order_status_intervened",
        entity_type="order",
        entity_id=str(order.id),
        detail={"to_status": target_enum.value, "reason": payload.reason},
    )
    await db.commit()

    return {
        "ok": True,
        "order_id": str(order.id),
        "status": order.status.value,
        "message": f"Đã chuyển trạng thái đơn hàng sang {order.status.value}.",
    }


@router.post("/orders/{order_id}/reassign")
async def admin_reassign_technician(
    order_id: str,
    payload: OrderInterventionReassignRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """FR-ADM-03: Admin manually reassigns order to another technician."""
    order = await db.get(Order, str(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")

    tech = await db.get(User, str(payload.technician_id))
    if not tech:
        raise HTTPException(status_code=404, detail="Không tìm thấy thợ được chỉ định.")

    old_tech_id = order.technician_id
    order.technician_id = tech.id
    order.accepted_at = datetime.now(timezone.utc)

    # Record event
    event = OrderEvent(
        id=str(uuid.uuid4()),
        order_id=order.id,
        from_status=order.status,
        to_status=order.status,
        actor_id=current_user.id,
        note=f"[Admin điều phối lại]: Gán sang thợ {tech.name or tech.phone}. Lý do: {payload.reason or 'Không có'}",
    )
    db.add(event)

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="order_reassigned",
        entity_type="order",
        entity_id=str(order.id),
        detail={"from_tech_id": old_tech_id, "to_tech_id": str(tech.id), "reason": payload.reason},
    )
    await db.commit()

    return {
        "ok": True,
        "order_id": str(order.id),
        "technician_id": str(tech.id),
        "message": f"Đã điều phối đơn hàng sang thợ {tech.name or tech.phone}.",
    }


@router.post("/orders/{order_id}/cancel")
async def admin_cancel_order(
    order_id: str,
    payload: OrderInterventionCancelRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """FR-ADM-03: Admin cancels order with reason via State Machine."""
    order = await db.get(Order, str(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")

    order.cancel_reason = f"[Admin hủy]: {payload.cancel_reason}"
    await transition_order(
        db,
        order,
        OrderStatus.CANCELLED,
        actor_id=current_user.id,
        note=order.cancel_reason,
    )

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="order_admin_cancelled",
        entity_type="order",
        entity_id=str(order.id),
        detail={"reason": payload.cancel_reason},
    )
    await db.commit()

    return {"ok": True, "order_id": str(order.id), "status": "CANCELLED", "message": "Đã hủy đơn hàng."}


@router.post("/orders/{order_id}/notes")
async def admin_add_order_note(
    order_id: str,
    payload: OrderInterventionNoteRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin adds internal note to order timeline."""
    order = await db.get(Order, str(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng.")

    event = OrderEvent(
        id=str(uuid.uuid4()),
        order_id=order.id,
        from_status=order.status,
        to_status=order.status,
        actor_id=current_user.id,
        note=f"[Ghi chú Admin]: {payload.note}",
    )
    db.add(event)

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="order_note_added",
        entity_type="order",
        entity_id=str(order.id),
        detail={"note": payload.note},
    )
    await db.commit()

    return {"ok": True, "message": "Đã thêm ghi chú nội bộ vào đơn hàng."}


# ── 5. Dispute Resolution & Refunds (UC-11, ADM-3) ───────────────────────────

@router.get("/disputes", response_model=DisputeListResponse)
async def admin_list_disputes(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """UC-11: List customer disputes."""
    stmt = select(Dispute).order_by(Dispute.created_at.desc())
    if status_filter:
        try:
            stmt = stmt.where(Dispute.status == DisputeStatus(status_filter))
        except ValueError:
            pass

    disputes = (await db.execute(stmt)).scalars().all()
    items = []
    for d in disputes:
        user = await db.get(User, d.opened_by_id)
        order = await db.get(Order, d.order_id)
        items.append(
            DisputeResponse(
                id=str(d.id),
                order_id=str(d.order_id),
                opened_by_id=str(d.opened_by_id),
                opened_by_phone=user.phone if user else None,
                opened_by_name=user.name if user else None,
                reason=d.reason,
                status=d.status.value,
                resolution=d.resolution,
                resolved_by_id=str(d.resolved_by_id) if d.resolved_by_id else None,
                resolved_at=d.resolved_at,
                created_at=d.created_at or datetime.now(timezone.utc),
                updated_at=d.updated_at or datetime.now(timezone.utc),
                order_total=order.total if order else None,
                order_code=str(order.id)[:8] if order else None,
            )
        )
    return DisputeListResponse(total=len(items), items=items)


@router.post("/disputes/{dispute_id}/resolve")
async def admin_resolve_dispute(
    dispute_id: str,
    payload: DisputeResolveRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    UC-11: Admin resolves dispute.
    If action == 'refund': transitions order to REFUNDED via State Machine.
    If action in ['reject', 'close']: marks dispute closed with explanation.
    """
    dispute = await db.get(Dispute, str(dispute_id))
    if not dispute:
        raise HTTPException(status_code=404, detail="Không tìm thấy khiếu nại.")

    order = await db.get(Order, dispute.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng của khiếu nại.")

    if payload.action == "refund":
        # Transition order to REFUNDED
        await transition_order(
            db,
            order,
            OrderStatus.REFUNDED,
            actor_id=current_user.id,
            note=f"[Admin duyệt hoàn tiền khiếu nại]: {payload.resolution_note}",
        )
        dispute.status = DisputeStatus.resolved
        dispute.resolution = f"Đã chấp thuận hoàn tiền: {payload.resolution_note}"
    elif payload.action in ("reject", "close"):
        dispute.status = DisputeStatus.closed
        dispute.resolution = f"Bác bỏ khiếu nại: {payload.resolution_note}"
    else:
        raise HTTPException(status_code=400, detail="Hành động giải quyết phải là 'refund', 'reject' hoặc 'close'.")

    dispute.resolved_by_id = current_user.id
    dispute.resolved_at = datetime.now(timezone.utc)

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action=f"dispute_{payload.action}",
        entity_type="dispute",
        entity_id=str(dispute.id),
        detail={"order_id": str(order.id), "resolution": dispute.resolution},
    )
    await db.commit()

    return {
        "ok": True,
        "dispute_id": str(dispute.id),
        "status": dispute.status.value,
        "order_status": order.status.value,
        "message": f"Đã giải quyết khiếu nại thành công: {dispute.resolution}",
    }


# ── 6. Platform Settings (FR-ADM-04) ─────────────────────────────────────────

@router.get("/settings", response_model=PlatformSettingsResponse)
async def admin_get_settings(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """FR-ADM-04: Get current platform configuration values."""
    comm = float(await get_config(db, "commission_rate", "0.10"))
    night = int(await get_config(db, "night_surcharge", "15000"))
    survey = int(await get_config(db, "survey_fee", "30000"))
    travel = int(await get_config(db, "travel_fee", "20000"))
    radius = float(await get_config(db, "emergency_radius_km", "3.0"))
    quota_anon = int(await get_config(db, "ai_daily_quota_anon", "2"))
    quota_user = int(await get_config(db, "ai_daily_quota_user", "10"))
    ai_budget = int(await get_config(db, "monthly_ai_budget_vnd", "5000000"))
    maps_budget = int(await get_config(db, "monthly_maps_budget_vnd", "3000000"))

    return PlatformSettingsResponse(
        commission_rate=comm,
        night_surcharge=night,
        survey_fee=survey,
        travel_fee=travel,
        emergency_radius_km=radius,
        ai_daily_quota_anon=quota_anon,
        ai_daily_quota_user=quota_user,
        monthly_ai_budget_vnd=ai_budget,
        monthly_maps_budget_vnd=maps_budget,
    )


@router.put("/settings", response_model=PlatformSettingsResponse)
async def admin_update_settings(
    payload: PlatformSettingsUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-ADM-04: Update platform settings.
    Effective for NEW orders only. Logs audit trail for every changed key.
    """
    changes = {}
    if payload.commission_rate is not None:
        await set_config(db, "commission_rate", str(payload.commission_rate), current_user.id)
        changes["commission_rate"] = payload.commission_rate
    if payload.night_surcharge is not None:
        await set_config(db, "night_surcharge", str(payload.night_surcharge), current_user.id)
        changes["night_surcharge"] = payload.night_surcharge
    if payload.survey_fee is not None:
        await set_config(db, "survey_fee", str(payload.survey_fee), current_user.id)
        changes["survey_fee"] = payload.survey_fee
    if payload.travel_fee is not None:
        await set_config(db, "travel_fee", str(payload.travel_fee), current_user.id)
        changes["travel_fee"] = payload.travel_fee
    if payload.emergency_radius_km is not None:
        await set_config(db, "emergency_radius_km", str(payload.emergency_radius_km), current_user.id)
        changes["emergency_radius_km"] = payload.emergency_radius_km
    if payload.ai_daily_quota_anon is not None:
        await set_config(db, "ai_daily_quota_anon", str(payload.ai_daily_quota_anon), current_user.id)
        changes["ai_daily_quota_anon"] = payload.ai_daily_quota_anon
    if payload.ai_daily_quota_user is not None:
        await set_config(db, "ai_daily_quota_user", str(payload.ai_daily_quota_user), current_user.id)
        changes["ai_daily_quota_user"] = payload.ai_daily_quota_user
    if payload.monthly_ai_budget_vnd is not None:
        await set_config(db, "monthly_ai_budget_vnd", str(payload.monthly_ai_budget_vnd), current_user.id)
        changes["monthly_ai_budget_vnd"] = payload.monthly_ai_budget_vnd
    if payload.monthly_maps_budget_vnd is not None:
        await set_config(db, "monthly_maps_budget_vnd", str(payload.monthly_maps_budget_vnd), current_user.id)
        changes["monthly_maps_budget_vnd"] = payload.monthly_maps_budget_vnd

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="platform_settings_updated",
        entity_type="platform_config",
        detail=changes,
    )
    await db.commit()

    return await admin_get_settings(current_user, db)


# ── 7. QR Location Manager (UC-12, FR-QR-01, FR-QR-02, AT-08) ────────────────

@router.get("/qr-locations", response_model=QRLocationListResponse)
async def admin_list_qr_locations(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """UC-12, AT-08: List all QR locations with scan and order metrics."""
    stmt = select(QRLocation).order_by(QRLocation.created_at.desc())
    locations = (await db.execute(stmt)).scalars().all()

    items = []
    for loc in locations:
        conv = round(loc.order_count / loc.scan_count * 100, 1) if loc.scan_count > 0 else 0.0
        items.append(
            QRLocationResponse(
                id=str(loc.id),
                code=loc.code,
                name=loc.name,
                location_type=loc.location_type,
                address=loc.address,
                lat=float(loc.lat) if loc.lat else None,
                lng=float(loc.lng) if loc.lng else None,
                owner_contact=loc.owner_contact,
                scan_count=loc.scan_count,
                order_count=loc.order_count,
                conversion_rate_pct=conv,
                is_active=loc.is_active,
                created_at=loc.created_at or datetime.now(timezone.utc),
                updated_at=loc.updated_at or datetime.now(timezone.utc),
                landing_url=f"/qr/{loc.code}",
            )
        )
    return QRLocationListResponse(total=len(items), items=items)


@router.post("/qr-locations", response_model=QRLocationResponse)
async def admin_create_qr_location(
    payload: QRLocationCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    UC-12, FR-QR-01, AT-08:
    Generate new printable QR location code (>= 10 random chars per A-03).
    """
    code = secrets.token_urlsafe(8)  # 11 characters base64url, entropy >= 10 chars per A-03

    loc = QRLocation(
        id=str(uuid.uuid4()),
        name=payload.name.strip(),
        location_type=payload.location_type,
        address=payload.address.strip(),
        lat=payload.lat,
        lng=payload.lng,
        owner_contact=payload.owner_contact,
        code=code,
        scan_count=0,
        order_count=0,
        is_active=True,
        created_by_id=current_user.id,
    )
    db.add(loc)
    await db.flush()

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="qr_location_created",
        entity_type="qr_location",
        entity_id=str(loc.id),
        detail={"code": loc.code, "name": loc.name, "address": loc.address},
    )
    await db.commit()

    return QRLocationResponse(
        id=str(loc.id),
        code=loc.code,
        name=loc.name,
        location_type=loc.location_type,
        address=loc.address,
        lat=float(loc.lat) if loc.lat else None,
        lng=float(loc.lng) if loc.lng else None,
        owner_contact=loc.owner_contact,
        scan_count=0,
        order_count=0,
        conversion_rate_pct=0.0,
        is_active=loc.is_active,
        created_at=loc.created_at or datetime.now(timezone.utc),
        updated_at=loc.updated_at or datetime.now(timezone.utc),
        landing_url=f"/qr/{loc.code}",
    )


@router.patch("/qr-locations/{id}", response_model=QRLocationResponse)
async def admin_update_qr_location(
    id: str,
    payload: QRLocationUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update QR location details or toggle active status."""
    loc = await db.get(QRLocation, str(id))
    if not loc:
        raise HTTPException(status_code=404, detail="Không tìm thấy điểm QR.")

    if payload.name is not None:
        loc.name = payload.name.strip()
    if payload.location_type is not None:
        loc.location_type = payload.location_type
    if payload.address is not None:
        loc.address = payload.address.strip()
    if payload.lat is not None:
        loc.lat = payload.lat
    if payload.lng is not None:
        loc.lng = payload.lng
    if payload.owner_contact is not None:
        loc.owner_contact = payload.owner_contact
    if payload.is_active is not None:
        loc.is_active = payload.is_active

    await log_admin_action(
        db,
        admin_id=current_user.id,
        action="qr_location_updated",
        entity_type="qr_location",
        entity_id=str(loc.id),
        detail={"name": loc.name, "is_active": loc.is_active},
    )
    await db.commit()

    conv = round(loc.order_count / loc.scan_count * 100, 1) if loc.scan_count > 0 else 0.0
    return QRLocationResponse(
        id=str(loc.id),
        code=loc.code,
        name=loc.name,
        location_type=loc.location_type,
        address=loc.address,
        lat=float(loc.lat) if loc.lat else None,
        lng=float(loc.lng) if loc.lng else None,
        owner_contact=loc.owner_contact,
        scan_count=loc.scan_count,
        order_count=loc.order_count,
        conversion_rate_pct=conv,
        is_active=loc.is_active,
        created_at=loc.created_at or datetime.now(timezone.utc),
        updated_at=loc.updated_at or datetime.now(timezone.utc),
        landing_url=f"/qr/{loc.code}",
    )


# ── 8. Admin Audit Trail (FR-ADM-01) ─────────────────────────────────────────

@router.get("/audit-logs", response_model=AdminActionLogListResponse)
async def admin_list_audit_logs(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """FR-ADM-01: View audit log of all admin interventions and changes."""
    stmt = (
        select(AdminActionLog)
        .order_by(AdminActionLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    logs = (await db.execute(stmt)).scalars().all()
    items = []
    for l in logs:
        admin_user = await db.get(User, l.admin_id)
        items.append(
            AdminActionLogResponse(
                id=str(l.id),
                admin_id=str(l.admin_id),
                admin_phone=admin_user.phone if admin_user else None,
                action=l.action,
                entity_type=l.entity_type,
                entity_id=l.entity_id,
                detail=l.detail,
                created_at=l.created_at or datetime.now(timezone.utc),
            )
        )

    total = (await db.execute(select(func.count(AdminActionLog.id)))).scalar() or 0
    return AdminActionLogListResponse(total=total, items=items)
