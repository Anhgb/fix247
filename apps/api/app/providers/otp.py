"""
OTP Provider interface + Mock implementation.
AGENTS.md: Every external service sits behind an interface with a mock
implementation that is the DEFAULT in dev.
D-02: Mock prints OTP to stdout with [OTP-MOCK] prefix.
"""
import random
import time
from abc import ABC, abstractmethod

from app.core.logging import get_logger

logger = get_logger(__name__)


class OTPProvider(ABC):
    """Abstract OTP provider interface."""

    @abstractmethod
    async def send_otp(self, phone: str, otp: str) -> bool:
        """Send OTP to phone number. Returns True if sent successfully."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Health check."""
        ...


class MockOTPProvider(OTPProvider):
    """
    Mock OTP provider for development.
    Prints OTP to console — no SMS API needed.
    D-02: prefix [OTP-MOCK].
    """

    async def send_otp(self, phone: str, otp: str) -> bool:
        # NEVER log phone number in production (AGENTS.md: never log PII)
        print(f"[OTP-MOCK] ☎️  {phone[:3]}****{phone[-3:]} → OTP: {otp}")  # noqa: T201
        logger.info("otp_sent_mock", phone_suffix=phone[-4:])
        return True

    async def is_available(self) -> bool:
        return True


def generate_otp() -> str:
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))


def get_otp_provider() -> OTPProvider:
    """Factory: returns correct provider based on settings."""
    from app.core.config import get_settings

    settings = get_settings()
    if settings.provider_otp == "mock":
        return MockOTPProvider()
    raise NotImplementedError(f"OTP provider '{settings.provider_otp}' not yet implemented")
