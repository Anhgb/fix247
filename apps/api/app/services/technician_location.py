"""
Technician location service – Fix 24/7.
FR-BOOK-01, FR-TRACK-02: PostGIS-based nearby technician queries and location updates.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DispatchAttempt, TechnicianProfile, _uuid_default


async def find_nearby_technicians(
    db: AsyncSession,
    lat: float,
    lng: float,
    radius_m: int = 3000,
) -> list[dict]:
    """
    FR-BOOK-01: PostGIS ST_DWithin query.
    Returns online, approved technicians whose location was updated ≤2 minutes ago.
    Result includes: user_id, distance_m, rating_avg, accept_rate.
    """
    two_min_ago = datetime.now(timezone.utc) - timedelta(minutes=2)

    # Use ST_DWithin with geography type (radius in metres)
    # ST_Distance returns metres for geography columns
    stmt = text(
        """
        SELECT
            tp.user_id::text,
            ST_Distance(
                tp.location::geography,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            ) AS distance_m,
            tp.rating_avg,
            tp.approval_status
        FROM technician_profiles tp
        WHERE
            tp.is_online = true
            AND tp.approval_status = 'approved'
            AND tp.location_updated_at > :cutoff
            AND ST_DWithin(
                tp.location::geography,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                :radius_m
            )
        ORDER BY distance_m ASC
        """
    )

    result = await db.execute(
        stmt,
        {"lat": lat, "lng": lng, "radius_m": radius_m, "cutoff": two_min_ago},
    )
    rows = result.mappings().all()

    techs = []
    for row in rows:
        accept_rate = await compute_accept_rate(db, row["user_id"])
        techs.append(
            {
                "user_id": row["user_id"],
                "distance_m": float(row["distance_m"]),
                "rating_avg": float(row["rating_avg"]) if row["rating_avg"] else 0.0,
                "accept_rate": accept_rate,
                "specialty_match": 0.0,  # Caller enriches with specialty data
            }
        )

    return techs


async def update_technician_location(
    db: AsyncSession,
    user_id: str,
    lat: float,
    lng: float,
) -> None:
    """
    FR-TECH-03: Update technician location and location_updated_at timestamp.
    Uses PostGIS point geometry.
    """
    stmt = text(
        """
        UPDATE technician_profiles
        SET
            location = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326),
            location_updated_at = NOW()
        WHERE user_id = :user_id
        """
    )
    await db.execute(stmt, {"user_id": user_id, "lat": lat, "lng": lng})


async def compute_accept_rate(db: AsyncSession, tech_user_id: str, days: int = 30) -> float:
    """
    FR-BOOK-01: Compute technician's acceptance rate over the last N days
    from dispatch_attempts table.
    Returns float 0.0–1.0.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    total_stmt = text(
        """
        SELECT COUNT(*) FROM dispatch_attempts
        WHERE technician_id = :tech_id AND created_at > :cutoff
        """
    )
    accepted_stmt = text(
        """
        SELECT COUNT(*) FROM dispatch_attempts
        WHERE technician_id = :tech_id AND created_at > :cutoff AND response = 'accepted'
        """
    )

    try:
        total_result = await db.execute(total_stmt, {"tech_id": tech_user_id, "cutoff": cutoff})
        total = total_result.scalar() or 0

        if total == 0:
            return 0.5  # Default 50% for new technicians

        accepted_result = await db.execute(accepted_stmt, {"tech_id": tech_user_id, "cutoff": cutoff})
        accepted = accepted_result.scalar() or 0

        return round(accepted / total, 4)
    except Exception:
        return 0.5
