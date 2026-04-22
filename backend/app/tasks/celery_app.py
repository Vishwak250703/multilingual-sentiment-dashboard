from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "sentiment_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.process_batch",
        "app.tasks.run_alerts",
        "app.tasks.embed_reviews",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.process_batch.*": {"queue": "nlp"},
        "app.tasks.embed_reviews.*": {"queue": "nlp"},
        "app.tasks.run_alerts.*": {"queue": "alerts"},
    },
    beat_schedule={
        "check-alerts-every-5-minutes": {
            "task": "app.tasks.run_alerts.check_all_tenant_alerts",
            "schedule": settings.ALERT_CHECK_INTERVAL_SECONDS,
        },
    },
)
