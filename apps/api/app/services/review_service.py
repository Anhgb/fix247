"""
Review & Rating Service – Fix 24/7.
FR-RATE-01..03, FR-TECH-05.
Time-weighted rating calculation and automatic suspension when rating < 3.5 (>= 10 reviews).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApprovalStatus, Review, TechnicianProfile

RECENT_DAYS_WINDOW = 30
RECENT_WEIGHT = 1.5
OLDER_WEIGHT = 1.0


async def update_technician_rating_stats(
    db: AsyncSession,
    tech_user_id: str,
    now: datetime | None = None,
) -> tuple[float, int, bool]:
    """
    FR-RATE-03: Compute time-weighted average rating.
    Reviews in the last 30 days have weight 1.5; older reviews have weight 1.0.
    FR-TECH-05: Automatically suspend technician if rating_avg < 3.5 with >= 10 reviews.

    Returns: (rating_avg, rating_count, was_suspended)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    stmt = select(Review).where(
        Review.to_user_id == tech_user_id,
        Review.from_role == "customer",
    )
    result = await db.execute(stmt)
    reviews = result.scalars().all()

    count = len(reviews)
    if count == 0:
        return 5.0, 0, False

    cutoff = now - timedelta(days=RECENT_DAYS_WINDOW)
    weighted_sum = 0.0
    total_weights = 0.0

    for r in reviews:
        # Check review age
        r_time = r.created_at
        if r_time.tzinfo is None:
            r_time = r_time.replace(tzinfo=timezone.utc)

        weight = RECENT_WEIGHT if r_time >= cutoff else OLDER_WEIGHT
        weighted_sum += r.stars * weight
        total_weights += weight

    rating_avg = round(weighted_sum / total_weights, 2) if total_weights > 0 else 5.0

    # Update technician profile
    tp_stmt = select(TechnicianProfile).where(TechnicianProfile.user_id == tech_user_id)
    tp_res = await db.execute(tp_stmt)
    profile = tp_res.scalar_one_or_none()

    was_suspended = False
    if profile:
        profile.rating_avg = rating_avg
        profile.rating_count = count

        # FR-TECH-05: Auto-suspend if count >= 10 and avg < 3.5
        if count >= 10 and rating_avg < 3.5:
            profile.approval_status = ApprovalStatus.suspended
            profile.is_online = False
            was_suspended = True

        await db.flush()

    return rating_avg, count, was_suspended

