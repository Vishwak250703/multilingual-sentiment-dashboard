"""Celery beat task for periodic alert checking."""
import uuid
import logging
from datetime import datetime, timezone, timedelta

from app.tasks.celery_app import celery_app
from app.services.notifications.email_service import send_alert_email, build_alert_html
from app.services.notifications.slack_service import send_slack_alert

logger = logging.getLogger(__name__)

MIN_REVIEWS_FOR_ALERT = 5   # minimum reviews required in a window to trigger
SPIKE_WINDOW_HOURS = 6      # complaint spike look-back window


@celery_app.task(name="app.tasks.run_alerts.check_all_tenant_alerts", queue="alerts")
def check_all_tenant_alerts():
    """
    Run every ALERT_CHECK_INTERVAL_SECONDS (default 300s).
    Detects:
      - sentiment_drop  : rolling 24h average drops vs prior 24h by >= SENTIMENT_DROP_THRESHOLD
      - complaint_spike : negative review count in last 6h is 2x+ the expected baseline rate
    Creates Alert records only when no unresolved alert of the same type already exists.
    """
    from sqlalchemy import create_engine, select, func, and_
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.models.tenant import Tenant
    from app.models.review import Review
    from app.models.alert import Alert

    engine = create_engine(settings.DATABASE_URL_SYNC)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # ── Get all active tenants ────────────────────────────────
        tenants = session.execute(
            select(Tenant).where(Tenant.is_active == True)  # noqa: E712
        ).scalars().all()

        now = datetime.now(timezone.utc)
        last_24h   = now - timedelta(hours=24)
        prev_24h   = now - timedelta(hours=48)
        last_6h    = now - timedelta(hours=SPIKE_WINDOW_HOURS)

        alerts_created = 0
        tenants_with_new_alerts: set[str] = set()
        # Track (alert_obj, tenant_name) for notifications after commit
        alerts_to_notify: list[tuple] = []

        for tenant in tenants:
            tid = tenant.id

            # ── 1. Sentiment Drop Detection ───────────────────────
            # Current window: last 24 hours
            cur_avg, cur_count = session.execute(
                select(func.avg(Review.sentiment_score), func.count(Review.id))
                .where(and_(
                    Review.tenant_id == tid,
                    Review.sentiment_score.isnot(None),
                    Review.processing_status == "completed",
                    Review.created_at >= last_24h,
                ))
            ).one()

            # Previous window: 24–48 hours ago
            prev_avg, prev_count = session.execute(
                select(func.avg(Review.sentiment_score), func.count(Review.id))
                .where(and_(
                    Review.tenant_id == tid,
                    Review.sentiment_score.isnot(None),
                    Review.processing_status == "completed",
                    Review.created_at >= prev_24h,
                    Review.created_at < last_24h,
                ))
            ).one()

            if (
                cur_avg is not None
                and prev_avg is not None
                and (cur_count or 0) >= MIN_REVIEWS_FOR_ALERT
                and (prev_count or 0) >= MIN_REVIEWS_FOR_ALERT
            ):
                drop = float(prev_avg) - float(cur_avg)
                if drop >= settings.SENTIMENT_DROP_THRESHOLD:
                    # Only fire if no open sentiment_drop alert exists
                    existing = session.execute(
                        select(Alert).where(and_(
                            Alert.tenant_id == tid,
                            Alert.alert_type == "sentiment_drop",
                            Alert.is_resolved == False,  # noqa: E712
                        ))
                    ).scalar_one_or_none()

                    if not existing:
                        severity = "critical" if drop >= 0.4 else "high" if drop >= 0.3 else "medium"
                        alert = Alert(
                            id=str(uuid.uuid4()),
                            tenant_id=tid,
                            alert_type="sentiment_drop",
                            severity=severity,
                            title="Sentiment Drop Detected",
                            message=(
                                f"Average sentiment score dropped by {drop:.1%} over the last 24 hours "
                                f"(from {float(prev_avg):.2f} to {float(cur_avg):.2f}). "
                                f"Based on {cur_count} recent reviews."
                            ),
                            alert_metadata={
                                "drop_percent": round(drop * 100, 1),
                                "current_avg": round(float(cur_avg), 3),
                                "previous_avg": round(float(prev_avg), 3),
                                "current_count": cur_count,
                                "period": "last_24h",
                            },
                        )
                        session.add(alert)
                        alerts_created += 1
                        tenants_with_new_alerts.add(tid)
                        alerts_to_notify.append((alert, tenant.name))
                        logger.info(
                            f"[Alerts] Tenant {tid}: sentiment_drop created "
                            f"(drop={drop:.3f}, severity={severity})"
                        )

            # ── 2. Complaint Spike Detection ──────────────────────
            # Spike window: last SPIKE_WINDOW_HOURS hours
            spike_count = session.execute(
                select(func.count(Review.id))
                .where(and_(
                    Review.tenant_id == tid,
                    Review.sentiment == "negative",
                    Review.processing_status == "completed",
                    Review.created_at >= last_6h,
                ))
            ).scalar() or 0

            # Baseline: negative reviews in the 18h window before the spike window
            baseline_count = session.execute(
                select(func.count(Review.id))
                .where(and_(
                    Review.tenant_id == tid,
                    Review.sentiment == "negative",
                    Review.processing_status == "completed",
                    Review.created_at >= last_24h,
                    Review.created_at < last_6h,
                ))
            ).scalar() or 0

            # Expected rate: scale baseline (18h) to 6h window
            expected_in_6h = (baseline_count / 18) * SPIKE_WINDOW_HOURS if baseline_count else 0

            is_spike = (
                spike_count >= MIN_REVIEWS_FOR_ALERT
                and (expected_in_6h == 0 or spike_count > expected_in_6h * 2)
            )

            if is_spike:
                existing = session.execute(
                    select(Alert).where(and_(
                        Alert.tenant_id == tid,
                        Alert.alert_type == "complaint_spike",
                        Alert.is_resolved == False,  # noqa: E712
                    ))
                ).scalar_one_or_none()

                if not existing:
                    severity = "critical" if spike_count > expected_in_6h * 4 else "high"
                    alert = Alert(
                        id=str(uuid.uuid4()),
                        tenant_id=tid,
                        alert_type="complaint_spike",
                        severity=severity,
                        title="Complaint Spike Detected",
                        message=(
                            f"{spike_count} negative reviews in the last {SPIKE_WINDOW_HOURS} hours "
                            f"(expected ~{expected_in_6h:.0f} based on recent baseline). "
                            "Immediate attention recommended."
                        ),
                        alert_metadata={
                            "spike_count": spike_count,
                            "expected_count": round(expected_in_6h, 1),
                            "window_hours": SPIKE_WINDOW_HOURS,
                            "multiplier": round(spike_count / expected_in_6h, 1) if expected_in_6h else None,
                        },
                    )
                    session.add(alert)
                    alerts_created += 1
                    tenants_with_new_alerts.add(tid)
                    alerts_to_notify.append((alert, tenant.name))
                    logger.info(
                        f"[Alerts] Tenant {tid}: complaint_spike created "
                        f"(count={spike_count}, expected={expected_in_6h:.1f})"
                    )

        session.commit()

        # ── Send Email + Slack notifications ──────────────────────
        if alerts_to_notify:
            from sqlalchemy import select as _select
            from app.models.user import User as _User
            from app.core.config import settings as _settings

            for alert_obj, tenant_name in alerts_to_notify:
                # Fetch admin emails for this tenant
                admin_emails = [
                    row[0] for row in session.execute(
                        _select(_User.email).where(
                            _User.tenant_id == alert_obj.tenant_id,
                            _User.role == "admin",
                            _User.is_active.is_(True),
                        )
                    ).all()
                ]
                # Fall back to configured recipients if tenant has no admins yet
                if not admin_emails:
                    admin_emails = _settings.alert_email_recipients_list

                subject = f"[{alert_obj.severity.upper()}] {alert_obj.title} — {tenant_name}"
                html = build_alert_html(
                    alert_type=alert_obj.alert_type,
                    title=alert_obj.title,
                    message=alert_obj.message,
                    severity=alert_obj.severity,
                    tenant_name=tenant_name,
                )
                send_alert_email(subject, html, admin_emails)

                send_slack_alert(
                    title=alert_obj.title,
                    message=alert_obj.message,
                    severity=alert_obj.severity,
                    tenant_name=tenant_name,
                    alert_type=alert_obj.alert_type,
                )

        # ── Notify connected WebSocket clients for tenants that got new alerts
        if tenants_with_new_alerts:
            try:
                import redis as _redis
                import json as _json
                _r = _redis.from_url(settings.REDIS_URL, decode_responses=True)
                for _tid in tenants_with_new_alerts:
                    _r.publish(f"ws:{_tid}", _json.dumps({"event": "new_alert"}))
                _r.close()
            except Exception as _e:
                logger.debug(f"[Alerts] WS publish failed (non-critical): {_e}")

        logger.info(
            f"[Alerts] Check complete — {len(tenants)} tenants scanned, "
            f"{alerts_created} new alert(s) created"
        )
        return {
            "status": "checked",
            "tenants_scanned": len(tenants),
            "alerts_created": alerts_created,
        }

    except Exception as e:
        session.rollback()
        logger.exception(f"[Alerts] Fatal error during alert check: {e}")
        return {"status": "error", "error": str(e)}

    finally:
        session.close()
        engine.dispose()
