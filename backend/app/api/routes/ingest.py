import os
import uuid
import logging
import aiofiles
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_analyst
from app.core.config import settings
from app.schemas.ingest import UploadJobStatus, WebhookPayload
from app.models.user import User
from app.services.ingestion.job_tracker import get_job
from app.services.security.audit_logger import log_action

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/upload", response_model=UploadJobStatus)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """
    Upload CSV or Excel file for batch sentiment analysis.
    Returns a job_id to track progress via /ingest/job/{job_id}.
    """
    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read and size-check
    file_bytes = await file.read()
    if len(file_bytes) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    if len(file_bytes) < 10:
        raise HTTPException(status_code=400, detail="File appears to be empty")

    # Save to uploads dir (Celery worker reads from here)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    job_id = str(uuid.uuid4())
    save_path = os.path.join(settings.UPLOAD_DIR, f"{job_id}{ext}")

    async with aiofiles.open(save_path, "wb") as f:
        await f.write(file_bytes)

    # Dispatch Celery task
    from app.tasks.process_batch import process_upload_file
    process_upload_file.delay(
        job_id=job_id,
        file_path=save_path,
        filename=file.filename or f"upload{ext}",
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    # Audit log
    await log_action(
        db=db,
        action="file_upload",
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        resource="upload",
        resource_id=job_id,
        ip_address=request.client.host if request.client else None,
        extra={"filename": file.filename, "size_bytes": len(file_bytes)},
    )

    logger.info(f"Upload job {job_id} queued for tenant {current_user.tenant_id}")

    return UploadJobStatus(
        job_id=job_id,
        status="queued",
        processed_rows=0,
        progress_percent=0.0,
    )


@router.get("/job/{job_id}", response_model=UploadJobStatus)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Poll the live status of a batch upload job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    # Tenant isolation — only the job owner can see it
    if job.get("tenant_id") != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return UploadJobStatus(
        job_id=job["job_id"],
        status=job["status"],
        total_rows=job.get("total_rows"),
        processed_rows=job.get("processed_rows", 0),
        failed_rows=job.get("failed_rows", 0),
        error_message=job.get("error_message"),
        progress_percent=job.get("progress_percent", 0.0),
    )


@router.post("/webhook")
async def receive_webhook(
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive real-time review data from external systems via webhook.
    Validates API key → normalizes → queues each review for NLP processing.
    """
    # Simple API key validation — in production, use tenant-specific keys from DB
    # For now accept any non-empty API key or open endpoint (configurable)
    if not payload.reviews:
        raise HTTPException(status_code=400, detail="No reviews in payload")

    from app.services.ingestion.webhook_handler import normalize_webhook_reviews
    from app.tasks.process_batch import process_single_review

    normalized = normalize_webhook_reviews(payload.reviews)
    if not normalized:
        raise HTTPException(status_code=400, detail="No valid review text found in payload")

    queued = 0
    for record in normalized:
        review_id = str(uuid.uuid4())
        process_single_review.delay(
            review_id=review_id,
            raw_text=record["text"],
            tenant_id="default",  # Phase 7: derive from API key → tenant
            source=record.get("source", payload.source),
            product_id=record.get("product_id"),
            branch_id=record.get("branch_id"),
            external_id=record.get("external_id"),
        )
        queued += 1

    logger.info(f"Webhook received {queued} reviews from source={payload.source}")
    return {"received": queued, "queued": queued, "status": "processing"}
