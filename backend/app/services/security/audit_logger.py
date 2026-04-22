"""
Audit logging service — records all significant user actions to the database.
"""
import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def log_action(
    db: AsyncSession,
    action: str,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    resource: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra: Optional[dict] = None,
):
    """Write an audit log entry to the database."""
    try:
        from app.models.audit_log import AuditLog
        log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            extra=extra,
        )
        db.add(log)
        # Don't commit here — let the request lifecycle handle it
    except Exception as e:
        logger.error(f"Audit log write failed: {e}")
