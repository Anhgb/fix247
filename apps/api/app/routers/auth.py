"""
Auth router – POST /api/v1/auth/*
FR-AUTH-01..04.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.redis import get_redis
from app.models import User
from app.providers.otp import get_otp_provider
from app.schemas.auth import (
    OTPRequestSchema,
    OTPVerifySchema,
    RefreshTokenSchema,
    TermsAcceptSchema,
    TokenResponse,
    UserMeResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_auth_service(db: AsyncSession = Depends(get_db)):
    """Dependency builder for AuthService."""
    async def _inner():
        redis = await get_redis()
        otp_provider = get_otp_provider()
        return AuthService(db, redis, otp_provider)
    return _inner


@router.post("/otp/request")
async def request_otp(
    body: OTPRequestSchema,
    db: AsyncSession = Depends(get_db),
):
    """
    FR-AUTH-01: Gửi OTP đến SĐT.
    Rate limit: 3 lần/giờ; sai 5 lần → khóa 15 phút.
    """
    redis = await get_redis()
    service = AuthService(db, redis, get_otp_provider())
    result = await service.request_otp(body.phone)
    if not result["ok"]:
        code = result["error"]
        http_status = status.HTTP_429_TOO_MANY_REQUESTS if "RATE" in code or "ATTEMPTS" in code else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=http_status,
            detail={"error": {"code": code, "message": result["message"]}},
        )
    return {"message": result["message"]}


@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp(
    body: OTPVerifySchema,
    db: AsyncSession = Depends(get_db),
):
    """FR-AUTH-01: Xác minh OTP, trả JWT access + refresh token."""
    redis = await get_redis()
    service = AuthService(db, redis, get_otp_provider())
    result = await service.verify_otp(body.phone, body.otp)
    if not result["ok"]:
        code = result["error"]
        http_status = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if code in ("TOO_MANY_ATTEMPTS", "BLOCKED")
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=http_status,
            detail={"error": {"code": code, "message": result["message"]}},
        )
    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        role=result["role"],
        user_id=result["user_id"],
        terms_accepted=result["terms_accepted"],
    )


@router.post("/refresh")
async def refresh_token(
    body: RefreshTokenSchema,
    db: AsyncSession = Depends(get_db),
):
    """FR-AUTH-02: Đổi refresh token lấy access token mới."""
    redis = await get_redis()
    service = AuthService(db, redis, get_otp_provider())
    result = await service.refresh(body.refresh_token)
    if not result["ok"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": result["error"], "message": result["message"]}},
        )
    return result


@router.post("/logout")
async def logout(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """FR-AUTH-02: Thu hồi refresh token."""
    redis = await get_redis()
    service = AuthService(db, redis, get_otp_provider())
    await service.logout(current_user.id)
    return {"message": "Đăng xuất thành công"}


@router.post("/terms/accept")
async def accept_terms(
    body: TermsAcceptSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """FR-AUTH-04: Đồng ý điều khoản sử dụng."""
    if not body.accepted:
        raise HTTPException(status_code=400, detail={"error": {"code": "TERMS_REQUIRED", "message": "Phải đồng ý điều khoản để sử dụng"}})
    redis = await get_redis()
    service = AuthService(db, redis, get_otp_provider())
    await service.accept_terms(current_user.id)
    return {"message": "Đã đồng ý điều khoản"}


@router.get("/me", response_model=UserMeResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Trả thông tin người dùng hiện tại."""
    return current_user
