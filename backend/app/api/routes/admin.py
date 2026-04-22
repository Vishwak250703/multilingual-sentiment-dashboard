from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
import uuid
import math

from app.core.database import get_db
from app.core.auth import require_admin, hash_password
from app.schemas.auth import UserOut, UserCreate, UserUpdate
from app.schemas.audit_log import AuditLogOut, AuditLogPaginated
from app.models.user import User
from app.models.audit_log import AuditLog

router = APIRouter()


@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(User).where(User.tenant_id == current_user.tenant_id)
    )
    return result.scalars().all()


@router.post("/users", response_model=UserOut)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Enforce tenant isolation — new user must belong to same tenant
    body.tenant_id = current_user.tenant_id

    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        tenant_id=body.tenant_id,
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    return {"message": "User deleted"}


@router.get("/audit-logs", response_model=AuditLogPaginated)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List audit log entries for the current tenant, newest first."""
    count_result = await db.execute(
        select(func.count()).select_from(AuditLog)
        .where(AuditLog.tenant_id == current_user.tenant_id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .where(AuditLog.tenant_id == current_user.tenant_id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset).limit(page_size)
    )
    logs = result.scalars().all()

    items = [
        AuditLogOut(
            id=log.id,
            user_id=log.user_id,
            user_email=log.user.email if log.user else None,
            user_full_name=log.user.full_name if log.user else None,
            action=log.action,
            resource=log.resource,
            resource_id=log.resource_id,
            ip_address=log.ip_address,
            extra=log.extra,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return AuditLogPaginated(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 1,
    )
