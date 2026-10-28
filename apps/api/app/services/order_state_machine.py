"""
Canonical order state machine – Fix 24/7.
AGENTS.md: Order status changes ONLY go through this module.
SRS §6: Every transition writes order_events + publishes Redis event.
"""
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models import OrderEvent, OrderStatus, _uuid_default


# ── Transition table (SRS §6) ─────────────────────────────────────────────────
VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED: {OrderStatus.SEARCHING, OrderStatus.SCHEDULED, OrderStatus.CANCELLED},
    OrderStatus.SEARCHING: {OrderStatus.ACCEPTED, OrderStatus.NO_TECH, OrderStatus.CANCELLED},
    OrderStatus.SCHEDULED: {OrderStatus.ON_THE_WAY, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.ON_THE_WAY, OrderStatus.CANCELLED},
    OrderStatus.ON_THE_WAY: {OrderStatus.SURVEYING, OrderStatus.CANCELLED},
    OrderStatus.SURVEYING: {OrderStatus.QUOTE_PENDING},
    OrderStatus.QUOTE_PENDING: {OrderStatus.IN_REPAIR, OrderStatus.QUOTE_REJECTED},
    OrderStatus.QUOTE_REJECTED: {OrderStatus.CLOSED},
    OrderStatus.IN_REPAIR: {OrderStatus.AWAITING_CONFIRM},
    OrderStatus.AWAITING_CONFIRM: {OrderStatus.COMPLETED, OrderStatus.DISPUTED},
    OrderStatus.COMPLETED: {OrderStatus.WARRANTY},
    OrderStatus.DISPUTED: {OrderStatus.COMPLETED, OrderStatus.REFUNDED, OrderStatus.CLOSED},
    OrderStatus.NO_TECH: {OrderStatus.SEARCHING, OrderStatus.CANCELLED},
    # Terminal states
    OrderStatus.WARRANTY: set(),
    OrderStatus.CANCELLED: set(),
    OrderStatus.CLOSED: set(),
    OrderStatus.REFUNDED: set(),
}


class InvalidTransitionError(Exception):
    """Raised when a requested status transition is not allowed. SRS AT-10."""

    def __init__(self, from_status: OrderStatus, to_status: OrderStatus) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Không thể chuyển trạng thái từ {from_status.value} sang {to_status.value}"
        )


async def transition_order(
    db: AsyncSession,
    order,  # app.models.Order – avoid circular import
    to_status: OrderStatus,
    actor_id: str | None = None,
    note: str | None = None,
):
    """
    Single canonical function to change an order's status.
    AGENTS.md: Order status changes only go through this state-machine function.

    Steps:
      1. Validate transition against VALID_TRANSITIONS.
      2. Update order.status.
      3. Write OrderEvent row.
      4. Publish Redis event to channel order:{order_id}.
      5. Return updated order.

    Raises InvalidTransitionError if the transition is not permitted.
    """
    from_status: OrderStatus = order.status

    # 1. Validate
    allowed = VALID_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise InvalidTransitionError(from_status, to_status)

    # 2. Update order status
    order.status = to_status

    # 3. Write event
    event = OrderEvent(
        id=_uuid_default(),
        order_id=order.id,
        from_status=from_status,
        to_status=to_status,
        actor_id=actor_id,
        note=note,
    )
    db.add(event)
    await db.flush()  # persist before Redis publish

    # 4. Publish to Redis pub/sub channel
    try:
        redis = await get_redis()
        payload = json.dumps({"type": "status", "status": to_status.value})
        await redis.publish(f"order:{order.id}", payload)
    except Exception:
        # Redis failure must not roll back the DB transaction
        pass

    return order
