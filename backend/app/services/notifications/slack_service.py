"""Slack webhook notifications for alerts."""
import json
import logging

logger = logging.getLogger(__name__)

_SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
}


def send_slack_alert(
    title: str,
    message: str,
    severity: str,
    tenant_name: str,
    alert_type: str = "",
) -> bool:
    """Post an alert notification to a Slack channel via incoming webhook.

    Returns True if sent successfully, False if disabled or failed.
    All failures are caught and logged — never raises.
    """
    from app.core.config import settings

    if not settings.SLACK_WEBHOOK_URL:
        return False  # Not configured — silent no-op

    try:
        import requests  # already in requirements.txt via httpx indirect dep

        emoji = _SEVERITY_EMOJI.get(severity, "⚪")
        type_label = alert_type.replace("_", " ").title() if alert_type else "Alert"

        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} SentimentAI — {tenant_name}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Alert Type*\n{type_label}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity*\n{severity.upper()}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{title}*\n{message}",
                    },
                },
                {
                    "type": "divider",
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Multilingual Sentiment Dashboard · Automated alert",
                        }
                    ],
                },
            ]
        }

        response = requests.post(
            settings.SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=5,
        )

        if response.status_code == 200 and response.text == "ok":
            logger.info("[Slack] Alert sent successfully")
            return True
        else:
            logger.warning(
                "[Slack] Webhook returned %s: %s",
                response.status_code,
                response.text[:200],
            )
            return False

    except Exception as exc:
        logger.warning("[Slack] Failed to send alert: %s", exc)
        return False
