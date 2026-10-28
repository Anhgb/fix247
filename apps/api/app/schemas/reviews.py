"""
Review & Dispute schemas – Fix 24/7.
FR-RATE-01, FR-RATE-02, FR-RATE-03, ADM-3.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    stars: int = Field(..., ge=1, le=5, description="Số sao từ 1 đến 5")
    tags: list[str] = Field(default_factory=list, description="Thẻ đánh giá: đúng giờ, giá đúng báo, sạch sẽ...")
    comment: str | None = Field(None, max_length=500, description="Nhận xét tối đa 500 ký tự")


class ReviewResponse(BaseModel):
    id: UUID
    order_id: UUID
    from_user_id: UUID
    to_user_id: UUID
    from_role: str
    stars: int
    tags: list[str]
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DisputeCreate(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1000, description="Lý do khiếu nại tranh chấp")


class DisputeResponse(BaseModel):
    id: UUID
    order_id: UUID
    opened_by_id: UUID
    reason: str
    status: str
    created_at: datetime
    resolution: str | None = None
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}

