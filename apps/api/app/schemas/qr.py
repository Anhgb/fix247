"""
Pydantic v2 Schemas for QR Location Management (UC-12, FR-QR-01, FR-QR-02)
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class QRLocationCreate(BaseModel):
    name: str = Field(..., max_length=200)
    location_type: Optional[str] = Field("KTX / Khu trọ", max_length=50)
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    owner_contact: Optional[str] = None


class QRLocationUpdate(BaseModel):
    name: Optional[str] = None
    location_type: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    owner_contact: Optional[str] = None
    is_active: Optional[bool] = None


class QRLocationResponse(BaseModel):
    id: str
    code: str
    name: str
    location_type: Optional[str] = None
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    owner_contact: Optional[str] = None
    scan_count: int
    order_count: int
    conversion_rate_pct: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    landing_url: str


class QRLocationListResponse(BaseModel):
    total: int
    items: List[QRLocationResponse]


class QRLocationPublicResponse(BaseModel):
    id: str
    code: str
    name: str
    location_type: Optional[str] = None
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None

