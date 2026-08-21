import smtplib
import ssl
from email.message import EmailMessage
from html import escape

from app.config import settings


class EmailNotConfiguredError(RuntimeError):
    """Required SMTP credentials are missing."""


class EmailDeliveryError(RuntimeError):
    """The SMTP server could not deliver an application email."""


def tracking_email_is_configured() -> bool:
    """Tell the public passport whether ticket email delivery is available."""

    return all(
        (
            settings.smtp_host,
            settings.smtp_username,
            settings.smtp_password,
            settings.smtp_from_email,
        ),
    )


def _send_email(message: EmailMessage) -> None:
    """Deliver an application email with the existing SMTP configuration."""

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            context=context,
            timeout=10,
        ) as smtp:
            smtp.login(
                settings.smtp_username,
                settings.smtp_password.get_secret_value(),
            )
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError from error


def send_email_confirmation_email(
    *,
    recipient: str,
    confirmation_token: str,
) -> None:
    """Send the signup confirmation link using the existing SMTP settings."""

    if not tracking_email_is_configured():
        raise EmailNotConfiguredError

    confirmation_url = (
        f"{settings.frontend_origin}/confirm-email?token={confirmation_token}"
    )
    message = EmailMessage()
    message["Subject"] = "Confirm your Digital Product Passport account"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "Thank you for registering a Digital Product Passport account.\n\n"
        f"Confirm your email address: {confirmation_url}\n\n"
        "This link expires in 24 hours and can be used once. You cannot sign "
        "in until the address is confirmed. If you did not create this "
        "account, you can ignore this email."
    )

    _send_email(message)


def send_team_member_invitation_email(
    *,
    recipient: str,
    invitation_token: str,
    organization_name: str,
) -> None:
    """Invite a technician to choose their own password, never sending one."""

    if not tracking_email_is_configured():
        raise EmailNotConfiguredError

    invitation_url = (
        f"{settings.frontend_origin}/accept-invitation?token={invitation_token}"
    )
    message = EmailMessage()
    message["Subject"] = "You have been added to a Digital Product Passport team"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        f"{organization_name} created a service-technician account for you in "
        "the Digital Product Passport platform.\n\n"
        f"Choose your password: {invitation_url}\n\n"
        "This link expires in 7 days and can be used once. If you were not "
        "expecting this invitation, you can ignore this email."
    )

    _send_email(message)


def send_password_reset_email(*, recipient: str, reset_token: str) -> None:
    """Send a short password reset link without logging or storing the token."""

    if not tracking_email_is_configured():
        raise EmailNotConfiguredError

    reset_url = f"{settings.frontend_origin}/reset-password?token={reset_token}"
    message = EmailMessage()
    message["Subject"] = "Reset your Digital Product Passport password"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "A password reset was requested for your Digital Product Passport "
        "account.\n\n"
        f"Reset your password: {reset_url}\n\n"
        "This link expires in 30 minutes and can be used once. If you did not "
        "request this change, you can ignore this email."
    )

    _send_email(message)


def send_tracking_email(
    *,
    recipient: str,
    ticket_id: int,
    tracking_code: str,
    subject: str,
    manufacturer_name: str,
    organization_logo_url: str | None,
) -> None:
    """Send one plain-text ticket tracking email over implicit TLS."""

    if not tracking_email_is_configured():
        raise EmailNotConfiguredError

    message = EmailMessage()
    message["Subject"] = f"Support ticket #{ticket_id} tracking details"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    tracking_url = f"{settings.frontend_origin}/support-ticket/{ticket_id}"
    message.set_content(
        f"Your support request to {manufacturer_name} was submitted.\n\n"
        f"Ticket: #{ticket_id}\n"
        f"Subject: {subject}\n"
        f"Tracking code: {tracking_code}\n\n"
        f"Track the ticket here: {tracking_url}\n\n"
        "Keep this tracking code private."
    )
    safe_manufacturer = escape(manufacturer_name)
    safe_subject = escape(subject)
    safe_tracking_code = escape(tracking_code)
    safe_tracking_url = escape(tracking_url, quote=True)
    safe_logo_url = (
        escape(organization_logo_url, quote=True)
        if organization_logo_url
        else None
    )
    logo_html = (
        f'<img src="{safe_logo_url}" alt="{safe_manufacturer} logo" '
        'width="52" style="display:block;width:52px;height:52px;'
        'object-fit:contain;background:#ffffff;border-radius:8px;">'
        if safe_logo_url
        else (
            '<div style="width:52px;height:52px;line-height:52px;text-align:center;'
            'background:#ffffff;color:#0f4c5c;border-radius:50%;font-size:13px;'
            'font-weight:700;">DPP</div>'
        )
    )
    message.add_alternative(
        f"""
<!doctype html>
<html lang="en">
  <body style="margin:0;padding:0;background:#f5f7f8;color:#17232a;"
        bgcolor="#f5f7f8">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
           border="0" style="width:100%;background:#f5f7f8;">
      <tr>
        <td align="center" style="padding:32px 16px;">
          <table role="presentation" width="100%" cellspacing="0"
                 cellpadding="0" border="0"
                 style="width:100%;max-width:600px;background:#ffffff;
                        border:1px solid #cbd5db;border-radius:12px;">
            <tr>
              <td style="padding:24px 32px;background:#0f4c5c;color:#ffffff;
                         border-radius:12px 12px 0 0;font-family:Arial,sans-serif;">
                <table role="presentation" cellspacing="0" cellpadding="0"
                       border="0">
                  <tr>
                    <td style="padding-right:16px;vertical-align:middle;">
                      {logo_html}
                    </td>
                    <td style="vertical-align:middle;color:#ffffff;">
                      <div style="font-size:13px;font-weight:700;
                                  letter-spacing:.08em;">
                        DIGITAL PRODUCT PASSPORT
                      </div>
                      <div style="margin-top:6px;font-size:24px;font-weight:700;">
                        Support ticket submitted
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;font-family:Arial,sans-serif;
                         font-size:16px;line-height:1.5;">
                <p style="margin:0 0 20px;">
                  Your support request to <strong>{safe_manufacturer}</strong>
                  was submitted successfully.
                </p>
                <table role="presentation" width="100%" cellspacing="0"
                       cellpadding="0" border="0"
                       style="width:100%;background:#f5f7f8;
                              border-radius:8px;">
                  <tr>
                    <td style="padding:20px;font-family:Arial,sans-serif;">
                      <div style="color:#52616b;font-size:13px;font-weight:700;">
                        TICKET
                      </div>
                      <div style="margin-top:4px;font-size:22px;font-weight:700;">
                        #{ticket_id}
                      </div>
                      <div style="margin-top:12px;color:#52616b;font-size:13px;
                                  font-weight:700;">
                        SUBJECT
                      </div>
                      <div style="margin-top:4px;">{safe_subject}</div>
                    </td>
                  </tr>
                </table>
                <p style="margin:24px 0 8px;color:#52616b;font-size:14px;">
                  Use this private tracking code to view the ticket status:
                </p>
                <div style="padding:14px 16px;background:#dbeafe;color:#17232a;
                            border:1px solid #93c5fd;border-radius:8px;
                            font-family:Courier New,monospace;font-size:20px;
                            font-weight:700;letter-spacing:.04em;text-align:center;">
                  {safe_tracking_code}
                </div>
                <table role="presentation" cellspacing="0" cellpadding="0"
                       border="0" style="margin-top:24px;">
                  <tr>
                    <td bgcolor="#0f4c5c" style="border-radius:8px;">
                      <a href="{safe_tracking_url}"
                         style="display:inline-block;padding:13px 22px;
                                color:#ffffff;font-family:Arial,sans-serif;
                                font-weight:700;text-decoration:none;">
                        Track ticket
                      </a>
                    </td>
                  </tr>
                </table>
                <p style="margin:24px 0 0;color:#52616b;font-size:13px;">
                  Keep this code private. Anyone with the ticket number and code
                  can view its customer-facing status.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""",
        subtype="html",
    )

    _send_email(message)
