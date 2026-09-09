"""In-app email composition and dispatch service for ETL Rationalisation recommendations."""

from __future__ import annotations

import html
import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Protocol, runtime_checkable

from backend.app.config import Settings, get_settings

logger = logging.getLogger("awa.email_service")

# Standard RFC 5322 compatible email validation pattern
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)


class EmailServiceError(Exception):
    """Base exception for email service errors."""


class EmailValidationError(EmailServiceError):
    """Raised when email parameters (recipient, subject, body) fail validation."""


class EmailDeliveryError(EmailServiceError):
    """Raised when email transport or dispatch fails."""


@runtime_checkable
class EmailTransport(Protocol):
    """Protocol for pluggable email transports (SMTP or Mock)."""

    def send_email(
        self,
        from_addr: str,
        to_addrs: list[str],
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        """Send an email to one or more recipients."""
        ...


class SMTPEmailTransport:
    """Production SMTP email transport using Python standard library smtplib."""

    def __init__(
        self,
        host: str | None = None,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        timeout: float = 15.0,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.timeout = timeout

    def send_email(
        self,
        from_addr: str,
        to_addrs: list[str],
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        if not self.host:
            raise EmailDeliveryError(
                "SMTP host is not configured on the server. Please set SMTP_HOST environment variable."
            )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs)

        # Plain text version (RFC standard)
        msg.attach(MIMEText(text_body, "plain", "utf-8"))

        # Optional HTML version
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if self.port == 465:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)

            with server:
                if self.use_tls and self.port != 465:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
                logger.info(
                    "Email sent successfully via SMTP to %s (subject: '%s')",
                    to_addrs,
                    subject,
                )
        except smtplib.SMTPAuthenticationError as e:
            logger.error("SMTP authentication failed for host %s: %s", self.host, e)
            raise EmailDeliveryError("SMTP authentication failed. Please check server credentials.") from e
        except smtplib.SMTPConnectError as e:
            logger.error("Failed to connect to SMTP server %s:%s: %s", self.host, self.port, e)
            raise EmailDeliveryError(f"Failed to connect to SMTP server at {self.host}:{self.port}.") from e
        except smtplib.SMTPException as e:
            logger.error("SMTP error during dispatch: %s", e)
            raise EmailDeliveryError("Failed to deliver email through SMTP server.") from e
        except OSError as e:
            logger.error("Network or connection error during email dispatch: %s", e)
            raise EmailDeliveryError(f"Network error connecting to SMTP host: {e}") from e
        except Exception as e:
            logger.exception("Unexpected error during email dispatch: %s", e)
            raise EmailDeliveryError("An unexpected error occurred while sending email.") from e


class EmailService:
    """Service to validate, format, and dispatch rationalisation recommendation emails."""

    def __init__(
        self,
        transport: EmailTransport | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        if transport is not None:
            self._transport = transport
        else:
            self._transport = SMTPEmailTransport(
                host=self._settings.smtp_host,
                port=self._settings.smtp_port,
                username=self._settings.smtp_username,
                password=self._settings.smtp_password,
                use_tls=self._settings.smtp_use_tls,
            )

    @property
    def transport(self) -> EmailTransport:
        return self._transport

    @transport.setter
    def transport(self, transport: EmailTransport) -> None:
        self._transport = transport

    def validate_recipient(self, email_address: str) -> str:
        """Validate recipient email format."""
        if not email_address or not isinstance(email_address, str):
            raise EmailValidationError("Recipient email address cannot be empty.")
        trimmed = email_address.strip()
        if not EMAIL_REGEX.match(trimmed):
            raise EmailValidationError(f"Invalid email address format: '{trimmed}'.")
        return trimmed

    def validate_content(self, subject: str, body: str) -> tuple[str, str]:
        """Validate subject and body."""
        if not subject or not isinstance(subject, str) or not subject.strip():
            raise EmailValidationError("Email subject cannot be empty.")
        if not body or not isinstance(body, str) or not body.strip():
            raise EmailValidationError("Email body cannot be empty.")
        return subject.strip(), body.strip()

    def generate_html_body(self, text_body: str) -> str:
        """Escape text and generate clean semantic HTML email body."""
        escaped_text = html.escape(text_body)
        formatted_html = escaped_text.replace("\n", "<br />\n")
        return (
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head><meta charset='utf-8'></head>\n"
            "<body style='font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Helvetica, Arial, sans-serif; "
            "font-size: 14px; line-height: 1.6; color: #1e293b; background-color: #f8fafc; padding: 20px;'>\n"
            "<div style='max-width: 680px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;'>\n"
            f"<div style='font-size: 13.5px; color: #334155; white-space: pre-wrap;'>{formatted_html}</div>\n"
            "</div>\n"
            "</body>\n"
            "</html>"
        )

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        from_email: str | None = None,
    ) -> dict[str, Any]:
        """Validate and send email via configured transport."""
        valid_to = self.validate_recipient(to_email)
        valid_subject, valid_body = self.validate_content(subject, body)
        from_addr = (from_email.strip() if from_email and from_email.strip() else None) or self._settings.email_from_address

        html_body = self.generate_html_body(valid_body)

        self._transport.send_email(
            from_addr=from_addr,
            to_addrs=[valid_to],
            subject=valid_subject,
            text_body=valid_body,
            html_body=html_body,
        )

        return {
            "status": "success",
            "message": "Email dispatched successfully.",
            "recipient": valid_to,
            "subject": valid_subject,
        }


# Global singleton instance
_default_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get the active EmailService instance."""
    global _default_email_service
    if _default_email_service is None:
        _default_email_service = EmailService()
    return _default_email_service


def set_default_email_service(service: EmailService | None) -> None:
    """Set or override the default EmailService instance (used for testing)."""
    global _default_email_service
    _default_email_service = service


def set_default_transport(transport: EmailTransport | None) -> None:
    """Set or override transport on default EmailService instance."""
    if transport is None:
        set_default_email_service(None)
    else:
        service = get_email_service()
        service.transport = transport
