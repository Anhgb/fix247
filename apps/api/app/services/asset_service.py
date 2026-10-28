"""
Asset service – Fix 24/7.
FR-HEALTH-01, FR-HEALTH-02, FR-HEALTH-03.
Handles Asset constraints (max 10/user, unique plate_or_serial per user),
health score calculation, and maintenance reminders.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Asset, AssetType, MaintenanceLog, User, _uuid_default
from app.schemas.assets import (
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    MaintenanceLogResponse,
    MaintenanceReminderResponse,
)

MAX_ASSETS_PER_USER = 10


def calculate_asset_health(
    asset_type: AssetType,
    created_at: datetime,
    last_maintained_at: datetime | None,
) -> tuple[str, list[MaintenanceReminderResponse]]:
    """
    FR-HEALTH-03: Rule-based maintenance schedule.
    - Vehicle:
        Oil change reminder: every 90 days (~2,000 km)
        General inspection: every 180 days (~5,000 km)
    - Appliance:
        Periodic check & cleaning: every 180 days
    """
    now = datetime.now(timezone.utc)
    base_date = last_maintained_at or created_at
    if base_date.tzinfo is None:
        base_date = base_date.replace(tzinfo=timezone.utc)

    days_since = (now - base_date).days
    reminders: list[MaintenanceReminderResponse] = []
    health_status = "good"

    if asset_type == AssetType.vehicle:
        # 90-day oil change rule
        due_date_oil = base_date + timedelta(days=90)
        is_overdue_oil = days_since >= 90
        is_soon_oil = 60 <= days_since < 90

        if is_overdue_oil:
            health_status = "needs_maintenance"
            reminders.append(
                MaintenanceReminderResponse(
                    reminder_type="oil_change",
                    title="Đã đến kỳ thay nhớt xe máy",
                    message=f"Đã {days_since} ngày kể từ lần bảo dưỡng gần nhất (định kỳ 90 ngày / 2.000 km). Thay nhớt định kỳ giúp xe vận hành êm ái và bền bỉ.",
                    due_date=due_date_oil,
                    is_overdue=True,
                )
            )
        elif is_soon_oil:
            health_status = "due_soon"
            reminders.append(
                MaintenanceReminderResponse(
                    reminder_type="oil_change",
                    title="Sắp đến kỳ thay nhớt xe máy",
                    message=f"Còn {90 - days_since} ngày nữa sẽ đến kỳ thay nhớt định kỳ.",
                    due_date=due_date_oil,
                    is_overdue=False,
                )
            )

        # 180-day general inspection
        if days_since >= 180:
            health_status = "needs_maintenance"
            reminders.append(
                MaintenanceReminderResponse(
                    reminder_type="general_check",
                    title="Đến hạn bảo dưỡng toàn diện & bugi",
                    message="Khuyến nghị kiểm tra bugi, lọc gió, phanh và dây curoa/nhông sên đĩa định kỳ 6 tháng.",
                    due_date=base_date + timedelta(days=180),
                    is_overdue=True,
                )
            )
    else:
        # Appliance: 180-day periodic maintenance
        due_date_appliance = base_date + timedelta(days=180)
        is_overdue_app = days_since >= 180
        is_soon_app = 150 <= days_since < 180

        if is_overdue_app:
            health_status = "needs_maintenance"
            reminders.append(
                MaintenanceReminderResponse(
                    reminder_type="cleaning_check",
                    title="Đến kỳ vệ sinh & bảo dưỡng thiết bị",
                    message=f"Đã {days_since} ngày kể từ lần bảo trì gần nhất. Nên vệ sinh lưới lọc, kiểm tra gas và linh kiện để tiết kiệm điện.",
                    due_date=due_date_appliance,
                    is_overdue=True,
                )
            )
        elif is_soon_app:
            health_status = "due_soon"
            reminders.append(
                MaintenanceReminderResponse(
                    reminder_type="cleaning_check",
                    title="Sắp đến hạn bảo dưỡng thiết bị định kỳ",
                    message=f"Còn {180 - days_since} ngày nữa đến hạn bảo dưỡng định kỳ.",
                    due_date=due_date_appliance,
                    is_overdue=False,
                )
            )

    return health_status, reminders


async def check_user_asset_count(db: AsyncSession, user_id: UUID) -> int:
    """Check how many active (non-deleted) assets the user owns."""
    stmt = (
        select(func.count(Asset.id))
        .where(Asset.owner_id == str(user_id), Asset.deleted_at.is_(None))
    )
    res = await db.execute(stmt)
    return res.scalar_one() or 0


async def check_duplicate_plate_or_serial(
    db: AsyncSession, user_id: UUID, plate_or_serial: str, exclude_asset_id: UUID | None = None
) -> bool:
    """Check if the user already has an active asset with the same plate or serial."""
    if not plate_or_serial or not plate_or_serial.strip():
        return False

    cleaned = plate_or_serial.strip().upper()
    stmt = (
        select(Asset)
        .where(
            Asset.owner_id == str(user_id),
            func.upper(Asset.plate_or_serial) == cleaned,
            Asset.deleted_at.is_(None),
        )
    )
    if exclude_asset_id:
        stmt = stmt.where(Asset.id != str(exclude_asset_id))

    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None


async def build_asset_response(db: AsyncSession, asset: Asset) -> AssetResponse:
    """Build AssetResponse with maintenance logs and health reminders."""
    logs_stmt = (
        select(MaintenanceLog)
        .where(MaintenanceLog.asset_id == str(asset.id))
        .order_by(MaintenanceLog.performed_at.desc())
    )
    logs_res = await db.execute(logs_stmt)
    logs = logs_res.scalars().all()

    last_maintained_at = logs[0].performed_at if logs else None
    health_status, reminders = calculate_asset_health(
        asset.asset_type, asset.created_at, last_maintained_at
    )

    log_items: list[MaintenanceLogResponse] = []
    for l in logs:
        tech_name = None
        if l.technician_id:
            tech_user = await db.get(User, l.technician_id)
            if tech_user:
                tech_name = f"Thợ {tech_user.phone[-4:]}"

        log_items.append(
            MaintenanceLogResponse(
                id=UUID(l.id),
                asset_id=UUID(l.asset_id),
                order_id=UUID(l.order_id) if l.order_id else None,
                summary=l.summary,
                parts_replaced=l.parts_replaced,
                labor_cost=l.labor_cost,
                parts_cost=l.parts_cost,
                total_cost=l.total_cost,
                technician_id=UUID(l.technician_id) if l.technician_id else None,
                technician_name=tech_name,
                performed_at=l.performed_at,
                created_at=l.created_at,
            )
        )

    return AssetResponse(
        id=UUID(asset.id),
        owner_id=UUID(asset.owner_id),
        asset_type=asset.asset_type,
        brand=asset.brand,
        model=asset.model,
        year=asset.year,
        plate_or_serial=asset.plate_or_serial,
        location_label=asset.location_label,
        notes=asset.notes,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        maintenance_count=len(logs),
        last_maintained_at=last_maintained_at,
        health_status=health_status,
        recent_logs=log_items,
        reminders=reminders,
    )

