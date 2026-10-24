"""
Tests for auth service OTP rate limiting.
FR-AUTH-01: OTP expires 5min, sai 5 lần khóa 15 phút, max 3 gửi/giờ.
AGENTS.md: Write tests for auth/OTP limits.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.auth import (
    AuthService,
    OTP_MAX_ATTEMPTS,
    OTP_MAX_SENDS_PER_HOUR,
    _otp_key,
    _attempts_key,
    _block_key,
    _send_count_key,
)


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    pipe = MagicMock()
    pipe.incr = MagicMock()
    pipe.expire = MagicMock()
    pipe.execute = AsyncMock(return_value=[1, True])
    redis.pipeline = MagicMock(return_value=pipe)
    return redis


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_otp_provider():
    provider = AsyncMock()
    provider.send_otp = AsyncMock(return_value=True)
    return provider


@pytest.fixture
def auth_service(mock_db, mock_redis, mock_otp_provider):
    return AuthService(mock_db, mock_redis, mock_otp_provider)


class TestOTPRateLimit:
    async def test_send_otp_blocked(self, auth_service, mock_redis):
        """When block key exists, OTP send should be refused."""
        mock_redis.get = AsyncMock(side_effect=lambda key: "1" if "block" in key else None)
        result = await auth_service.request_otp("0905111001")
        assert result["ok"] is False
        assert result["error"] == "TOO_MANY_ATTEMPTS"

    async def test_send_otp_rate_limit_hourly(self, auth_service, mock_redis):
        """After 3 sends in an hour, 4th should be refused."""
        mock_redis.get = AsyncMock(
            side_effect=lambda key: "3" if "sends" in key else None
        )
        result = await auth_service.request_otp("0905111001")
        assert result["ok"] is False
        assert result["error"] == "RATE_LIMIT"

    async def test_send_otp_success(self, auth_service, mock_redis):
        """Normal OTP send should succeed."""
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        result = await auth_service.request_otp("0905111001")
        assert result["ok"] is True

    async def test_verify_wrong_otp_increments_counter(self, auth_service, mock_redis):
        """Wrong OTP should increment failure counter."""
        mock_redis.get = AsyncMock(
            side_effect=lambda key: "123456" if "otp:0905" in key else None
        )
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        result = await auth_service.verify_otp("0905111001", "999999")
        assert result["ok"] is False
        assert result["error"] == "INVALID_OTP"
        mock_redis.incr.assert_called_once()

    async def test_verify_5th_wrong_otp_blocks(self, auth_service, mock_redis):
        """5th wrong attempt should trigger 15-min block."""
        mock_redis.get = AsyncMock(
            side_effect=lambda key: "123456" if "otp:0905" in key else None
        )
        mock_redis.incr = AsyncMock(return_value=OTP_MAX_ATTEMPTS)
        mock_redis.expire = AsyncMock()
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()
        result = await auth_service.verify_otp("0905111001", "999999")
        assert result["ok"] is False
        assert result["error"] == "BLOCKED"
        mock_redis.setex.assert_called()

    async def test_verify_expired_otp(self, auth_service, mock_redis):
        """Expired OTP (not in Redis) should return OTP_EXPIRED."""
        mock_redis.get = AsyncMock(return_value=None)
        result = await auth_service.verify_otp("0905111001", "123456")
        assert result["ok"] is False
        assert result["error"] == "OTP_EXPIRED"

    async def test_verify_correct_otp_success(self, auth_service, mock_redis, mock_db):
        """Correct OTP should return tokens."""
        mock_redis.get = AsyncMock(
            side_effect=lambda key: "123456" if "otp:0905" in key else None
        )
        mock_redis.delete = AsyncMock()
        mock_redis.setex = AsyncMock()

        # Mock DB: user already exists
        mock_user = MagicMock()
        mock_user.id = "user-uuid-1234"
        mock_user.role = MagicMock()
        mock_user.role.value = "customer"
        mock_user.terms_accepted_at = None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.flush = AsyncMock()

        result = await auth_service.verify_otp("0905111001", "123456")
        assert result["ok"] is True
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["role"] == "customer"
