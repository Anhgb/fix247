"""
Provider interfaces and factories for external services.
AGENTS.md: Every external service sits behind an interface with a mock
implementation that is the DEFAULT in dev.
"""
from app.providers.ai import AIProvider, MockAIProvider, get_ai_provider
from app.providers.maps import MapsProvider, MockMapsProvider, get_maps_provider
from app.providers.otp import MockOTPProvider, OTPProvider, get_otp_provider
from app.providers.payment import MockPaymentProvider, PaymentProvider, get_payment_provider
from app.providers.push import MockPushProvider, PushProvider, get_push_provider

__all__ = [
    "AIProvider",
    "MockAIProvider",
    "get_ai_provider",
    "OTPProvider",
    "MockOTPProvider",
    "get_otp_provider",
    "MapsProvider",
    "MockMapsProvider",
    "get_maps_provider",
    "PushProvider",
    "MockPushProvider",
    "get_push_provider",
    "PaymentProvider",
    "MockPaymentProvider",
    "get_payment_provider",
]
