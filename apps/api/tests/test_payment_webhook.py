"""
Unit tests for Payment Webhook and Idempotency.
FR-PAY-02, AT-06.
Webhook sending twice records only once (idempotent by provider_ref).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import Order, OrderStatus, Payment, PaymentMethod, PaymentStatus, _uuid_default
from app.routers.payments import payment_gateway_webhook
from app.schemas.payments import PaymentWebhookPayload


@pytest.mark.asyncio
async def test_webhook_idempotency_at_06():
    """
    AT-06: Webhook sent twice with same provider_ref is recorded only once.
    Second call returns already_processed without re-transitioning or duplicate commission.
    """
    mock_db = AsyncMock()

    # Pre-existing completed payment with this provider_ref
    existing_payment = MagicMock(spec=Payment)
    existing_payment.provider_ref = "vietqr_tx_999888"
    existing_payment.status = PaymentStatus.completed
    existing_payment.amount = 250000

    # DB returns existing payment
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_payment
    mock_db.execute = AsyncMock(return_value=mock_result)

    payload = PaymentWebhookPayload(
        provider_ref="vietqr_tx_999888",
        order_id="order-uuid-123",
        amount=250000,
        status="completed",
        signature="valid_mock_signature",
    )

    with patch("app.routers.payments.get_payment_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.verify_webhook_signature = AsyncMock(return_value=True)
        mock_get_provider.return_value = mock_provider

        response = await payment_gateway_webhook(payload, db=mock_db)

        # Idempotent response
        assert response["status"] == "already_processed"
        assert response["provider_ref"] == "vietqr_tx_999888"
        # No DB additions or commits happened
        mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_first_processing_succeeds():
    """First webhook call updates payment to completed and transitions order."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    # First lookup (by provider_ref): None
    payment_lookup = MagicMock()
    payment_lookup.scalar_one_or_none.return_value = None

    # Second lookup (order): Order in AWAITING_CONFIRM
    mock_order = MagicMock(spec=Order)
    mock_order.id = _uuid_default()
    mock_order.status = OrderStatus.AWAITING_CONFIRM
    mock_order.technician_id = "tech-1"
    mock_order.items = []
    mock_order.night_surcharge = 0
    mock_order.total = 200000
    mock_order.asset_id = None

    order_lookup = MagicMock()
    order_lookup.scalar_one_or_none.return_value = mock_order

    # Profile lookup
    mock_profile = MagicMock()
    mock_profile.total_earned = 0
    mock_profile.debt_amount = 0
    profile_lookup = MagicMock()
    profile_lookup.scalar_one_or_none.return_value = mock_profile

    mock_db.execute = AsyncMock(side_effect=[payment_lookup, order_lookup, profile_lookup])

    payload = PaymentWebhookPayload(
        provider_ref="vietqr_tx_first_call",
        order_id=str(mock_order.id),
        amount=200000,
        status="completed",
        signature="valid_signature",
    )

    with patch("app.routers.payments.get_payment_provider") as mock_get_provider, \
         patch("app.routers.payments.transition_order", new_callable=AsyncMock) as mock_transition, \
         patch("app.routers.payments.get_config", new_callable=AsyncMock, return_value="0.10"), \
         patch("app.routers.payments.create_maintenance_log_for_order", new_callable=AsyncMock):

        mock_provider = AsyncMock()
        mock_provider.verify_webhook_signature = AsyncMock(return_value=True)
        mock_get_provider.return_value = mock_provider

        resp = await payment_gateway_webhook(payload, db=mock_db)

        assert resp["status"] == "success"
        assert resp["amount"] == 200000
        mock_transition.assert_called_once()
