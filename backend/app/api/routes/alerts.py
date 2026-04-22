from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.schemas.alert import AlertListResponse, AlertOut
from app.models.alert import Alert
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    resolved: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    filters = [Alert.tenant_id == current_user.tenant_id]
    if not resolved:
        filters.append(Alert.is_resolved == False)  # noqa

    result = await db.execute(
        select(Alert).where(and_(*filters)).order_by(Alert.triggered_at.desc()).limit(50)
    )
    items = result.scalars().all()

    count_result = await db.execute(
        select(func.count()).select_from(Alert).where(
            Alert.tenant_id == current_user.tenant_id,
            Alert.is_resolved == False  # noqa
        )
    )
    unresolved = count_result.scalar()
    total_result = await db.execute(
        select(func.count()).select_from(Alert).where(Alert.tenant_id == current_user.tenant_id)
    )
    total = total_result.scalar()

    return AlertListResponse(items=items, unresolved_count=unresolved, total=total)


@router.post("/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.tenant_id == current_user.tenant_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    return alert
