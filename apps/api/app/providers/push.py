"""
Push Notification Provider interface + Mock implementation.
AGENTS.md: Every external service sits behind an interface with a mock
implementation that is the DEFAULT in dev.
"""
from abc import ABC, abstractmethod
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class PushProvider(ABC):
    """Abstract push notification provider interface."""

    @abstractmethod
    async def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send push notification to user's registered device."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Health check."""
        ...


class MockPushProvider(PushProvider):
    """
    Mock push notification provider for development.
    Logs notifications to console and logger without requiring Firebase/WebPush credentials.
    """

    async def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        print(f"[PUSH-MOCK] 🔔 To User {user_id[:8]}... | {title}: {body}")  # noqa: T201
        logger.info(
            "push_notification_mock_sent",
            user_id=user_id,
            title=title,
            data=data or {},
        )
        return True

    async def is_available(self) -> bool:
        return True


def get_push_provider() -> PushProvider:
    """Factory: returns correct provider based on settings."""
    from app.core.config import get_settings

    settings = get_settings()
    if settings.provider_push == "mock":
        return MockPushProvider()
    raise NotImplementedError(f"Push provider '{settings.provider_push}' not yet implemented")
