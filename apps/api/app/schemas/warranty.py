"""
Warranty schemas – Fix 24/7.
FR-PAY-06.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WarrantyClaimCreate(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1000, description="Mô tả sự cố cần bảo hành")
    media_urls: list[str] = Field(default_factory=list, description="Ảnh/video sự cố")


class WarrantyClaimResponse(BaseModel):
    id: UUID
    order_id: UUID
    opened_by_id: UUID
    reason: str
    media_urls: list[str]
    status: str
    created_at: datetime
    resolved_at: datetime | None = None
    resolution_note: str | None = None

    model_config = {"from_attributes": True}


class TechCompleteOrderRequest(BaseModel):
    photo_after_urls: list[str] = Field(default_factory=list, description="Ảnh chụp sau khi sửa xong")
    summary: str | None = Field(None, max_length=500, description="Tóm tắt công việc đã làm")

