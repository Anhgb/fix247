"""
Auth service: OTP generation, rate limiting, JWT issuance.
FR-AUTH-01: OTP expires 5min, 5 wrong → block 15min, max 3 sends/hour.
"""
import uuid
from datetime import UTC, datetime

from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
)
from app.models import User, UserRole
from app.providers.otp import OTPProvider, generate_otp

logger = get_logger(__name__)

OTP_TTL = 300           # 5 minutes
OTP_MAX_ATTEMPTS = 5    # FR-AUTH-01: sai 5 lần khóa 15 phút
OTP_BLOCK_TTL = 900     # 15 minutes
OTP_MAX_SENDS_PER_HOUR = 3  # FR-AUTH-01: gửi lại tối đa 3 lần/giờ


def _otp_key(phone: str) -> str:
    return f"otp:{phone}"


def _attempts_key(phone: str) -> str:
    return f"otp_attempts:{phone}"


def _block_key(phone: str) -> str:
    return f"otp_block:{phone}"


def _send_count_key(phone: str) -> str:
    return f"otp_sends:{phone}"


def _refresh_key(user_id: str) -> str:
    return f"refresh:{user_id}"


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis, otp_provider: OTPProvider):
        self.db = db
        self.redis = redis
        self.otp_provider = otp_provider

    async def request_otp(self, phone: str) -> dict:
        """Send OTP with rate limiting. Returns status info."""
        # Check if blocked
        if await self.redis.get(_block_key(phone)):
            return {"ok": False, "error": "TOO_MANY_ATTEMPTS", "message": "Tài khoản tạm khóa 15 phút do nhập sai quá nhiều lần"}

        # Check send rate
        sends = await self.redis.get(_send_count_key(phone))
        if sends and int(sends) >= OTP_MAX_SENDS_PER_HOUR:
            return {"ok": False, "error": "RATE_LIMIT", "message": "Vượt giới hạn gửi OTP. Vui lòng thử lại sau 1 giờ"}

        # Generate and store OTP
        otp = generate_otp()
        await self.redis.setex(_otp_key(phone), OTP_TTL, otp)
        await self.redis.delete(_attempts_key(phone))

        # Increment send count (expire in 1 hour)
        pipe = self.redis.pipeline()
        pipe.incr(_send_count_key(phone))
        pipe.expire(_send_count_key(phone), 3600)
        await pipe.execute()

        # Send (mock prints to console)
        await self.otp_provider.send_otp(phone, otp)
        logger.info("otp_requested", phone_suffix=phone[-4:])
        return {"ok": True, "message": "Mã OTP đã được gửi"}

    async def verify_otp(self, phone: str, otp: str) -> dict:
        """Verify OTP, create/get user, return JWT tokens."""
        # Check blocked
        if await self.redis.get(_block_key(phone)):
            return {"ok": False, "error": "TOO_MANY_ATTEMPTS", "message": "Tài khoản tạm khóa 15 phút"}

        stored_otp = await self.redis.get(_otp_key(phone))
        if not stored_otp:
            return {"ok": False, "error": "OTP_EXPIRED", "message": "Mã OTP đã hết hạn hoặc chưa được gửi"}

        if stored_otp != otp:
            # Increment failure counter
            attempts = await self.redis.incr(_attempts_key(phone))
            await self.redis.expire(_attempts_key(phone), OTP_TTL)
            if int(attempts) >= OTP_MAX_ATTEMPTS:
                await self.redis.setex(_block_key(phone), OTP_BLOCK_TTL, "1")
                await self.redis.delete(_otp_key(phone))
                logger.warning("otp_blocked", phone_suffix=phone[-4:])
                return {"ok": False, "error": "BLOCKED", "message": "Sai quá nhiều lần. Tài khoản bị khóa 15 phút"}
            remaining = OTP_MAX_ATTEMPTS - int(attempts)
            return {
                "ok": False,
                "error": "INVALID_OTP",
                "message": f"Mã OTP không đúng. Còn {remaining} lần thử",
            }

        # OTP correct — clean up
        await self.redis.delete(_otp_key(phone))
        await self.redis.delete(_attempts_key(phone))

        # Get or create user
        result = await self.db.execute(
            select(User).where(User.phone == phone, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(id=str(uuid.uuid4()), phone=phone, role=UserRole.customer)
            self.db.add(user)
            await self.db.flush()
            logger.info("user_created", phone_suffix=phone[-4:])

        # Issue tokens
        payload = {"sub": user.id, "role": user.role.value}
        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)

        # Store refresh token in Redis for revocation (FR-AUTH-02)
        from app.core.config import get_settings
        settings = get_settings()
        await self.redis.setex(
            _refresh_key(user.id),
            settings.jwt_refresh_expire_days * 86400,
            refresh_token,
        )

        return {
            "ok": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "role": user.role.value,
            "user_id": user.id,
            "terms_accepted": user.terms_accepted_at is not None,
        }

    async def refresh(self, refresh_token: str) -> dict:
        """Exchange refresh token for new access token."""
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            return {"ok": False, "error": "INVALID_TOKEN", "message": "Token không hợp lệ"}

        if not verify_token_type(payload, "refresh"):
            return {"ok": False, "error": "INVALID_TOKEN", "message": "Sai loại token"}

        user_id = payload.get("sub")
        stored = await self.redis.get(_refresh_key(user_id))
        if stored != refresh_token:
            return {"ok": False, "error": "REVOKED", "message": "Token đã bị thu hồi"}

        access_token = create_access_token({"sub": user_id, "role": payload["role"]})
        return {"ok": True, "access_token": access_token, "token_type": "bearer"}

    async def logout(self, user_id: str) -> None:
        """Revoke refresh token (FR-AUTH-02)."""
        await self.redis.delete(_refresh_key(user_id))

    async def accept_terms(self, user_id: str) -> None:
        """FR-AUTH-04: Record terms acceptance timestamp."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.terms_accepted_at = datetime.now(UTC)
