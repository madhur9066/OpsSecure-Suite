"""modules/email_utils.py — SMTP alert sender (config-driven, no hardcoded addresses)."""
import smtplib
import logging
from email.mime.text import MIMEText
from flask import current_app

logger = logging.getLogger(__name__)


def send_alert(subject: str, body: str, to_email: str) -> None:
    """
    Send a plain-text alert email using the SMTP settings from app config.
    Raises on failure so the caller can decide whether to retry / log.
    """
    smtp_server = current_app.config["SMTP_SERVER"]
    smtp_port   = current_app.config["SMTP_PORT"]
    from_email  = current_app.config["EMAIL_FROM"]

    msg             = MIMEText(body)
    msg["Subject"]  = subject
    msg["From"]     = from_email
    msg["To"]       = to_email

    with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
        server.ehlo()
        # Use STARTTLS if the server supports it
        if server.has_extn("STARTTLS"):
            server.starttls()
            server.ehlo()
        server.send_message(msg)

    logger.info("Alert email sent to %s: %s", to_email, subject)
