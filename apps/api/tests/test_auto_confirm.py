"""
Unit tests for 24-Hour Auto-Confirm Job (AT-05, BR-08, FR-PAY-04).
Orders awaiting customer confirmation for >24h without dispute are automatically COMPLETED.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import Asset, AssetType, ItemType, Order, OrderItem, OrderStatus, _uuid_default
from app.services.auto_confirm import auto_confirm_expired_orders, create_maintenance_log_for_order


@pytest.mark.asyncio
async def test_auto_confirm_after_24h_at_05():
    """
    AT-05: Customer does not confirm after 24h -> Auto COMPLETED + health log.
    """
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.flush = AsyncMock()

    now = datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc)
    twenty_five_hours_ago = now - timedelta(hours=25)

    expired_order = MagicMock(spec=Order)
    expired_order.id = _uuid_default()
    expired_order.status = OrderStatus.AWAITING_CONFIRM
    expired_order.updated_at = twenty_five_hours_ago
    expired_order.technician_id = "tech-007"
    expired_order.asset_id = "asset-001"
    expired_order.total = 300000
    expired_order.night_surcharge = 0
    expired_order.items = [
        OrderItem(item_type=ItemType.labor, qty=1, unit_price=100000, name="Tiền công"),
        OrderItem(item_type=ItemType.part, qty=1, unit_price=200000, name="Linh kiện"),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [expired_order]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.auto_confirm.transition_order", new_callable=AsyncMock) as mock_transition, \
         patch("app.services.auto_confirm.create_maintenance_log_for_order", new_callable=AsyncMock) as mock_log, \
         patch("app.services.auto_confirm.record_order_commission", new_callable=AsyncMock) as mock_comm:

        confirmed_ids = await auto_confirm_expired_orders(mock_db, cutoff_hours=24, now=now)

        assert len(confirmed_ids) == 1
        assert confirmed_ids[0] == str(expired_order.id)
        mock_transition.assert_called_once()
        mock_log.assert_called_once()
        mock_comm.assert_called_once()


@pytest.mark.asyncio
async def test_create_maintenance_log_structure():
    """FR-HEALTH-02: Auto-creates maintenance log with parts and costs."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    order = MagicMock(spec=Order)
    order.id = _uuid_default()
    order.asset_id = "asset-xyz"
    order.technician_id = "tech-123"
    order.total = 250000
    order.items = [
        OrderItem(item_type=ItemType.labor, qty=1, unit_price=100000, name="Công thợ"),
        OrderItem(item_type=ItemType.part, qty=1, unit_price=150000, name="Dây curoa"),
    ]

    log = await create_maintenance_log_for_order(mock_db, order)

    assert log is not None
    assert log.asset_id == "asset-xyz"
    assert log.labor_cost == 100000
    assert log.parts_cost == 150000
    assert len(log.parts_replaced) == 1
    assert log.parts_replaced[0]["name"] == "Dây curoa"
    mock_db.add.assert_called_once()

