"""
Pydantic v2 Schemas for Admin Panel (UC-10, UC-11, FR-ADM-01..04)
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Dashboard Schemas ─────────────────────────────────────────────────────────

class AdminDashboardStats(BaseModel):
    orders_total: int = 0
    orders_today: int = 0
    gmv_total: int = 0  # Total completed order gross value in VND
    gmv_today: int = 0
    commission_total: int = 0  # Total platform commission in VND
    median_time_to_accept_sec: Optional[int] = None
    completion_rate_pct: float = 0.0
    dispute_rate_pct: float = 0.0
    ai_top3_accuracy_pct: float = 0.0
    ai_calls_total: int = 0
    ai_cost_per_call_vnd: int = 150  # Estimated cost ~0.006 USD = ~150 VND
    ai_daily_spend_vnd: int = 0
    ai_monthly_spend_vnd: int = 0
    ai_monthly_budget_vnd: int = 5000000
    ai_budget_alert: bool = False  # >= 80% monthly budget
    maps_daily_spend_vnd: int = 0
    maps_monthly_spend_vnd: int = 0
    maps_monthly_budget_vnd: int = 3000000
    maps_budget_alert: bool = False  # >= 80% monthly budget


# ── Fault Catalog Schemas ─────────────────────────────────────────────────────

class FaultCatalogCreate(BaseModel):
    category_id: str
    fault_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    labor_min: int = Field(..., ge=0)
    labor_max: int = Field(..., ge=0)
    parts_min: int = Field(0, ge=0)
    parts_max: int = Field(0, ge=0)
    safety_notes: Optional[str] = None
    is_active: bool = True


class FaultCatalogUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    labor_min: Optional[int] = Field(None, ge=0)
    labor_max: Optional[int] = Field(None, ge=0)
    parts_min: Optional[int] = Field(None, ge=0)
    parts_max: Optional[int] = Field(None, ge=0)
    safety_notes: Optional[str] = None
    is_active: Optional[bool] = None


class FaultCatalogResponse(BaseModel):
    id: str
    category_id: str
    category_name: Optional[str] = None
    fault_code: str
    name: str
    description: Optional[str] = None
    labor_min: int
    labor_max: int
    parts_min: int
    parts_max: int
    safety_notes: Optional[str] = None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class FaultCatalogListResponse(BaseModel):
    total: int
    items: List[FaultCatalogResponse]


# ── Order Intervention Schemas ────────────────────────────────────────────────

class OrderInterventionTransitionRequest(BaseModel):
    target_status: str
    reason: Optional[str] = None


class OrderInterventionReassignRequest(BaseModel):
    technician_id: str
    reason: Optional[str] = None


class OrderInterventionCancelRequest(BaseModel):
    cancel_reason: str


class OrderInterventionNoteRequest(BaseModel):
    note: str


# ── Dispute Management Schemas ────────────────────────────────────────────────

class DisputeResolveRequest(BaseModel):
    action: str = Field(..., description="'refund', 'reject', or 'close'")
    resolution_note: str


class DisputeResponse(BaseModel):
    id: str
    order_id: str
    opened_by_id: str
    opened_by_phone: Optional[str] = None
    opened_by_name: Optional[str] = None
    reason: str
    status: str
    resolution: Optional[str] = None
    resolved_by_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    order_total: Optional[int] = None
    order_code: Optional[str] = None


class DisputeListResponse(BaseModel):
    total: int
    items: List[DisputeResponse]


# ── Settings Schemas ──────────────────────────────────────────────────────────

class PlatformSettingsUpdate(BaseModel):
    commission_rate: Optional[float] = Field(None, ge=0.05, le=0.20)
    night_surcharge: Optional[int] = Field(None, ge=0)
    survey_fee: Optional[int] = Field(None, ge=0)
    travel_fee: Optional[int] = Field(None, ge=0)
    emergency_radius_km: Optional[float] = Field(None, ge=1.0, le=20.0)
    ai_daily_quota_anon: Optional[int] = Field(None, ge=1)
    ai_daily_quota_user: Optional[int] = Field(None, ge=1)
    monthly_ai_budget_vnd: Optional[int] = Field(None, ge=0)
    monthly_maps_budget_vnd: Optional[int] = Field(None, ge=0)


class PlatformSettingsResponse(BaseModel):
    commission_rate: float
    night_surcharge: int
    survey_fee: int
    travel_fee: int
    emergency_radius_km: float
    ai_daily_quota_anon: int
    ai_daily_quota_user: int
    monthly_ai_budget_vnd: int
    monthly_maps_budget_vnd: int


# ── Admin Action Log Schemas ──────────────────────────────────────────────────

class AdminActionLogResponse(BaseModel):
    id: str
    admin_id: str
    admin_phone: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    detail: Optional[Dict[str, Any]] = None
    created_at: datetime


class AdminActionLogListResponse(BaseModel):
    total: int
    items: List[AdminActionLogResponse]

