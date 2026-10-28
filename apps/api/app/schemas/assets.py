"""
Asset and Maintenance Log schemas – Fix 24/7.
FR-HEALTH-01, FR-HEALTH-02, FR-HEALTH-03, UC-09.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import AssetType


class PartReplaced(BaseModel):
    name: str
    qty: int = 1
    unit_price: int = 0


class AssetCreate(BaseModel):
    asset_type: AssetType = Field(..., description="vehicle (xe máy) hoặc appliance (gia dụng)")
    brand: str = Field(..., min_length=1, max_length=100, description="Hãng sản xuất (Honda, Yamaha, Daikin,...)")
    model: str = Field(..., min_length=1, max_length=100, description="Dòng máy (AirBlade, Wave Alpha, Inverter 1.5HP,...)")
    year: int | None = Field(None, ge=1990, le=2030, description="Năm sản xuất")
    plate_or_serial: str | None = Field(None, max_length=50, description="Biển số xe (75F1-12345) hoặc số serial máy")
    location_label: str | None = Field(None, max_length=200, description="Vị trí đặt (Phòng khách, Nhà xe,...)")
    notes: str | None = Field(None, max_length=1000, description="Ghi chú thêm về thiết bị")


class AssetUpdate(BaseModel):
    brand: str | None = Field(None, max_length=100)
    model: str | None = Field(None, max_length=100)
    year: int | None = Field(None, ge=1990, le=2030)
    plate_or_serial: str | None = Field(None, max_length=50)
    location_label: str | None = Field(None, max_length=200)
    notes: str | None = Field(None, max_length=1000)


class MaintenanceLogResponse(BaseModel):
    id: UUID
    asset_id: UUID
    order_id: UUID | None = None
    summary: str
    parts_replaced: list[dict] | None = None
    labor_cost: int
    parts_cost: int
    total_cost: int
    technician_id: UUID | None = None
    technician_name: str | None = None
    performed_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class MaintenanceReminderResponse(BaseModel):
    reminder_type: str
    title: str
    message: str
    due_date: datetime | None = None
    is_overdue: bool = False


class AssetResponse(BaseModel):
    id: UUID
    owner_id: UUID
    asset_type: AssetType
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    plate_or_serial: str | None = None
    location_label: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    maintenance_count: int = 0
    last_maintained_at: datetime | None = None
    health_status: str = "good"  # "good" | "needs_maintenance" | "due_soon"
    recent_logs: list[MaintenanceLogResponse] = []
    reminders: list[MaintenanceReminderResponse] = []

    model_config = {"from_attributes": True}


class AssetListResponse(BaseModel):
    total: int
    items: list[AssetResponse]

