from email.message import EmailMessage

from pydantic import SecretStr
from pytest import MonkeyPatch

from app.config import settings
from app.email_delivery import send_tracking_email


def test_tracking_email_uses_secure_ukr_net_smtp(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeSmtp:
        def __init__(
            self,
            host: str,
            port: int,
            *,
            context: object,
            timeout: int,
        ) -> None:
            captured.update(
                host=host,
                port=port,
                context=context,
                timeout=timeout,
            )

        def __enter__(self) -> "FakeSmtp":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            captured["login"] = (username, password)

        def send_message(self, message: EmailMessage) -> None:
            captured["message"] = message

    monkeypatch.setattr(settings, "smtp_host", "smtp.ukr.net")
    monkeypatch.setattr(settings, "smtp_port", 465)
    monkeypatch.setattr(settings, "smtp_username", "example@ukr.net")
    monkeypatch.setattr(settings, "smtp_password", SecretStr("app-password"))
    monkeypatch.setattr(settings, "smtp_from_email", "example@ukr.net")
    monkeypatch.setattr("app.email_delivery.smtplib.SMTP_SSL", FakeSmtp)

    send_tracking_email(
        recipient="customer@example.com",
        ticket_id=991,
        tracking_code="private-tracking-code",
        subject="Door problem",
        manufacturer_name="KhersonSafe Ltd.",
        organization_logo_url="https://example.com/organization-logo.png",
    )

    message = captured["message"]
    assert captured["host"] == "smtp.ukr.net"
    assert captured["port"] == 465
    assert captured["timeout"] == 10
    assert captured["login"] == ("example@ukr.net", "app-password")
    assert message["To"] == "customer@example.com"
    assert message.is_multipart()
    plain_part, html_part = message.get_payload()
    assert plain_part.get_content_type() == "text/plain"
    assert html_part.get_content_type() == "text/html"
    assert "private-tracking-code" in plain_part.get_content()
    assert "/support-ticket/991" in plain_part.get_content()
    assert "Support ticket submitted" in html_part.get_content()
    assert "Track ticket" in html_part.get_content()
    assert "private-tracking-code" in html_part.get_content()
    assert "https://example.com/organization-logo.png" in html_part.get_content()
