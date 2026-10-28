"""
Pydantic v2 schemas for orders – Fix 24/7.
SRS §7.4, UC-03/04/05/06.
All user-facing text in Vietnamese.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models import ItemType, OrderMode, OrderStatus


# ── Location ───────────────────────────────────────────────────────────────────

class LocationIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Vĩ độ")
    lng: float = Field(..., ge=-180, le=180, description="Kinh độ")
    address: str = Field(..., min_length=1, max_length=500, description="Địa chỉ")


# ── Order Create ───────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    """FR-BOOK-03/05: Create emergency or scheduled order."""
    mode: OrderMode
    diagnosis_id: UUID | None = None
    asset_id: UUID | None = None
    qr_location_id: UUID | None = None
    qr_code: str | None = None
    location: LocationIn
    note: str | None = Field(None, max_length=1000)
    scheduled_at: datetime | None = None  # FR-BOOK-03: required for scheduled mode


# ── Quote ─────────────────────────────────────────────────────────────────────

class QuoteItem(BaseModel):
    item_type: ItemType
    name: str = Field(..., min_length=1, max_length=200)
    qty: int = Field(..., ge=1)
    unit_price: int = Field(..., ge=0, description="Đơn giá VND")
    photo_url: str | None = Field(None, max_length=500)


class QuoteSubmit(BaseModel):
    """UC-05: Technician submits quote. BR-05: quote_reason required when >20%."""
    items: list[QuoteItem] = Field(..., min_length=1)
    note: str | None = Field(None, max_length=1000)
    quote_reason: str | None = Field(None, max_length=500)


class QuoteRespond(BaseModel):
    """UC-05: Customer accepts or rejects the quote."""
    action: Literal["accept", "reject"]


# ── Status update ──────────────────────────────────────────────────────────────

class OrderStatusUpdate(BaseModel):
    to_status: OrderStatus
    note: str | None = Field(None, max_length=500)


class CancelOrder(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="Lý do hủy đơn")


# ── Technician location ───────────────────────────────────────────────────────

class TechLocationUpdate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    media_url: str | None = Field(None, max_length=500)


class ChatMessageResponse(BaseModel):
    id: UUID
    order_id: UUID
    sender_id: UUID
    sender_role: str
    content: str
    media_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Order responses ───────────────────────────────────────────────────────────

class OrderItemResponse(BaseModel):
    id: UUID
    item_type: ItemType
    name: str
    qty: int
    unit_price: int
    photo_url: str | None

    model_config = {"from_attributes": True}


class OrderEventResponse(BaseModel):
    id: UUID
    from_status: OrderStatus | None
    to_status: OrderStatus
    actor_id: UUID | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: UUID
    customer_id: UUID
    technician_id: UUID | None
    asset_id: UUID | None
    diagnosis_id: UUID | None
    mode: OrderMode
    status: OrderStatus
    address: str
    lat: float | None
    lng: float | None
    scheduled_at: datetime | None
    est_min: int | None
    est_max: int | None
    night_surcharge: int
    survey_fee: int
    final_quote: int | None
    commission_rate: float | None
    commission_amount: int | None
    total: int | None
    customer_note: str | None
    cancel_reason: str | None
    accepted_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []
    events: list[OrderEventResponse] = []

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    size: int
