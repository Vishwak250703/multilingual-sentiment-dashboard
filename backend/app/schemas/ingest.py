from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class WebhookPayload(BaseModel):
    source: str  # app_review | social | support_ticket | chat_log
    reviews: List[Dict[str, Any]]
    # Each item: {"text": "...", "rating": 4, "product_id": "...", "branch_id": "..."}
    api_key: Optional[str] = None


class UploadJobStatus(BaseModel):
    job_id: str
    status: str  # queued | processing | completed | failed
    total_rows: Optional[int] = None
    processed_rows: Optional[int] = None
    failed_rows: Optional[int] = None
    error_message: Optional[str] = None
    progress_percent: Optional[float] = None
