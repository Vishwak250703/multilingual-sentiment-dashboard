"""
Celery tasks for batch CSV/Excel processing and single-review pipeline.
"""
import logging
import uuid
import os
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# How many reviews to insert per DB batch
BATCH_SIZE = 10
# How often to push WebSocket progress (every N rows)
PROGRESS_PUSH_EVERY = 5


@celery_app.task(
    bind=True,
    name="app.tasks.process_batch.process_upload_file",
    queue="nlp",
    max_retries=2,
    acks_late=True,
)
def process_upload_file(self, job_id: str, file_path: str, filename: str, tenant_id: str, user_id: str):
    """
    Full pipeline for an uploaded CSV/Excel file.
    Steps: parse → PII mask → lang detect → translate → sentiment → ABSA → store → embed
    """
    from app.services.ingestion.csv_parser import parse_file
    from app.services.ingestion.pipeline import process_review
    from app.services.ingestion.job_tracker import create_job, update_progress, complete_job, fail_job
    from app.tasks.embed_reviews import embed_review

    logger.info(f"[Job {job_id}] Starting — tenant={tenant_id}, file={filename}")

    # Read file
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
    except FileNotFoundError:
        fail_job(job_id, f"Upload file not found: {file_path}")
        return

    # Parse
    records, parse_errors = parse_file(file_bytes, filename)
    if not records:
        fail_job(job_id, f"No valid rows found. Errors: {parse_errors[:3]}")
        return

    total = len(records)
    create_job(job_id, total, tenant_id)
    logger.info(f"[Job {job_id}] Parsed {total} records, {len(parse_errors)} parse errors")

    # Process each record
    processed = 0
    failed = 0
    db_batch = []

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.models.review import Review

    engine = create_engine(settings.DATABASE_URL_SYNC)
    Session = sessionmaker(bind=engine)

    try:
        for i, record in enumerate(records):
            try:
                enriched = process_review(
                    raw_text=record["text"],
                    tenant_id=tenant_id,
                    source=record.get("source", "csv"),
                    product_id=record.get("product_id"),
                    branch_id=record.get("branch_id"),
                    review_date=record.get("date"),
                )
                db_batch.append(enriched)
                processed += 1

                # Queue embedding (async, non-blocking)
                embed_review.delay(
                    review_id=enriched["id"],
                    text=enriched.get("translated_text") or enriched["raw_text"],
                    tenant_id=tenant_id,
                )

            except Exception as e:
                logger.error(f"[Job {job_id}] Row {i+1} failed: {e}")
                failed += 1

            # Flush batch to DB
            if len(db_batch) >= BATCH_SIZE:
                _flush_to_db(Session, db_batch, job_id)
                db_batch = []

            # Update progress in Redis
            if (i + 1) % PROGRESS_PUSH_EVERY == 0 or i == total - 1:
                update_progress(job_id, processed, failed, total)
                _push_ws_progress(tenant_id, job_id, processed, failed, total)

        # Final flush
        if db_batch:
            _flush_to_db(Session, db_batch, job_id)

        complete_job(job_id, processed, failed, total)
        _push_ws_complete(tenant_id, job_id, processed, failed, total)
        logger.info(f"[Job {job_id}] Done — {processed} processed, {failed} failed")

    except Exception as e:
        logger.exception(f"[Job {job_id}] Fatal error: {e}")
        fail_job(job_id, str(e))
    finally:
        engine.dispose()
        # Clean up temp file
        try:
            os.remove(file_path)
        except Exception:
            pass


def _flush_to_db(Session, batch: list[dict], job_id: str):
    """Bulk insert a batch of review dicts into PostgreSQL."""
    from app.models.review import Review
    session = Session()
    try:
        reviews = [Review(**{k: v for k, v in r.items() if hasattr(Review, k)}) for r in batch]
        session.bulk_save_objects(reviews)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"[Job {job_id}] DB flush error: {e}")
    finally:
        session.close()


def _push_ws_progress(tenant_id: str, job_id: str, processed: int, failed: int, total: int):
    """Publish progress to Redis pub/sub so WebSocket handler can push to clients."""
    try:
        import redis
        from app.core.config import settings
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        import json
        r.publish(f"ws:{tenant_id}", json.dumps({
            "event": "job_progress",
            "job_id": job_id,
            "processed": processed,
            "failed": failed,
            "total": total,
            "progress_percent": round((processed / total) * 100, 1) if total else 0,
        }))
    except Exception as e:
        logger.debug(f"WS push failed (non-critical): {e}")


def _push_ws_complete(tenant_id: str, job_id: str, processed: int, failed: int, total: int):
    try:
        import redis, json
        from app.core.config import settings
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.publish(f"ws:{tenant_id}", json.dumps({
            "event": "job_complete",
            "job_id": job_id,
            "processed": processed,
            "failed": failed,
            "total": total,
        }))
    except Exception as e:
        logger.debug(f"WS complete push failed (non-critical): {e}")


@celery_app.task(
    bind=True,
    name="app.tasks.process_batch.process_single_review",
    queue="nlp",
    max_retries=3,
)
def process_single_review(self, review_id: str, raw_text: str, tenant_id: str,
                           source: str = "webhook", product_id: str = None,
                           branch_id: str = None, external_id: str = None):
    """Single-record pipeline — used by webhook path for real-time processing."""
    from app.services.ingestion.pipeline import process_review
    from app.tasks.embed_reviews import embed_review
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.models.review import Review

    try:
        enriched = process_review(
            raw_text=raw_text,
            tenant_id=tenant_id,
            source=source,
            product_id=product_id,
            branch_id=branch_id,
            external_id=external_id,
        )
        # Override the generated ID with the provided one
        enriched["id"] = review_id

        engine = create_engine(settings.DATABASE_URL_SYNC)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            review = Review(**{k: v for k, v in enriched.items() if hasattr(Review, k)})
            session.add(review)
            session.commit()
        finally:
            session.close()
            engine.dispose()

        embed_review.delay(
            review_id=review_id,
            text=enriched.get("translated_text") or enriched["raw_text"],
            tenant_id=tenant_id,
        )

        # Push WebSocket update
        try:
            import redis, json
            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            r.publish(f"ws:{tenant_id}", json.dumps({
                "event": "new_review",
                "review_id": review_id,
                "sentiment": enriched.get("sentiment"),
            }))
        except Exception:
            pass

        logger.info(f"[Webhook] Review {review_id} processed: {enriched.get('sentiment')}")

    except Exception as e:
        logger.exception(f"[Webhook] Review {review_id} failed: {e}")
        raise self.retry(exc=e, countdown=5)
