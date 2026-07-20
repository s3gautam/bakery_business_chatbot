import asyncio
import smtplib
from email.message import EmailMessage

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings

logger = structlog.get_logger(__name__)


class EmailNotConfiguredError(RuntimeError):
    pass


class EmailService:
    """SMTP (Gmail) email sender with retry on transient failures. Used
    to send feedback and, in a later stage, order confirmations — since
    this app has no database, email is the only durable record.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _send_sync(self, to_address: str, subject: str, body: str) -> None:
        if not self._settings.email_configured:
            raise EmailNotConfiguredError(
                "SMTP_USERNAME/SMTP_PASSWORD are not set — cannot send email."
            )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._settings.smtp_username
        message["To"] = to_address
        message.set_content(body)

        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port) as server:
            server.starttls()
            server.login(self._settings.smtp_username, self._settings.smtp_password)
            server.send_message(message)

    async def send(self, to_address: str, subject: str, body: str) -> None:
        try:
            await asyncio.to_thread(self._send_sync, to_address, subject, body)
        except EmailNotConfiguredError:
            logger.warning("email_not_configured", to=to_address, subject=subject)
            raise
        except Exception:
            logger.error("email_send_failed", to=to_address, subject=subject)
            raise
