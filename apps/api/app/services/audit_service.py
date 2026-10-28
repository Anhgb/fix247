"""
Admin Action Audit Trail Service (FR-ADM-01)
Records every mutating action performed by an admin.
"""
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AdminActionLog


async def log_admin_action(
    db: AsyncSession,
    admin_id: str,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> AdminActionLog:
    """
    FR-ADM-01: Record an immutable audit log entry for admin intervention or changes.
    """
    log_entry = AdminActionLog(
        id=str(uuid.uuid4()),
        admin_id=str(admin_id),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        detail=detail or {},
    )
    db.add(log_entry)
    await db.flush()
    return log_entry

