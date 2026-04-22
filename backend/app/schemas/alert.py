from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class AlertOut(BaseModel):
    id: str
    tenant_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    alert_metadata: Optional[Dict[str, Any]] = Field(None, serialization_alias="metadata")
    is_resolved: bool
    triggered_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class AlertListResponse(BaseModel):
    items: List[AlertOut]
    unresolved_count: int
    total: int
