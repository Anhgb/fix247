"""
Maintenance Reminders Dispatcher – Fix 24/7.
FR-HEALTH-03, SRS §7.
Checks active assets against time/km intervals and dispatches notifications
via NotificationService interface (MockPushProvider + MockOTPProvider / SMS).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    Asset,
    MaintenanceLog,
    Notification,
    NotificationChannel,
    User,
    _uuid_default,
)
from app.providers.otp import get_otp_provider
from app.providers.push import get_push_provider
from app.services.asset_service import calculate_asset_health

logger = get_logger(__name__)


async def check_and_send_maintenance_reminders(db: AsyncSession) -> int:
    """
    FR-HEALTH-03: Scan all active assets and send reminders if maintenance is due.
    Prevents duplicate notifications within 30 days for the same reminder type.
    Returns the number of notifications sent.
    """
    stmt = select(Asset).where(Asset.deleted_at.is_(None))
    res = await db.execute(stmt)
    assets = res.scalars().all()

    sent_count = 0
    now = datetime.now(timezone.utc)
    push_provider = get_push_provider()
    otp_provider = get_otp_provider()

    for asset in assets:
        # Get last maintenance
        logs_stmt = (
            select(MaintenanceLog)
            .where(MaintenanceLog.asset_id == str(asset.id))
            .order_by(MaintenanceLog.performed_at.desc())
        )
        logs_res = await db.execute(logs_stmt)
        last_log = logs_res.scalars().first()

        last_date = last_log.performed_at if last_log else asset.created_at
        _, reminders = calculate_asset_health(asset.asset_type, asset.created_at, last_date)

        for rem in reminders:
            if not rem.is_overdue:
                continue

            # Check if notification already sent in last 30 days
            cutoff_30d = now - timedelta(days=30)
            existing_notif_stmt = select(Notification).where(
                Notification.user_id == asset.owner_id,
                Notification.notification_type == f"maintenance_reminder:{rem.reminder_type}",
                Notification.created_at >= cutoff_30d,
            )
            existing = (await db.execute(existing_notif_stmt)).scalar_one_or_none()
            if existing:
                continue

            owner = await db.get(User, asset.owner_id)
            if not owner:
                continue

            device_name = f"{asset.brand or ''} {asset.model or ''}".strip() or "thiết bị của bạn"
            title = f"Fix 24/7 – {rem.title}"
            body = f"Thiết bị '{device_name}' {rem.message}"

            # 1. Store in-app notification
            notif = Notification(
                id=_uuid_default(),
                user_id=asset.owner_id,
                notification_type=f"maintenance_reminder:{rem.reminder_type}",
                title=title,
                body=body,
                payload={
                    "asset_id": str(asset.id),
                    "reminder_type": rem.reminder_type,
                    "due_date": rem.due_date.isoformat() if rem.due_date else None,
                },
                channel=NotificationChannel.in_app,
            )
            db.add(notif)

            # 2. Dispatch via MockPushProvider
            try:
                await push_provider.send_notification(
                    user_id=str(asset.owner_id),
                    title=title,
                    body=body,
                    data={"asset_id": str(asset.id)},
                )
            except Exception as e:
                logger.warning("push_reminder_failed", error=str(e))

            # 3. Dispatch via Mock SMS if phone available
            if owner.phone:
                try:
                    await otp_provider.send_sms(
                        phone=owner.phone,
                        message=f"[Fix 24/7] {title}: {body}",
                    )
                except Exception as e:
                    logger.warning("sms_reminder_failed", error=str(e))

            sent_count += 1

    if sent_count > 0:
        await db.commit()

    return sent_count

