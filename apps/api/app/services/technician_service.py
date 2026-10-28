"""
Technician service – Fix 24/7.
FR-TECH-01, FR-TECH-02, FR-TECH-03, FR-TECH-04, FR-TECH-05, UC-08.
Handles profile onboarding, CCCD encryption/masking, badges calculation,
and 5-minute auto-offline worker.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt, encrypt
from app.core.logging import get_logger
from app.models import ApprovalStatus, TechnicianProfile
from app.schemas.technician import TechBadge

logger = get_logger(__name__)


def compute_technician_badges(profile: TechnicianProfile) -> list[TechBadge]:
    """Calculate badges earned by technician based on stats and specialties."""
    badges: list[TechBadge] = []
    rating_avg = float(profile.rating_avg) if profile.rating_avg else 5.0
    rating_count = profile.rating_count or 0
    specialties = profile.specialties or []

    if rating_avg >= 4.8 and rating_count >= 5:
        badges.append(
            TechBadge(
                id="five_star",
                name="Thợ 5 Sao",
                description="Đánh giá trung bình xuất sắc từ 4.8 sao trở lên",
                icon="⭐",
            )
        )

    if rating_count >= 10:
        badges.append(
            TechBadge(
                id="hard_working",
                name="Thợ Chăm Chỉ",
                description="Đã hoàn thành xuất sắc trên 10 đơn cứu hộ",
                icon="🔥",
            )
        )

    if "motorbike" in specialties:
        badges.append(
            TechBadge(
                id="motorbike_expert",
                name="Chuyên Gia Xe Máy",
                description="Chứng chỉ chuyên sâu sửa chữa và cứu hộ xe máy",
                icon="🏍️",
            )
        )

    if any(s in specialties for s in ["air_conditioner", "refrigerator", "washing_machine"]):
        badges.append(
            TechBadge(
                id="appliance_expert",
                name="Chuyên Gia Điện Lạnh",
                description="Kỹ thuật viên lành nghề thiết bị gia dụng và điện lạnh",
                icon="❄️",
            )
        )

    if profile.debt_amount == 0 and rating_count >= 3:
        badges.append(
            TechBadge(
                id="trusted_partner",
                name="Đối Tác Tin Cậy",
                description="Lịch sử đối soát uy tín, không nợ đọng hoa hồng",
                icon="🛡️",
            )
        )

    return badges


def mask_id_number(encrypted_or_plain: str) -> str:
    """Mask national ID number so only last 4 digits are shown: '******1234'."""
    try:
        plain = decrypt(encrypted_or_plain)
    except Exception:
        plain = encrypted_or_plain

    if len(plain) >= 4:
        return "*" * (len(plain) - 4) + plain[-4:]
    return "******"


async def auto_offline_inactive_technicians(db: AsyncSession) -> int:
    """
    FR-TECH-03, DECISIONS A-14:
    Auto-offline technicians after 5 minutes without location pings.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    stmt = (
        select(TechnicianProfile)
        .where(
            TechnicianProfile.is_online.is_(True),
            or_(
                TechnicianProfile.location_updated_at.is_(None),
                TechnicianProfile.location_updated_at < cutoff,
            ),
        )
    )
    res = await db.execute(stmt)
    stale_techs = res.scalars().all()

    count = 0
    for tech in stale_techs:
        tech.is_online = False
        tech.location_updated_at = None
        count += 1
        logger.info("tech_auto_offline_inactivity", tech_id=str(tech.id), user_id=str(tech.user_id))

    if count > 0:
        await db.commit()

    return count

