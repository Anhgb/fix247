"""
Assets & Digital Health Log Router – Fix 24/7.
FR-HEALTH-01, FR-HEALTH-02, FR-HEALTH-03, UC-09.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_customer
from app.models import Asset, User, _uuid_default
from app.schemas.assets import (
    AssetCreate,
    AssetListResponse,
    AssetResponse,
    AssetUpdate,
    MaintenanceReminderResponse,
)
from app.services.asset_service import (
    MAX_ASSETS_PER_USER,
    build_asset_response,
    check_duplicate_plate_or_serial,
    check_user_asset_count,
)

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    payload: AssetCreate,
    current_user: User = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-HEALTH-01: Register vehicle or appliance asset.
    - Max 10 assets per user.
    - Unique plate/serial per user.
    """
    user_uuid = UUID(current_user.id)

    # 1. Check max assets limit (max 10)
    current_count = await check_user_asset_count(db, user_uuid)
    if current_count >= MAX_ASSETS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "MAX_ASSETS_REACHED",
                    "message": f"Bạn đã đạt giới hạn tối đa {MAX_ASSETS_PER_USER} phương tiện/thiết bị (FR-HEALTH-01).",
                }
            },
        )

    # 2. Check duplicate plate or serial
    if payload.plate_or_serial:
        is_dup = await check_duplicate_plate_or_serial(db, user_uuid, payload.plate_or_serial)
        if is_dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "DUPLICATE_PLATE_OR_SERIAL",
                        "message": f"Bạn đã đăng ký thiết bị có biển số / serial '{payload.plate_or_serial}' rồi.",
                    }
                },
            )

    asset = Asset(
        id=_uuid_default(),
        owner_id=current_user.id,
        asset_type=payload.asset_type,
        brand=payload.brand.strip(),
        model=payload.model.strip(),
        year=payload.year,
        plate_or_serial=payload.plate_or_serial.strip() if payload.plate_or_serial else None,
        location_label=payload.location_label.strip() if payload.location_label else None,
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    return await build_asset_response(db, asset)


@router.get("", response_model=AssetListResponse)
async def list_user_assets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active assets belonging to current user."""
    stmt = (
        select(Asset)
        .where(Asset.owner_id == current_user.id, Asset.deleted_at.is_(None))
        .order_by(Asset.created_at.desc())
    )
    res = await db.execute(stmt)
    assets = res.scalars().all()

    items = [await build_asset_response(db, a) for a in assets]
    return AssetListResponse(total=len(items), items=items)


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset_detail(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    FR-HEALTH-02: Get asset Digital Health Log with full maintenance timeline.
    """
    stmt = select(Asset).where(Asset.id == str(asset_id), Asset.deleted_at.is_(None))
    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ASSET_NOT_FOUND", "message": "Không tìm thấy thiết bị."}},
        )

    # Must be owner or admin/technician with assigned order
    if asset.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Bạn không có quyền xem thiết bị này."}},
        )

    return await build_asset_response(db, asset)


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: UUID,
    payload: AssetUpdate,
    current_user: User = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Update asset information."""
    stmt = select(Asset).where(Asset.id == str(asset_id), Asset.deleted_at.is_(None))
    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ASSET_NOT_FOUND", "message": "Không tìm thấy thiết bị."}},
        )

    if asset.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Bạn không phải chủ sở hữu thiết bị này."}},
        )

    if payload.plate_or_serial and payload.plate_or_serial != asset.plate_or_serial:
        is_dup = await check_duplicate_plate_or_serial(
            db, UUID(current_user.id), payload.plate_or_serial, exclude_asset_id=asset_id
        )
        if is_dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "DUPLICATE_PLATE_OR_SERIAL",
                        "message": f"Bạn đã đăng ký thiết bị khác có biển số/serial '{payload.plate_or_serial}' rồi.",
                    }
                },
            )
        asset.plate_or_serial = payload.plate_or_serial.strip()

    if payload.brand is not None:
        asset.brand = payload.brand.strip()
    if payload.model is not None:
        asset.model = payload.model.strip()
    if payload.year is not None:
        asset.year = payload.year
    if payload.location_label is not None:
        asset.location_label = payload.location_label.strip()
    if payload.notes is not None:
        asset.notes = payload.notes.strip()

    await db.commit()
    await db.refresh(asset)
    return await build_asset_response(db, asset)


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: UUID,
    current_user: User = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete an asset."""
    stmt = select(Asset).where(Asset.id == str(asset_id), Asset.deleted_at.is_(None))
    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ASSET_NOT_FOUND", "message": "Không tìm thấy thiết bị."}},
        )

    if asset.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Bạn không phải chủ sở hữu thiết bị này."}},
        )

    asset.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return {"ok": True, "message": "Đã xóa thiết bị thành công."}


@router.get("/{asset_id}/reminders", response_model=list[MaintenanceReminderResponse])
async def get_asset_reminders(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get maintenance reminders for an asset."""
    stmt = select(Asset).where(Asset.id == str(asset_id), Asset.deleted_at.is_(None))
    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "ASSET_NOT_FOUND", "message": "Không tìm thấy thiết bị."}},
        )

    resp = await build_asset_response(db, asset)
    return resp.reminders

