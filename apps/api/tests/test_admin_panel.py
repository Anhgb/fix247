"""
Unit Tests for Phase P5: Admin Panel, QR Locations, Analytics (UC-10, UC-11, UC-12, FR-ADM, FR-QR)
Acceptance: AT-07, AT-08.
"""
import io
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
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
    QRLocation,
    ServiceCategory,
    ServiceGroup,
    TechnicianProfile,
    User,
    UserRole,
    Diagnosis,
    VerifiedLabel,
)
from app.schemas.admin import (
    DisputeResolveRequest,
    FaultCatalogCreate,
    FaultCatalogUpdate,
    OrderInterventionCancelRequest,
    OrderInterventionReassignRequest,
    OrderInterventionTransitionRequest,
    PlatformSettingsUpdate,
)
from app.schemas.qr import QRLocationCreate, QRLocationUpdate
from app.schemas.technician import TechApprovalRequest
from app.routers.admin import (
    admin_approve_technician,
    admin_create_fault_catalog,
    admin_create_qr_location,
    admin_get_order_detail,
    admin_get_settings,
    admin_import_fault_catalog_csv,
    admin_intervene_order_status,
    admin_list_disputes,
    admin_list_fault_catalog,
    admin_list_orders,
    admin_list_qr_locations,
    admin_list_technicians,
    admin_reassign_technician,
    admin_reject_technician,
    admin_resolve_dispute,
    admin_suspend_technician,
    admin_update_fault_catalog,
    admin_update_qr_location,
    admin_update_settings,
    get_admin_dashboard_stats,
)
from app.routers.qr import resolve_qr_code


def _make_admin_user() -> User:
    return User(
        id=str(uuid4()),
        phone="0900000000",
        name="Admin Test",
        role=UserRole.admin,
        status="active",
    )


def _make_customer_user() -> User:
    return User(
        id=str(uuid4()),
        phone="0905123456",
        name="Khách Hàng Test",
        role=UserRole.customer,
        status="active",
    )


# ── Test 1: Dashboard Stats Calculation (UC-10, FR-ADM-01) ────────────────────

@pytest.mark.asyncio
async def test_admin_dashboard_stats():
    admin = _make_admin_user()
    db = AsyncMock()

    # Mock scalar executions
    # 1. orders_total = 10
    # 2. orders_today = 3
    # 3. gmv_total = 1500000
    # 4. gmv_today = 450000
    # 5. commission_total = 150000
    # 6. completed_count = 8
    # 7. disputes_count = 1
    # 8. times query: 1 record with 120s duration
    # 9. ai_calls_total = 25
    # 10. daily_ai_calls = 5
    # 11. monthly_ai_calls = 20
    # 12. maps_monthly_orders = 10

    mock_res_total = MagicMock()
    mock_res_total.scalar.return_value = 10

    mock_res_today = MagicMock()
    mock_res_today.scalar.return_value = 3

    mock_res_gmv = MagicMock()
    mock_res_gmv.scalar.return_value = 1500000

    mock_res_gmv_today = MagicMock()
    mock_res_gmv_today.scalar.return_value = 450000

    mock_res_comm = MagicMock()
    mock_res_comm.scalar.return_value = 150000

    mock_res_comp = MagicMock()
    mock_res_comp.scalar.return_value = 8

    mock_res_disp = MagicMock()
    mock_res_disp.scalar.return_value = 1

    t1 = datetime(2026, 10, 28, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 28, 10, 2, 0, tzinfo=timezone.utc)
    mock_res_times = MagicMock()
    mock_res_times.all.return_value = [(t1, t2)]

    mock_res_ai_total = MagicMock()
    mock_res_ai_total.scalar.return_value = 25

    d1 = Diagnosis(id=str(uuid4()), verified_label=VerifiedLabel.correct)
    d2 = Diagnosis(id=str(uuid4()), verified_label=VerifiedLabel.partial)
    mock_res_diag = MagicMock()
    mock_res_diag.scalars.return_value.all.return_value = [d1, d2]

    mock_res_ai_daily = MagicMock()
    mock_res_ai_daily.scalar.return_value = 5

    mock_res_ai_monthly = MagicMock()
    mock_res_ai_monthly.scalar.return_value = 20

    mock_res_maps_monthly = MagicMock()
    mock_res_maps_monthly.scalar.return_value = 10

    db.execute.side_effect = [
        mock_res_total,
        mock_res_today,
        mock_res_gmv,
        mock_res_gmv_today,
        mock_res_comm,
        mock_res_comp,
        mock_res_disp,
        mock_res_times,
        mock_res_ai_total,
        mock_res_diag,
        mock_res_ai_daily,
        mock_res_ai_monthly,
        mock_res_maps_monthly,
    ]

    with patch("app.routers.admin.get_config", AsyncMock(side_effect=["5000000", "3000000"])):
        stats = await get_admin_dashboard_stats(current_user=admin, db=db)

    assert stats.orders_total == 10
    assert stats.orders_today == 3
    assert stats.gmv_total == 1500000
    assert stats.commission_total == 150000
    assert stats.completion_rate_pct == 80.0
    assert stats.dispute_rate_pct == 10.0
    assert stats.median_time_to_accept_sec == 120
    # (1.0 + 0.5) / 2 * 100 = 75.0%
    assert stats.ai_top3_accuracy_pct == 75.0
    assert stats.ai_budget_alert is False


# ── Test 2: Technician Review Queue & AT-07 ───────────────────────────────────

@pytest.mark.asyncio
async def test_admin_technician_approval_and_suspension_at_07():
    admin = _make_admin_user()
    tech_user_id = str(uuid4())
    db = AsyncMock()

    profile = TechnicianProfile(
        id=str(uuid4()),
        user_id=tech_user_id,
        id_number_encrypted="ENCRYPTED_CCCD",
        approval_status=ApprovalStatus.pending,
        is_online=False,
    )
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = profile
    db.execute.return_value = mock_scalar

    # 1. Approve
    appr_res = await admin_approve_technician(
        tech_user_id=tech_user_id,
        payload=TechApprovalRequest(note="Hồ sơ hợp lệ"),
        current_user=admin,
        db=db,
    )
    assert appr_res["ok"] is True
    assert profile.approval_status == ApprovalStatus.approved
    assert profile.approved_by_id == admin.id

    # 2. Suspend with reason
    db.execute.return_value = mock_scalar
    susp_res = await admin_suspend_technician(
        tech_user_id=tech_user_id,
        payload=TechApprovalRequest(note="Khách phản ánh thái độ không đúng mực"),
        current_user=admin,
        db=db,
    )
    assert susp_res["ok"] is True
    assert profile.approval_status == ApprovalStatus.suspended
    assert profile.is_online is False
    assert "Khách phản ánh" in profile.approval_note


# ── Test 3: Fault Catalog CRUD & Versioning (FR-ADM-02) ────────────────────────

@pytest.mark.asyncio
async def test_fault_catalog_crud_and_versioning():
    admin = _make_admin_user()
    db = AsyncMock()

    # 1. Create Catalog Item
    mock_dup = MagicMock()
    mock_dup.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_dup

    cat_id = str(uuid4())
    cat = ServiceCategory(id=cat_id, name="Xe máy", group=ServiceGroup.motorbike)
    db.get.return_value = cat

    res_create = await admin_create_fault_catalog(
        payload=FaultCatalogCreate(
            category_id=cat_id,
            fault_code="MOTO_PUNC_NEW",
            name="Vá xăm xe số lưu động",
            labor_min=30000,
            labor_max=50000,
            parts_min=0,
            parts_max=20000,
        ),
        current_user=admin,
        db=db,
    )
    assert res_create.fault_code == "MOTO_PUNC_NEW"
    assert res_create.version == 1

    # 2. Update Catalog Item -> Version must increment to 2
    fc_item = FaultCatalog(
        id=res_create.id,
        category_id=cat_id,
        fault_code="MOTO_PUNC_NEW",
        name="Vá xăm xe số lưu động",
        labor_min=30000,
        labor_max=50000,
        version=1,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.get.side_effect = [fc_item, cat]

    res_update = await admin_update_fault_catalog(
        id=res_create.id,
        payload=FaultCatalogUpdate(labor_max=60000),
        current_user=admin,
        db=db,
    )
    assert res_update.labor_max == 60000
    assert res_update.version == 2


# ── Test 4: Fault Catalog CSV Bulk Import (FR-ADM-02) ─────────────────────────

@pytest.mark.asyncio
async def test_fault_catalog_csv_import():
    admin = _make_admin_user()
    db = AsyncMock()

    csv_data = (
        "fault_code,name,labor_min,labor_max,parts_min,parts_max,safety_notes\n"
        "MOTO_CHAIN_01,Tăng xích và bôi trơn,20000,40000,0,0,Tránh kẹt tay vào đĩa xích\n"
        "AC_FILTER_01,Vệ sinh lưới lọc bụi,50000,80000,0,0,Ngắt nguồn điện trước khi làm\n"
    )
    upload_file = MagicMock()
    upload_file.read = AsyncMock(return_value=csv_data.encode("utf-8"))
    upload_file.filename = "fault_catalog_2026.csv"

    mock_cats = MagicMock()
    mock_cats.scalars.return_value.all.return_value = [ServiceCategory(id=str(uuid4()), name="Test")]

    mock_existing = MagicMock()
    mock_existing.scalar_one_or_none.return_value = None

    db.execute.side_effect = [mock_cats, mock_existing, mock_existing]

    res = await admin_import_fault_catalog_csv(file=upload_file, current_user=admin, db=db)
    assert res["ok"] is True
    assert res["created_count"] == 2
    assert res["updated_count"] == 0


# ── Test 5: Order Explorer & Interventions (FR-ADM-03) ────────────────────────

@pytest.mark.asyncio
async def test_order_interventions():
    admin = _make_admin_user()
    db = AsyncMock()

    order = Order(
        id=str(uuid4()),
        customer_id=str(uuid4()),
        technician_id=str(uuid4()),
        mode=OrderMode.emergency,
        status=OrderStatus.SEARCHING,
        address="123 Hùng Vương, Huế",
    )
    db.get.return_value = order

    # 1. State machine transition via intervention
    with patch("app.routers.admin.transition_order", AsyncMock()) as mock_trans:
        res = await admin_intervene_order_status(
            order_id=order.id,
            payload=OrderInterventionTransitionRequest(
                target_status="NO_TECH",
                reason="Không có thợ trong bán kính mở rộng 5km",
            ),
            current_user=admin,
            db=db,
        )
        assert res["ok"] is True
        mock_trans.assert_called_once()

    # 2. Reassign technician
    new_tech = User(id=str(uuid4()), phone="0908888888", name="Thợ mới", role=UserRole.technician)
    db.get.side_effect = [order, new_tech]

    reassign_res = await admin_reassign_technician(
        order_id=order.id,
        payload=OrderInterventionReassignRequest(technician_id=new_tech.id, reason="Thợ cũ hỏng xe"),
        current_user=admin,
        db=db,
    )
    assert reassign_res["ok"] is True
    assert order.technician_id == new_tech.id


# ── Test 6: Dispute Resolution & Refund (UC-11) ───────────────────────────────

@pytest.mark.asyncio
async def test_dispute_resolution_refund():
    admin = _make_admin_user()
    db = AsyncMock()

    order = Order(
        id=str(uuid4()),
        customer_id=str(uuid4()),
        technician_id=str(uuid4()),
        mode=OrderMode.emergency,
        status=OrderStatus.DISPUTED,
        total=250000,
        address="Huế",
    )
    dispute = Dispute(
        id=str(uuid4()),
        order_id=order.id,
        opened_by_id=order.customer_id,
        reason="Thợ sửa xong xe vẫn không nổ máy được",
        status=DisputeStatus.open,
    )
    db.get.side_effect = [dispute, order]

    with patch("app.routers.admin.transition_order", AsyncMock()) as mock_trans:
        res = await admin_resolve_dispute(
            dispute_id=dispute.id,
            payload=DisputeResolveRequest(action="refund", resolution_note="Chấp nhận hoàn tiền 100% cho khách"),
            current_user=admin,
            db=db,
        )
        assert res["ok"] is True
        assert dispute.status == DisputeStatus.resolved
        assert "Chấp nhận hoàn tiền" in dispute.resolution
        mock_trans.assert_called_once()


# ── Test 7: QR Location Creation & Public Landing (UC-12, AT-08) ──────────────

@pytest.mark.asyncio
async def test_qr_location_creation_and_scan_at_08():
    admin = _make_admin_user()
    db = AsyncMock()

    # 1. Admin creates QR location
    res_qr = await admin_create_qr_location(
        payload=QRLocationCreate(
            name="KTX Đại học Khoa học Huế",
            location_type="Ký túc xá",
            address="Số 77 Nguyễn Huệ, TP. Huế",
            lat=16.4637,
            lng=107.5909,
            owner_contact="Ban quản lý KTX",
        ),
        current_user=admin,
        db=db,
    )
    # Code must be >= 10 chars (A-03, token_urlsafe(8) is 11 chars)
    assert len(res_qr.code) >= 10
    assert res_qr.name == "KTX Đại học Khoa học Huế"
    assert res_qr.landing_url == f"/qr/{res_qr.code}"

    # 2. Customer scans QR code -> increments scan_count
    loc_record = QRLocation(
        id=res_qr.id,
        code=res_qr.code,
        name=res_qr.name,
        location_type=res_qr.location_type,
        address=res_qr.address,
        lat=res_qr.lat,
        lng=res_qr.lng,
        scan_count=0,
        order_count=0,
        is_active=True,
    )
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = loc_record
    db.execute.return_value = mock_scalar

    pub_res = await resolve_qr_code(code=res_qr.code, db=db)
    assert pub_res.name == "KTX Đại học Khoa học Huế"
    assert pub_res.address == "Số 77 Nguyễn Huệ, TP. Huế"
    assert loc_record.scan_count == 1

    # 3. Invalid QR code -> returns 404
    mock_scalar_none = MagicMock()
    mock_scalar_none.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_scalar_none

    with pytest.raises(HTTPException) as exc_info:
        await resolve_qr_code(code="INVALID_CODE_123", db=db)
    assert exc_info.value.status_code == 404

