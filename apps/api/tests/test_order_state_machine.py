"""
Unit tests for Order State Machine (SRS §6, AT-10).
Tests all valid transitions, all invalid transitions, and event logging.
Pure unit tests with mock DB and Redis.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import Order, OrderEvent, OrderStatus, _uuid_default
from app.services.order_state_machine import (
    VALID_TRANSITIONS,
    InvalidTransitionError,
    transition_order,
)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def sample_order():
    order = MagicMock(spec=Order)
    order.id = _uuid_default()
    order.status = OrderStatus.CREATED
    return order


# ── Test All Valid Transitions ────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "from_status,to_status",
    [
        (OrderStatus.CREATED, OrderStatus.SEARCHING),
        (OrderStatus.CREATED, OrderStatus.SCHEDULED),
        (OrderStatus.CREATED, OrderStatus.CANCELLED),
        (OrderStatus.SEARCHING, OrderStatus.ACCEPTED),
        (OrderStatus.SEARCHING, OrderStatus.NO_TECH),
        (OrderStatus.SEARCHING, OrderStatus.CANCELLED),
        (OrderStatus.SCHEDULED, OrderStatus.ON_THE_WAY),
        (OrderStatus.SCHEDULED, OrderStatus.CANCELLED),
        (OrderStatus.ACCEPTED, OrderStatus.ON_THE_WAY),
        (OrderStatus.ACCEPTED, OrderStatus.CANCELLED),
        (OrderStatus.ON_THE_WAY, OrderStatus.SURVEYING),
        (OrderStatus.ON_THE_WAY, OrderStatus.CANCELLED),
        (OrderStatus.SURVEYING, OrderStatus.QUOTE_PENDING),
        (OrderStatus.QUOTE_PENDING, OrderStatus.IN_REPAIR),
        (OrderStatus.QUOTE_PENDING, OrderStatus.QUOTE_REJECTED),
        (OrderStatus.QUOTE_REJECTED, OrderStatus.CLOSED),
        (OrderStatus.IN_REPAIR, OrderStatus.AWAITING_CONFIRM),
        (OrderStatus.AWAITING_CONFIRM, OrderStatus.COMPLETED),
        (OrderStatus.AWAITING_CONFIRM, OrderStatus.DISPUTED),
        (OrderStatus.COMPLETED, OrderStatus.WARRANTY),
        (OrderStatus.DISPUTED, OrderStatus.COMPLETED),
        (OrderStatus.DISPUTED, OrderStatus.REFUNDED),
        (OrderStatus.DISPUTED, OrderStatus.CLOSED),
        (OrderStatus.NO_TECH, OrderStatus.SEARCHING),
        (OrderStatus.NO_TECH, OrderStatus.CANCELLED),
    ],
)
async def test_valid_transitions(mock_db, sample_order, from_status, to_status):
    """Test that all transitions defined in SRS §6 table succeed."""
    sample_order.status = from_status

    with patch("app.services.order_state_machine.get_redis", new_callable=AsyncMock) as mock_get_redis:
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        updated_order = await transition_order(
            db=mock_db,
            order=sample_order,
            to_status=to_status,
            actor_id="user-123",
            note="Testing transition",
        )

        assert updated_order.status == to_status
        # Event was written
        mock_db.add.assert_called_once()
        added_event = mock_db.add.call_args[0][0]
        assert isinstance(added_event, OrderEvent)
        assert added_event.from_status == from_status
        assert added_event.to_status == to_status
        assert added_event.actor_id == "user-123"
        # Redis publish was attempted
        mock_redis.publish.assert_called_once()


# ── Test Invalid Transitions (AT-10) ──────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "from_status,invalid_to_status",
    [
        (OrderStatus.CREATED, OrderStatus.COMPLETED),
        (OrderStatus.CREATED, OrderStatus.IN_REPAIR),
        (OrderStatus.SEARCHING, OrderStatus.IN_REPAIR),
        (OrderStatus.SEARCHING, OrderStatus.COMPLETED),
        (OrderStatus.ACCEPTED, OrderStatus.COMPLETED),
        (OrderStatus.ACCEPTED, OrderStatus.QUOTE_PENDING),
        (OrderStatus.ON_THE_WAY, OrderStatus.IN_REPAIR),
        (OrderStatus.ON_THE_WAY, OrderStatus.COMPLETED),
        (OrderStatus.SURVEYING, OrderStatus.IN_REPAIR),  # Must go through QUOTE_PENDING
        (OrderStatus.SURVEYING, OrderStatus.COMPLETED),
        (OrderStatus.QUOTE_PENDING, OrderStatus.COMPLETED),
        (OrderStatus.QUOTE_REJECTED, OrderStatus.IN_REPAIR),
        (OrderStatus.IN_REPAIR, OrderStatus.COMPLETED),  # Must go through AWAITING_CONFIRM
        (OrderStatus.IN_REPAIR, OrderStatus.CANCELLED),
        (OrderStatus.AWAITING_CONFIRM, OrderStatus.IN_REPAIR),
        (OrderStatus.COMPLETED, OrderStatus.SEARCHING),  # AT-10 explicit requirement
        (OrderStatus.COMPLETED, OrderStatus.CREATED),
        (OrderStatus.CANCELLED, OrderStatus.SEARCHING),  # Terminal state
        (OrderStatus.CANCELLED, OrderStatus.CREATED),
        (OrderStatus.CLOSED, OrderStatus.CREATED),
        (OrderStatus.CLOSED, OrderStatus.SEARCHING),
        (OrderStatus.REFUNDED, OrderStatus.COMPLETED),
        (OrderStatus.WARRANTY, OrderStatus.IN_REPAIR),
    ],
)
async def test_invalid_transitions(mock_db, sample_order, from_status, invalid_to_status):
    """SRS AT-10: Invalid transitions must raise InvalidTransitionError."""
    sample_order.status = from_status

    with pytest.raises(InvalidTransitionError) as exc_info:
        await transition_order(
            db=mock_db,
            order=sample_order,
            to_status=invalid_to_status,
        )

    assert exc_info.value.from_status == from_status
    assert exc_info.value.to_status == invalid_to_status
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_terminal_states_reject_all(mock_db, sample_order):
    """Terminal states CANCELLED, CLOSED, REFUNDED, WARRANTY reject all transitions."""
    terminal_statuses = [
        OrderStatus.CANCELLED,
        OrderStatus.CLOSED,
        OrderStatus.REFUNDED,
        OrderStatus.WARRANTY,
    ]
    all_statuses = list(OrderStatus)

    for term in terminal_statuses:
        sample_order.status = term
        for target in all_statuses:
            with pytest.raises(InvalidTransitionError):
                await transition_order(mock_db, sample_order, target)

