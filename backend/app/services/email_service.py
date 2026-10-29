from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("itam.email")

EMAIL_STATUS_SKIPPED = "SKIPPED"
EMAIL_STATUS_SENT = "SENT"
EMAIL_STATUS_FAILED = "FAILED"


class EmailNotifier:
    @property
    def enabled(self) -> bool:
        return settings.REMINDER_EMAIL_ENABLED

    def _recipients(self) -> list[str]:
        return [
            item.strip()
            for item in settings.REMINDER_EMAIL_TO.replace(";", ",").split(",")
            if item.strip()
        ]

    async def send_digest(self, subject: str, body: str) -> str:
        if not self.enabled:
            return EMAIL_STATUS_SKIPPED
        recipients = self._recipients()
        if not recipients or not settings.SMTP_HOST:
            logger.warning(
                "reminder email is enabled but SMTP_HOST or REMINDER_EMAIL_TO is empty"
            )
            return EMAIL_STATUS_SKIPPED
        try:
            await asyncio.to_thread(self._send, subject, body, recipients)
            return EMAIL_STATUS_SENT
        except Exception:  # noqa: BLE001 - email failure must not break reminders
            logger.exception("send reminder email failed")
            return EMAIL_STATUS_FAILED

    def _send(self, subject: str, body: str, recipients: list[str]) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = (
            settings.SMTP_FROM or settings.SMTP_USERNAME or "itam@localhost"
        )
        message["To"] = ", ".join(recipients)
        message.set_content(body)
        with smtplib.SMTP(
            settings.SMTP_HOST, settings.SMTP_PORT, timeout=20
        ) as smtp:
            smtp.ehlo()
            if settings.SMTP_USE_TLS:
                smtp.starttls()
                smtp.ehlo()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
