"""
FastAPI auth dependency: extract and validate JWT, enforce role guards.
FR-AUTH-02/03.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import decode_token, verify_token_type
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: returns authenticated User or raises 401."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Vui lòng đăng nhập"}},
        )
    try:
        payload = decode_token(credentials.credentials)
        if not verify_token_type(payload, "access"):
            raise ValueError("wrong token type")
        user_id: str = payload["sub"]
    except (JWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Token không hợp lệ hoặc đã hết hạn"}},
        )

    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None or user.status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "Tài khoản không tồn tại hoặc bị khóa"}},
        )
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Optional auth — returns None if no valid token."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(*roles: str):
    """Role guard factory. FR-AUTH-03."""
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": f"Tính năng này yêu cầu vai trò: {', '.join(roles)}",
                    }
                },
            )
        return current_user
    return dependency


# Pre-built role dependencies
require_customer = require_role("customer", "admin")   # admin can do all customer actions too
require_technician = require_role("technician")
require_admin = require_role("admin")
require_any = require_role("customer", "technician", "admin")
