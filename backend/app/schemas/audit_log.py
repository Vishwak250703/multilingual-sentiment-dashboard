from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class AuditLogOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    action: str
    resource: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogPaginated(BaseModel):
    items: List[AuditLogOut]
    total: int
    page: int
    page_size: int
    total_pages: int
