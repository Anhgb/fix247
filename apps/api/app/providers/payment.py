"""
Payment Provider interface + Mock implementation.
AGENTS.md: Every external service sits behind an interface with a mock
implementation that is the DEFAULT in dev.
FR-PAY-02: VietQR generation and webhook verification.
"""
from abc import ABC, abstractmethod
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class PaymentProvider(ABC):
    """Abstract payment provider interface."""

    @abstractmethod
    async def create_payment_request(
        self,
        order_id: str,
        amount: int,
        description: str,
    ) -> dict[str, Any]:
        """Generate payment instructions / VietQR payload."""
        ...

    @abstractmethod
    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify webhook signature from payment gateway."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Health check."""
        ...


class MockPaymentProvider(PaymentProvider):
    """
    Mock payment provider generating mock VietQR data and URLs.
    No live bank or gateway account required.
    """

    async def create_payment_request(
        self,
        order_id: str,
        amount: int,
        description: str,
    ) -> dict[str, Any]:
        # Formulate a mock VietQR URL or payload format
        bank_code = "MB"
        account_no = "FIX247HUE"
        # Standard format or SVG placeholder QR
        qr_url = f"https://api.vietqr.io/image/{bank_code}-{account_no}-compact2.png?amount={amount}&addInfo={description}"

        print(f"[PAYMENT-MOCK] 💳 Payment Request Created: Order {order_id} | Amount: {amount:,.0f} VND")  # noqa: T201
        logger.info(
            "mock_payment_created",
            order_id=order_id,
            amount=amount,
            description=description,
        )
        return {
            "order_id": order_id,
            "amount": amount,
            "currency": "VND",
            "provider_ref": f"mock_pay_{order_id[:8]}",
            "qr_url": qr_url,
            "account_name": "CONG TY TNHH FIX 247 HUẾ",
            "account_number": account_no,
            "bank_name": "Ngân hàng TMCP Quân Đội (MB)",
        }

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        # Mock provider accepts any valid non-empty mock signature or secret
        return bool(signature)

    async def is_available(self) -> bool:
        return True


def get_payment_provider() -> PaymentProvider:
    """Factory: returns correct provider based on settings."""
    from app.core.config import get_settings

    settings = get_settings()
    if settings.provider_payment == "mock":
        return MockPaymentProvider()
    raise NotImplementedError(f"Payment provider '{settings.provider_payment}' not yet implemented")
