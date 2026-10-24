"""Auth Pydantic schemas. FR-AUTH-01..04."""
import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


VN_PHONE_RE = re.compile(r"^(03|05|07|08|09)\d{8}$")


class OTPRequestSchema(BaseModel):
    """FR-AUTH-01: SĐT Việt Nam 10 số."""
    phone: str = Field(..., description="Số điện thoại Việt Nam, 10 số")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if not VN_PHONE_RE.match(v):
            raise ValueError(
                "Số điện thoại không hợp lệ. Vui lòng nhập số Việt Nam 10 chữ số (đầu 03/05/07/08/09)"
            )
        return v


class OTPVerifySchema(BaseModel):
    phone: str
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not VN_PHONE_RE.match(v):
            raise ValueError("Số điện thoại không hợp lệ")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    terms_accepted: bool


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class TermsAcceptSchema(BaseModel):
    accepted: bool = True


class UserMeResponse(BaseModel):
    id: str
    phone: str
    name: str | None
    role: str
    avatar_url: str | None
    status: str
    terms_accepted_at: datetime | None

    model_config = {"from_attributes": True}
