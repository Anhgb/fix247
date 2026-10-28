"""
Public QR Location Landing Router – Fix 24/7 (Phase P5)
Requirements: UC-12, FR-QR-01, FR-QR-02, AT-08.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import QRLocation
from app.schemas.qr import QRLocationPublicResponse

router = APIRouter(prefix="/qr", tags=["qr"])


@router.get("/{code}", response_model=QRLocationPublicResponse)
async def resolve_qr_code(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    UC-12, AT-08: Resolve QR location code.
    Increments scan_count and returns prefilled address info.
    If code is invalid or inactive, returns 404.
    """
    stmt = select(QRLocation).where(
        QRLocation.code == code.strip(),
        QRLocation.is_active == True,
    )
    loc = (await db.execute(stmt)).scalar_one_or_none()
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "QR_NOT_FOUND", "message": "Mã QR địa điểm không tồn tại hoặc đã ngưng hoạt động."}},
        )

    # Increment scan count
    loc.scan_count += 1
    await db.commit()

    return QRLocationPublicResponse(
        id=str(loc.id),
        code=loc.code,
        name=loc.name,
        location_type=loc.location_type,
        address=loc.address,
        lat=float(loc.lat) if loc.lat else None,
        lng=float(loc.lng) if loc.lng else None,
    )

