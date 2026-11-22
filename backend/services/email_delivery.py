"""Send a verification code through the selected mail provider.

Google Apps Script is the production transport. SMTP remains available when
EMAIL_PROVIDER is smtp or unset. Failures are logged as a category only.
"""

import json
import logging
import smtplib
import ssl
from email.message import EmailMessage

import requests

from settings import get_email_provider, get_google_apps_script_settings, get_smtp_settings

LOGGER = logging.getLogger("email_delivery")
TIMEOUT_SECONDS = 10
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 20


class EmailDeliveryError(Exception):
    """Mail could not be sent. The message is a fixed label, not a server error."""


def deliver_setup_code(recipient: str, otp: str) -> None:
    """Send the account-setup code. Raises EmailDeliveryError when delivery fails."""
    _deliver(
        recipient,
        otp,
        "Your AI Job Matching Agent verification",
        "If you did not request a password for this profile, you can ignore this email.",
    )


def deliver_reset_code(recipient: str, otp: str) -> None:
    """Send the password-reset code. The subject does not contain the code."""
    _deliver(
        recipient,
        otp,
        "Reset your AI Job Matching Agent password",
        "If you did not request a password reset, you can ignore this email.",
    )


def _deliver(recipient: str, otp: str, subject: str, ignore_line: str) -> None:
    if get_email_provider() == "google_apps_script":
        _deliver_apps_script(recipient, otp)
        return
    if get_email_provider() != "smtp":
        raise EmailDeliveryError("not-configured")
    settings = get_smtp_settings()
    if not settings["host"] or not settings["from_email"]:
        raise EmailDeliveryError("not-configured")
    message = EmailMessage()
    message["Subject"] = subject
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
                ignore_line,
            ]
        )
    )
    message.add_alternative(
        (
            "<p><strong>AI Job Matching Agent</strong></p>"
            f"<p>Your verification code is <strong>{otp}</strong>.</p>"
            "<p>It expires in 10 minutes. Do not share this code.</p>"
            f"<p>{ignore_line}</p>"
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


def _deliver_apps_script(recipient: str, otp: str) -> None:
    """POST the code to the configured web app. SMTP is not tried after a failure."""
    settings = get_google_apps_script_settings()
    if not settings["url"] or not settings["secret"]:
        raise EmailDeliveryError("not-configured")
    payload = {"secret": settings["secret"], "to": recipient, "otp": otp}
    try:
        response = _post_apps_script(settings["url"], payload)
    except EmailDeliveryError:
        raise
    except requests.Timeout:
        _fail("timeout")
    except requests.TooManyRedirects:
        _fail("redirect")
    except requests.RequestException:
        _fail("network")
    _accept_apps_script_response(response)


def _post_apps_script(url: str, payload: dict) -> requests.Response:
    """POST JSON and follow the ContentService redirect to the final response."""
    with requests.Session() as session:
        return session.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
            allow_redirects=True,
        )


def _accept_apps_script_response(response: requests.Response) -> None:
    urls = [response.url, *[getattr(item, "url", "") for item in response.history]]
    if any(not str(url).lower().startswith("https://") for url in urls):
        _fail("redirect")
    if response.status_code in {401, 403}:
        _fail("unauthorized")
    if response.status_code == 429:
        _fail("quota")
    if response.status_code >= 400:
        _fail("http-error")
    try:
        body = response.json()
    except ValueError:
        _fail("invalid-json")
    if isinstance(body, dict) and body.get("ok") is True:
        return
    _fail(_rejection_category(body))


def _rejection_category(body) -> str:
    """Map a rejected JSON body to a fixed category. The body itself is not logged."""
    if not isinstance(body, dict):
        return "rejected"
    text = " ".join(str(body.get(key) or "") for key in ("error", "message", "reason")).lower()
    if any(word in text for word in ("quota", "too many times", "daily limit")):
        return "quota"
    if any(word in text for word in ("unauthor", "forbidden", "secret", "permission")):
        return "unauthorized"
    return "rejected"


def _fail(category: str) -> None:
    LOGGER.warning("Apps Script delivery failed: %s", category)
    raise EmailDeliveryError("delivery-failed")
