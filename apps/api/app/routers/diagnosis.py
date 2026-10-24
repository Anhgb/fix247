"""
Diagnosis router – /api/v1/diagnoses
FR-DIAG-01..09, UC-02.
"""
import json
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.core.redis import get_redis
from app.models import ServiceCategory, User
from app.schemas.diagnosis import DiagnosisFeedbackRequest, DiagnosisResponse
from app.services.diagnosis import DiagnosisService
from app.services.storage import StorageService, get_storage_service

router = APIRouter(prefix="/diagnoses", tags=["diagnoses"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_diagnosis(
    request: Request,
    category_group: str = Form("motorbike", description="motorbike | home"),
    category_id: str | None = Form(None),
    asset_id: str | None = Form(None),
    description: str | None = Form(None),
    clarifying_answers: str | None = Form(None, description="JSON encoded dict of answers"),
    images: list[UploadFile] | None = None,
    video: UploadFile | None = None,
    audio: UploadFile | None = None,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> dict[str, Any]:
    """
    Create an AI diagnosis from media + description.
    FR-DIAG-01: File limits (images <= 5 <= 8MB, video <= 50MB, audio <= 10MB).
    FR-DIAG-07: Quotas: 10/day for logged-in user, 2/day for anonymous (returns 429).
    FR-DIAG-08: Content hash cache 24h.
    FR-AUTH-04: Terms acceptance gate for logged-in users.
    """
    # FR-AUTH-04: Logged-in user must have accepted terms before diagnosing
    if current_user and not current_user.terms_accepted_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "TERMS_NOT_ACCEPTED",
                "message": "Bạn cần chấp nhận Điều khoản Dịch vụ trước khi tạo chẩn đoán.",
            },
        )

    # Parse clarifying answers if provided
    answers_dict = None
    if clarifying_answers:
        try:
            answers_dict = json.loads(clarifying_answers)
        except Exception:
            answers_dict = {"raw": clarifying_answers}

    # Validate and save uploaded media files
    saved_media = await storage.validate_and_save_media(
        images=images,
        video=video,
        audio=audio,
    )
    media_urls = [m["url"] for m in saved_media]

    # Client IP for anonymous quota tracking
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    # Run Diagnosis Service
    redis = await get_redis()
    service = DiagnosisService(db=db, redis=redis)

    result = await service.create_diagnosis(
        user_id=current_user.id if current_user else None,
        client_ip=client_ip,
        category_group=category_group,
        category_id=category_id,
        asset_id=asset_id,
        description=description,
        media_urls=media_urls,
        clarifying_answers=answers_dict,
    )

    return {"success": True, "data": result.model_dump()}


@router.get("/{diagnosis_id}")
async def get_diagnosis(
    diagnosis_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve diagnosis by ID with catalog price mapping."""
    redis = await get_redis()
    service = DiagnosisService(db=db, redis=redis)
    result = await service.get_diagnosis_by_id(diagnosis_id)
    return {"success": True, "data": result.model_dump()}


@router.post("/{diagnosis_id}/feedback")
async def submit_diagnosis_feedback(
    diagnosis_id: str,
    body: DiagnosisFeedbackRequest,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """FR-DIAG-09: Mark verified label (correct/partial/wrong) or user feedback."""
    redis = await get_redis()
    service = DiagnosisService(db=db, redis=redis)
    res = await service.submit_feedback(
        diagnosis_id=diagnosis_id,
        verified_label=body.verified_label,
        feedback_text=body.feedback_text,
        rating=body.rating,
        user_id=current_user.id if current_user else None,
    )
    return {"success": True, "data": res}
