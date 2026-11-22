"""Send a setup code through SMTP.

The message body contains the code. The subject does not. Failures are logged
as an exception type only, never as a password, code, or server reply.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from settings import get_smtp_settings

LOGGER = logging.getLogger("email_delivery")
TIMEOUT_SECONDS = 10


class EmailDeliveryError(Exception):
    """Mail could not be sent. The message is a fixed label, not a server error."""


def deliver_setup_code(recipient: str, otp: str) -> None:
    """Send the six-digit code. Raises EmailDeliveryError when delivery fails."""
    settings = get_smtp_settings()
    if not settings["host"] or not settings["from_email"]:
        raise EmailDeliveryError("not-configured")
    message = EmailMessage()
    message["Subject"] = "Your AI Job Matching Agent verification"
    message["From"] = settings["from_email"]
    message["To"] = recipient
    message.set_content(
        "\n".join(
            [
                "AI Job Matching Agent",
                "",
                f"Your verification code is {otp}.",
                "It expires in 10 minutes.",
                "Do not share this code.",
                "If you did not request a password for this profile, you can ignore this email.",
            ]
        )
    )
    message.add_alternative(
        (
            "<p><strong>AI Job Matching Agent</strong></p>"
            f"<p>Your verification code is <strong>{otp}</strong>.</p>"
            "<p>It expires in 10 minutes. Do not share this code.</p>"
            "<p>If you did not request a password for this profile, you can ignore this email.</p>"
        ),
        subtype="html",
    )
    try:
        _send(settings, message)
    except EmailDeliveryError:
        raise
    except Exception as exc:
        LOGGER.warning("SMTP delivery failed: %s", type(exc).__name__)
        raise EmailDeliveryError("delivery-failed") from None


def _send(settings: dict, message: EmailMessage) -> None:
    host = settings["host"]
    port = settings["port"]
    if settings["use_ssl"]:
        with smtplib.SMTP_SSL(host, port, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context()) as smtp:
            _login_and_send(smtp, settings, message)
        return
    with smtplib.SMTP(host, port, timeout=TIMEOUT_SECONDS) as smtp:
        smtp.ehlo()
        if settings["use_tls"]:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        _login_and_send(smtp, settings, message)


def _login_and_send(smtp, settings: dict, message: EmailMessage) -> None:
    if settings["username"]:
        smtp.login(settings["username"], settings["password"])
    smtp.send_message(message)
