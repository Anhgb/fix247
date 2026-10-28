"""
Technician Onboarding and Management schemas – Fix 24/7.
FR-TECH-01, FR-TECH-02, FR-TECH-03, FR-TECH-04, FR-TECH-05, UC-08.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import ApprovalStatus


class TechProfileOnboardingRequest(BaseModel):
    id_number: str = Field(..., min_length=9, max_length=12, description="Số CCCD/CMND (9 hoặc 12 số, sẽ được mã hóa AES-256)")
    portrait_url: str = Field(..., min_length=5, description="Ảnh chân dung thợ")
    certificate_urls: list[str] = Field(default_factory=list, max_length=5, description="Tối đa 5 chứng chỉ nghề (A-11)")
    specialties: list[str] = Field(default_factory=list, description="Chuyên môn: motorbike, air_conditioner, refrigerator, washing_machine,...")
    service_areas: list[str] = Field(default_factory=list, description="Khu vực hoạt động tại Huế: Phu Nhuan, Vy Da, Hai Ba Trung,...")


class TechBadge(BaseModel):
    id: str
    name: str
    description: str
    icon: str


class TechProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    id_number_masked: str
    portrait_url: str | None = None
    certificate_urls: list[str] = []
    specialties: list[str] = []
    service_areas: list[str] = []
    approval_status: ApprovalStatus
    approval_note: str | None = None
    approved_at: datetime | None = None
    is_online: bool
    rating_avg: float
    rating_count: int
    total_earned: int
    debt_amount: int
    badges: list[TechBadge] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TechApprovalRequest(BaseModel):
    note: str | None = Field(None, max_length=500, description="Ghi chú duyệt hoặc lý do từ chối")


class TechOrderHistoryItem(BaseModel):
    order_id: UUID
    code: str
    service_name: str
    status: str
    customer_name: str
    address: str
    completed_at: datetime | None = None
    total_amount: int
    tech_earnings: int
    customer_rating: int | None = None
    customer_comment: str | None = None


class TechOrderHistoryResponse(BaseModel):
    total: int
    items: list[TechOrderHistoryItem]
    total_earnings: int

