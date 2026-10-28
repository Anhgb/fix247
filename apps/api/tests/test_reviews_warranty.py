"""
Unit tests for Reviews, Time-Weighted Ratings, Auto-Suspension, and Warranty Claims.
FR-RATE-01..03, FR-TECH-05, FR-PAY-06.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models import ApprovalStatus, Review, TechnicianProfile
from app.services.review_service import update_technician_rating_stats


@pytest.mark.asyncio
async def test_time_weighted_rating_calculation():
    """
    FR-RATE-03: Reviews within 30 days have weight 1.5, older reviews weight 1.0.
    """
    now = datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc)
    mock_db = AsyncMock()

    # 1 recent 5-star review (weight 1.5)
    r1 = Review(stars=5, created_at=now - timedelta(days=5), to_user_id="tech-1", from_role="customer")
    # 1 older 1-star review (weight 1.0)
    r2 = Review(stars=1, created_at=now - timedelta(days=45), to_user_id="tech-1", from_role="customer")

    # Weighted: (5 * 1.5 + 1 * 1.0) / (1.5 + 1.0) = (7.5 + 1.0) / 2.5 = 8.5 / 2.5 = 3.4
    review_result = MagicMock()
    review_result.scalars.return_value.all.return_value = [r1, r2]

    profile = TechnicianProfile(user_id="tech-1", rating_avg=0, rating_count=0)
    profile_result = MagicMock()
    profile_result.scalar_one_or_none.return_value = profile

    mock_db.execute = AsyncMock(side_effect=[review_result, profile_result])

    avg, count, suspended = await update_technician_rating_stats(mock_db, "tech-1", now=now)

    assert avg == 3.4
    assert count == 2
    assert profile.rating_avg == 3.4
    assert profile.rating_count == 2
    # Not suspended yet because count < 10
    assert suspended is False


@pytest.mark.asyncio
async def test_auto_suspension_fr_tech_05():
    """
    FR-TECH-05: Auto-suspend technician if rating_count >= 10 and rating_avg < 3.5.
    """
    now = datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc)
    mock_db = AsyncMock()

    # 10 reviews with 3 stars each -> avg = 3.0 (< 3.5)
    reviews = [
        Review(stars=3, created_at=now - timedelta(days=2), to_user_id="tech-bad", from_role="customer")
        for _ in range(10)
    ]

    review_result = MagicMock()
    review_result.scalars.return_value.all.return_value = reviews

    profile = TechnicianProfile(
        user_id="tech-bad",
        approval_status=ApprovalStatus.approved,
        is_online=True,
    )
    profile_result = MagicMock()
    profile_result.scalar_one_or_none.return_value = profile

    mock_db.execute = AsyncMock(side_effect=[review_result, profile_result])

    avg, count, suspended = await update_technician_rating_stats(mock_db, "tech-bad", now=now)

    assert count == 10
    assert avg == 3.0
    assert suspended is True
    assert profile.approval_status == ApprovalStatus.suspended
    assert profile.is_online is False

