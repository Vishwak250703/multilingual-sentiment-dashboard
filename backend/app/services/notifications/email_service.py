"""SMTP email notifications for alerts."""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

logger = logging.getLogger(__name__)


def send_alert_email(subject: str, body_html: str, recipients: List[str]) -> bool:
    """Send an HTML alert email via SMTP.

    Returns True if sent successfully, False if disabled or failed.
    All failures are caught and logged — never raises.
    """
    from app.core.config import settings

    if not settings.SMTP_HOST or not recipients:
        return False  # Not configured — silent no-op

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            if settings.SMTP_TLS:
                server.starttls()
                server.ehlo()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, recipients, msg.as_string())

        logger.info("[Email] Alert sent to %s", recipients)
        return True

    except Exception as exc:
        logger.warning("[Email] Failed to send alert email: %s", exc)
        return False


def build_alert_html(
    alert_type: str,
    title: str,
    message: str,
    severity: str,
    tenant_name: str,
) -> str:
    """Return a styled HTML email body for an alert notification."""
    severity_color = {
        "critical": "#ef4444",
        "high": "#f97316",
        "medium": "#f59e0b",
        "low": "#3b82f6",
    }.get(severity, "#6b7280")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#0f0f19;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#0f0f19;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:rgba(255,255,255,0.04);
                      border:1px solid rgba(255,255,255,0.08);
                      border-radius:16px;overflow:hidden;max-width:600px;">

          <!-- Header gradient bar -->
          <tr>
            <td style="background:linear-gradient(135deg,#7c3aed,#2563eb);
                       padding:28px 32px;">
              <h1 style="margin:0;color:#fff;font-size:20px;font-weight:700;
                         letter-spacing:-0.02em;">
                SentimentAI Alerts
              </h1>
              <p style="margin:4px 0 0;color:rgba(255,255,255,0.65);font-size:13px;">
                {tenant_name}
              </p>
            </td>
          </tr>

          <!-- Severity badge -->
          <tr>
            <td style="padding:24px 32px 0;">
              <span style="display:inline-block;
                           background:{severity_color}22;
                           border:1px solid {severity_color}55;
                           color:{severity_color};
                           padding:4px 14px;border-radius:999px;
                           font-size:11px;font-weight:700;
                           text-transform:uppercase;letter-spacing:0.07em;">
                {severity.upper()}
              </span>
              &nbsp;
              <span style="color:rgba(255,255,255,0.35);font-size:11px;
                           text-transform:uppercase;letter-spacing:0.05em;">
                {alert_type.replace("_", " ")}
              </span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:16px 32px 32px;">
              <h2 style="margin:0 0 12px;color:#fff;font-size:18px;font-weight:600;">
                {title}
              </h2>
              <p style="margin:0 0 28px;color:rgba(255,255,255,0.65);
                        font-size:14px;line-height:1.65;">
                {message}
              </p>
              <a href="#"
                 style="display:inline-block;
                        background:linear-gradient(135deg,#7c3aed,#2563eb);
                        color:#fff;text-decoration:none;
                        padding:11px 26px;border-radius:10px;
                        font-size:14px;font-weight:600;">
                View Dashboard →
              </a>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:16px 32px;
                       border-top:1px solid rgba(255,255,255,0.07);">
              <p style="margin:0;color:rgba(255,255,255,0.28);font-size:12px;">
                Multilingual Sentiment Dashboard · Automated alert notification
                <br>You are receiving this because you are an admin user of {tenant_name}.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
