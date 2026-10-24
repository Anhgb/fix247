"""
Pydantic v2 schemas for Diagnosis endpoints.
FR-DIAG-01..09, SRS §7.2, §7.4.
"""
from typing import Any, Literal
from pydantic import BaseModel, Field


def get_confidence_label(confidence: float) -> str:
    """FR-DIAG-03: Thấp (<0.50), Vừa (0.50-0.79), Cao (>=0.80)."""
    if confidence < 0.50:
        return "Thấp"
    elif confidence < 0.80:
        return "Vừa"
    return "Cao"


def get_severity_vi(severity: str) -> str:
    mapping = {
        "low": "Thấp",
        "medium": "Trung bình",
        "high": "Cao",
        "critical": "Khẩn cấp",
    }
    return mapping.get(severity.lower(), severity)


class PriceRange(BaseModel):
    min: int = Field(..., description="Giá tối thiểu (VNĐ, đã làm tròn 10.000đ)")
    max: int = Field(..., description="Giá tối đa (VNĐ, đã làm tròn 10.000đ)")
    currency: str = "VND"


class CandidateResponse(BaseModel):
    fault_code: str
    name: str
    confidence: float
    confidence_label: str
    severity: str
    severity_vi: str
    price_range: PriceRange | None = None
    price_display: str
    safety_warning: str | None = None


class DiagnosisResponse(BaseModel):
    id: str
    user_id: str | None = None
    asset_id: str | None = None
    category_id: str | None = None
    category_group: str
    description: str | None = None
    media_urls: list[str] = Field(default_factory=list)
    candidates: list[CandidateResponse] = Field(default_factory=list)
    safety_warnings: list[str] = Field(default_factory=list)
    self_checks: list[str] = Field(default_factory=list)
    followup_questions: list[str] = Field(default_factory=list)
    needs_technician: bool = True
    can_book_without_diagnosis: bool = False
    is_cached: bool = False
    has_audio_beta: bool = False
    disclaimer: str = (
        "Kết quả chẩn đoán mang tính tham khảo dựa trên mô tả và AI. "
        "Chi phí sửa chữa chính thức sẽ được thợ khảo sát trực tiếp và báo giá minh bạch."
    )
    created_at: str


class DiagnosisFeedbackRequest(BaseModel):
    verified_label: Literal["correct", "partial", "wrong"] | None = None
    feedback_text: str | None = None
    rating: int | None = Field(None, ge=1, le=5)
