"""
Unit tests for DIAG-9: Technician Diagnosis Accuracy Feedback and Admin Analytics.
FR-DIAG-09, SRS §7.2.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.models import (
    Diagnosis,
    Order,
    OrderStatus,
    User,
    UserRole,
    VerifiedLabel,
    _uuid_default,
)
from app.routers.technician import (
    admin_get_diagnosis_accuracy,
    submit_technician_diagnosis_feedback,
)
from app.schemas.diagnosis import TechDiagnosisLabelRequest


@pytest.mark.asyncio
async def test_technician_diagnosis_feedback():
    """
    FR-DIAG-09:
    Technician labels diagnosis accuracy after the job (correct / partial / incorrect).
    Stored in diagnoses.verified_label.
    """
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    tech_user = User(id=_uuid_default(), role=UserRole.technician, phone="0911223344")
    other_user = User(id=_uuid_default(), role=UserRole.technician, phone="0999888777")

    order = MagicMock(spec=Order)
    order.id = _uuid_default()
    order.technician_id = tech_user.id
    order.diagnosis_id = _uuid_default()
    order.status = OrderStatus.COMPLETED

    diag = MagicMock(spec=Diagnosis)
    diag.id = order.diagnosis_id
    diag.verified_label = None

    mock_res_order = MagicMock()
    mock_res_order.scalar_one_or_none.return_value = order
    mock_db.execute.return_value = mock_res_order
    mock_db.get.return_value = diag

    # 1. Other technician cannot submit feedback -> 403 FORBIDDEN
    with pytest.raises(HTTPException) as exc:
        await submit_technician_diagnosis_feedback(
            order_id=UUID(order.id),
            payload=TechDiagnosisLabelRequest(verified_label="correct"),
            current_user=other_user,
            db=mock_db,
        )
    assert exc.value.status_code == 403
    assert exc.value.detail["error"]["code"] == "FORBIDDEN"

    # 2. Assigned technician submits feedback -> 200 OK
    res = await submit_technician_diagnosis_feedback(
        order_id=UUID(order.id),
        payload=TechDiagnosisLabelRequest(
            verified_label="correct",
            notes="AI chẩn đoán đúng bệnh nghẹt béc phun xăng",
        ),
        current_user=tech_user,
        db=mock_db,
    )
    assert res["ok"] is True
    assert res["verified_label"] == "correct"
    assert diag.verified_label == VerifiedLabel.correct
    assert diag.verified_by_id == tech_user.id
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_admin_diagnosis_accuracy_stats():
    """FR-DIAG-09: Admin view computes accuracy % from verified labels."""
    mock_db = AsyncMock()
    admin_user = User(id=_uuid_default(), role=UserRole.admin, phone="0901234567")

    d1 = MagicMock(spec=Diagnosis)
    d1.verified_label = VerifiedLabel.correct

    d2 = MagicMock(spec=Diagnosis)
    d2.verified_label = VerifiedLabel.correct

    d3 = MagicMock(spec=Diagnosis)
    d3.verified_label = VerifiedLabel.partial

    d4 = MagicMock(spec=Diagnosis)
    d4.verified_label = VerifiedLabel.incorrect

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [d1, d2, d3, d4]
    mock_db.execute.return_value = mock_res

    stats = await admin_get_diagnosis_accuracy(current_user=admin_user, db=mock_db)
    assert stats.total_verified == 4
    assert stats.correct_count == 2
    assert stats.partial_count == 1
    assert stats.incorrect_count == 1
    # (2 + 0.5 * 1) / 4 * 100 = 62.5%
    assert stats.accuracy_percentage == 62.5

