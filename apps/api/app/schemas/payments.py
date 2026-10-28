"""
Payment & Invoice schemas – Fix 24/7.
FR-PAY-01, FR-PAY-02, FR-PAY-03, BR-01, BR-02, BR-09.
All currency values in integer VND.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import PaymentMethod, PaymentStatus


class InvoiceItem(BaseModel):
    name: str
    item_type: str  # "labor" | "part"
    qty: int
    unit_price: int
    line_total: int


class InvoiceResponse(BaseModel):
    order_id: UUID
    customer_name: str | None
    customer_phone: str
    technician_name: str | None
    technician_phone: str | None
    address: str
    items: list[InvoiceItem]
    labor_subtotal: int
    parts_subtotal: int
    night_surcharge: int
    total: int
    commission_rate: float
    commission_amount: int  # Internal line
    warranty_days: int
    created_at: datetime
    paid_at: datetime | None = None
    payment_method: PaymentMethod | None = None


class PaymentCreateRequest(BaseModel):
    method: PaymentMethod


class PaymentCreateResponse(BaseModel):
    payment_id: UUID
    order_id: UUID
    method: PaymentMethod
    amount: int
    status: PaymentStatus
    provider_ref: str | None
    qr_url: str | None = None
    account_name: str | None = None
    account_number: str | None = None
    bank_name: str | None = None


class PaymentWebhookPayload(BaseModel):
    provider_ref: str = Field(..., description="Unique transaction reference from gateway")
    order_id: str
    amount: int
    status: str = Field("completed", description="Status from payment gateway")
    signature: str = Field(..., description="Gateway HMAC signature")


class CashPaymentConfirm(BaseModel):
    amount_collected: int = Field(..., ge=0)


class WalletInfoResponse(BaseModel):
    technician_id: UUID
    total_earned: int
    total_commission: int
    debt_amount: int
    debt_overdue_at: datetime | None
    is_blocked: bool
    block_reason: str | None = None

