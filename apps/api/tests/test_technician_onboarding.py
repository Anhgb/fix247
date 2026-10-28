"""
Unit tests for Technician Onboarding, Approval, Badges, and Auto-Offline.
FR-TECH-01, FR-TECH-02, FR-TECH-03, FR-TECH-04, FR-TECH-05, AT-07, UC-08.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.core.encryption import decrypt, encrypt
from app.models import (
    ApprovalStatus,
    TechnicianProfile,
    User,
    UserRole,
    _uuid_default,
)
from app.routers.technician import (
    TechStatusUpdate,
    admin_approve_technician,
    admin_reject_technician,
    admin_suspend_technician,
    register_or_update_technician_profile,
    toggle_technician_status,
)
from app.schemas.technician import TechApprovalRequest, TechProfileOnboardingRequest
from app.services.technician_service import (
    auto_offline_inactive_technicians,
    compute_technician_badges,
    mask_id_number,
)


def test_encryption_and_masking():
    """NFR-04: National ID encrypted at rest and masked in responses."""
    plaintext = "046098001234"
    ciphertext = encrypt(plaintext)
    assert ciphertext != plaintext
    assert decrypt(ciphertext) == plaintext

    # Masking
    masked = mask_id_number(ciphertext)
    assert masked.endswith("1234")
    assert masked.startswith("********")


def test_technician_badges_calculation():
    """FR-TECH-04: Badges calculated from ratings, specialties, and debt."""
    profile = TechnicianProfile(
        id=_uuid_default(),
        user_id=_uuid_default(),
        id_number_encrypted="encrypted",
        specialties=["motorbike", "air_conditioner"],
        service_areas=["Phu Nhuan"],
        rating_avg=4.9,
        rating_count=12,
        debt_amount=0,
    )
    badges = compute_technician_badges(profile)
    badge_ids = [b.id for b in badges]

    assert "five_star" in badge_ids
    assert "hard_working" in badge_ids
    assert "motorbike_expert" in badge_ids
    assert "appliance_expert" in badge_ids
    assert "trusted_partner" in badge_ids


@pytest.mark.asyncio
async def test_auto_offline_inactive_technicians():
    """
    FR-TECH-03, DECISIONS A-14:
    Technicians online without location pings for > 5 mins are set offline.
    """
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    stale_time = datetime.now(timezone.utc) - timedelta(minutes=6)
    stale_profile = TechnicianProfile(
        id=_uuid_default(),
        user_id=_uuid_default(),
        id_number_encrypted="enc1",
        is_online=True,
        location_updated_at=stale_time,
        approval_status=ApprovalStatus.approved,
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [stale_profile]
    mock_db.execute.return_value = mock_res

    offlined = await auto_offline_inactive_technicians(mock_db)
    assert offlined == 1
    assert stale_profile.is_online is False
    assert stale_profile.location_updated_at is None
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_technician_onboarding_and_max_certificates():
    """FR-TECH-01, DECISIONS A-11: Profile onboarding with max 5 certificates."""
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None  # New profile
    mock_db.execute.return_value = mock_res

    tech_user = User(id=_uuid_default(), role=UserRole.technician, phone="0911223344")

    # 1. Reject if > 5 certificates via Pydantic schema validation (A-11)
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TechProfileOnboardingRequest(
            id_number="046098001111",
            portrait_url="https://minio/portrait.jpg",
            certificate_urls=[f"https://minio/cert_{i}.jpg" for i in range(6)],
            specialties=["motorbike"],
            service_areas=["Phu Nhuan"],
        )

    # 2. Accept valid profile -> status pending
    good_req = TechProfileOnboardingRequest(
        id_number="046098001111",
        portrait_url="https://minio/portrait.jpg",
        certificate_urls=["https://minio/cert1.jpg"],
        specialties=["motorbike"],
        service_areas=["Phu Nhuan"],
    )
    resp = await register_or_update_technician_profile(good_req, current_user=tech_user, db=mock_db)
    assert resp.approval_status == ApprovalStatus.pending
    assert resp.id_number_masked.endswith("1111")
    assert resp.is_online is False
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_approval_flow_and_online_toggle():
    """
    AT-07: Unapproved technician cannot go online.
    Admin approves -> technician can toggle online.
    """
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    tech_user = User(id=_uuid_default(), role=UserRole.technician, phone="0988001122")
    admin_user = User(id=_uuid_default(), role=UserRole.admin, phone="0901234567")

    pending_profile = TechnicianProfile(
        id=_uuid_default(),
        user_id=tech_user.id,
        id_number_encrypted=encrypt("046098005555"),
        approval_status=ApprovalStatus.pending,
        is_online=False,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = pending_profile
    mock_db.execute.return_value = mock_res

    # 1. Unapproved technician tries to go online -> 403 NOT_APPROVED (AT-07)
    with pytest.raises(HTTPException) as exc:
        await toggle_technician_status(
            TechStatusUpdate(is_online=True), current_user=tech_user, db=mock_db
        )
    assert exc.value.status_code == 403
    assert exc.value.detail["error"]["code"] == "NOT_APPROVED"

    # 2. Admin approves technician
    appr_res = await admin_approve_technician(
        tech_user_id=UUID(tech_user.id),
        payload=TechApprovalRequest(note="Đạt yêu cầu"),
        current_user=admin_user,
        db=mock_db,
    )
    assert appr_res["approval_status"] == "approved"
    assert pending_profile.approval_status == ApprovalStatus.approved

    # 3. Approved technician can go online
    toggle_res = await toggle_technician_status(
        TechStatusUpdate(is_online=True), current_user=tech_user, db=mock_db
    )
    assert toggle_res["is_online"] is True
    assert pending_profile.is_online is True

    # 4. Admin suspends technician -> sets offline (FR-TECH-05)
    susp_res = await admin_suspend_technician(
        tech_user_id=UUID(tech_user.id),
        payload=TechApprovalRequest(note="Điểm đánh giá quá thấp"),
        current_user=admin_user,
        db=mock_db,
    )
    assert susp_res["approval_status"] == "suspended"
    assert pending_profile.is_online is False

