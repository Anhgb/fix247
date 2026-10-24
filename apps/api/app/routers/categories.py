"""
Categories router – /api/v1/categories
"""
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import ServiceCategory, FaultCatalog

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all active service categories."""
    stmt = (
        select(ServiceCategory)
        .where(ServiceCategory.is_active.is_(True))
        .order_by(ServiceCategory.sort_order.asc())
    )
    res = await db.execute(stmt)
    cats = res.scalars().all()

    data = [
        {
            "id": c.id,
            "name": c.name,
            "group": c.group.value if hasattr(c.group, "value") else str(c.group),
            "icon": c.icon,
            "sort_order": c.sort_order,
        }
        for c in cats
    ]
    return {"success": True, "data": data}
