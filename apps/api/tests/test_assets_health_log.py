"""
Unit tests for Digital Health Log, Asset CRUD, and Maintenance Reminders.
FR-HEALTH-01, FR-HEALTH-02, FR-HEALTH-03, UC-09.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.models import (
    Asset,
    AssetType,
    ItemType,
    MaintenanceLog,
    Notification,
    Order,
    OrderItem,
    OrderStatus,
    User,
    UserRole,
    _uuid_default,
)
from app.routers.assets import create_asset, delete_asset
from app.schemas.assets import AssetCreate
from app.services.asset_service import (
    MAX_ASSETS_PER_USER,
    calculate_asset_health,
    check_duplicate_plate_or_serial,
    check_user_asset_count,
)
from app.services.auto_confirm import create_maintenance_log_for_order
from app.services.maintenance_reminders import check_and_send_maintenance_reminders


def test_asset_health_calculation_rules():
    """
    FR-HEALTH-03: Rule-based health status and reminders.
    - Vehicle: oil change at 90 days, general check at 180 days.
    - Appliance: periodic maintenance at 180 days.
    """
    now = datetime.now(timezone.utc)

    # 1. Fresh vehicle (10 days old) -> good health
    fresh_date = now - timedelta(days=10)
    status_fresh, rem_fresh = calculate_asset_health(AssetType.vehicle, fresh_date, None)
    assert status_fresh == "good"
    assert not any(r.is_overdue for r in rem_fresh)

    # 2. Overdue vehicle (95 days old) -> needs_maintenance (oil change overdue)
    overdue_date = now - timedelta(days=95)
    status_overdue, rem_overdue = calculate_asset_health(AssetType.vehicle, overdue_date, None)
    assert status_overdue == "needs_maintenance"
    oil_rem = next(r for r in rem_overdue if r.reminder_type == "oil_change")
    assert oil_rem.is_overdue is True

    # 3. Overdue appliance (200 days old) -> needs_maintenance
    appliance_date = now - timedelta(days=200)
    status_app, rem_app = calculate_asset_health(AssetType.appliance, appliance_date, None)
    assert status_app == "needs_maintenance"
    assert any(r.reminder_type == "cleaning_check" and r.is_overdue for r in rem_app)


@pytest.mark.asyncio
async def test_asset_creation_max_limit():
    """FR-HEALTH-01: User cannot exceed 10 assets."""
    mock_db = AsyncMock()
    customer = User(id=_uuid_default(), role=UserRole.customer, phone="0935111222")

    # Mock count = 10
    with patch("app.routers.assets.check_user_asset_count", return_value=10):
        req = AssetCreate(
            asset_type=AssetType.vehicle,
            brand="Honda",
            model="AirBlade",
            plate_or_serial="75F1-99999",
        )
        with pytest.raises(HTTPException) as exc:
            await create_asset(req, current_user=customer, db=mock_db)

        assert exc.value.status_code == 400
        assert exc.value.detail["error"]["code"] == "MAX_ASSETS_REACHED"


@pytest.mark.asyncio
async def test_asset_creation_duplicate_plate():
    """FR-HEALTH-01: Unique plate/serial per user."""
    mock_db = AsyncMock()
    customer = User(id=_uuid_default(), role=UserRole.customer, phone="0935111222")

    with patch("app.routers.assets.check_user_asset_count", return_value=3), \
         patch("app.routers.assets.check_duplicate_plate_or_serial", return_value=True):
        req = AssetCreate(
            asset_type=AssetType.vehicle,
            brand="Honda",
            model="Vision",
            plate_or_serial="75F1-12345",
        )
        with pytest.raises(HTTPException) as exc:
            await create_asset(req, current_user=customer, db=mock_db)

        assert exc.value.status_code == 409
        assert exc.value.detail["error"]["code"] == "DUPLICATE_PLATE_OR_SERIAL"


@pytest.mark.asyncio
async def test_order_completion_auto_creates_maintenance_log():
    """
    FR-HEALTH-02:
    Completed order generates MaintenanceLog linked to asset with parts and labor.
    """
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    order = MagicMock(spec=Order)
    order.id = _uuid_default()
    order.asset_id = "asset-uuid-123"
    order.technician_id = "tech-uuid-456"
    order.total = 180000
    order.items = [
        OrderItem(item_type=ItemType.labor, qty=1, unit_price=80000, name="Tiền công"),
        OrderItem(item_type=ItemType.part, qty=1, unit_price=100000, name="Bugi"),
    ]

    log = await create_maintenance_log_for_order(mock_db, order)
    assert log is not None
    assert log.asset_id == "asset-uuid-123"
    assert log.labor_cost == 80000
    assert log.parts_cost == 100000
    assert log.total_cost == 180000
    assert len(log.parts_replaced) == 1
    assert log.parts_replaced[0]["name"] == "Bugi"
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_maintenance_reminders_scanner():
    """
    FR-HEALTH-03:
    Scanner finds assets overdue for maintenance, creates Notification,
    and calls PushProvider.
    """
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    # Asset 100 days old
    old_date = datetime.now(timezone.utc) - timedelta(days=100)
    asset = MagicMock(spec=Asset)
    asset.id = "asset-lead-123"
    asset.owner_id = "user-owner-456"
    asset.asset_type = AssetType.vehicle
    asset.brand = "Honda"
    asset.model = "Lead 125"
    asset.created_at = old_date

    owner = MagicMock(spec=User)
    owner.id = "user-owner-456"
    owner.phone = "0935888777"

    # Setup DB mock returns
    mock_assets_res = MagicMock()
    mock_assets_res.scalars.return_value.all.return_value = [asset]

    mock_logs_res = MagicMock()
    mock_logs_res.scalars.return_value.first.return_value = None  # No prior logs

    mock_notif_res = MagicMock()
    mock_notif_res.scalar_one_or_none.return_value = None  # No notification in last 30d

    mock_db.execute.side_effect = [mock_assets_res, mock_logs_res, mock_notif_res]
    mock_db.get.return_value = owner

    with patch("app.services.maintenance_reminders.get_push_provider") as mock_get_push, \
         patch("app.services.maintenance_reminders.get_otp_provider") as mock_get_otp:
        push_mock = AsyncMock()
        push_mock.send_notification = AsyncMock(return_value=True)
        mock_get_push.return_value = push_mock

        otp_mock = AsyncMock()
        otp_mock.send_sms = AsyncMock(return_value=True)
        mock_get_otp.return_value = otp_mock

        count = await check_and_send_maintenance_reminders(mock_db)
        assert count >= 1
        mock_db.add.assert_called()
        push_mock.send_notification.assert_called()

