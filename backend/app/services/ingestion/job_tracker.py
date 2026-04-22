"""
Redis-based job progress tracker for batch upload jobs.
Stores live progress so the frontend can poll or receive WebSocket updates.
"""
import json
import logging
from typing import Optional
from datetime import datetime, timezone

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

JOB_TTL_SECONDS = 60 * 60 * 24  # 24 hours
JOB_KEY_PREFIX = "job:"


def _get_redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def create_job(job_id: str, total_rows: int, tenant_id: str) -> dict:
    payload = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "status": "processing",
        "total_rows": total_rows,
        "processed_rows": 0,
        "failed_rows": 0,
        "progress_percent": 0.0,
        "error_message": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _get_redis().setex(f"{JOB_KEY_PREFIX}{job_id}", JOB_TTL_SECONDS, json.dumps(payload))
    return payload


def update_progress(job_id: str, processed: int, failed: int, total: int):
    r = _get_redis()
    key = f"{JOB_KEY_PREFIX}{job_id}"
    raw = r.get(key)
    if not raw:
        return
    payload = json.loads(raw)
    payload["processed_rows"] = processed
    payload["failed_rows"] = failed
    payload["progress_percent"] = round((processed / total) * 100, 1) if total else 0
    r.setex(key, JOB_TTL_SECONDS, json.dumps(payload))


def complete_job(job_id: str, processed: int, failed: int, total: int):
    r = _get_redis()
    key = f"{JOB_KEY_PREFIX}{job_id}"
    raw = r.get(key)
    if not raw:
        return
    payload = json.loads(raw)
    payload["status"] = "completed"
    payload["processed_rows"] = processed
    payload["failed_rows"] = failed
    payload["total_rows"] = total
    payload["progress_percent"] = 100.0
    payload["completed_at"] = datetime.now(timezone.utc).isoformat()
    r.setex(key, JOB_TTL_SECONDS, json.dumps(payload))


def fail_job(job_id: str, error_message: str):
    r = _get_redis()
    key = f"{JOB_KEY_PREFIX}{job_id}"
    raw = r.get(key)
    payload = json.loads(raw) if raw else {"job_id": job_id}
    payload["status"] = "failed"
    payload["error_message"] = error_message
    r.setex(key, JOB_TTL_SECONDS, json.dumps(payload))


def get_job(job_id: str) -> Optional[dict]:
    raw = _get_redis().get(f"{JOB_KEY_PREFIX}{job_id}")
    if not raw:
        return None
    return json.loads(raw)
