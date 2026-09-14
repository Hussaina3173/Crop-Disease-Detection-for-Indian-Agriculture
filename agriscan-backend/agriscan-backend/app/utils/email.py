import smtplib
from email.message import EmailMessage

from app.config import settings


def send_password_reset_email(to_email: str, raw_token: str):
    """
    Sends the password reset link. If SMTP isn't configured (local dev),
    it just prints the link to the console so you can test the flow
    without setting up a mail server.
    """
    reset_link = f"{settings.frontend_origin}/reset-password?token={raw_token}"

    if not settings.smtp_host:
        print(f"[DEV] Password reset link for {to_email}: {reset_link}")
        return

    msg = EmailMessage()
    msg["Subject"] = "Reset your AgriScan password"
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg.set_content(
        f"We received a request to reset your AgriScan password.\n\n"
        f"Reset it here: {reset_link}\n\n"
        f"This link expires in {settings.reset_token_expire_minutes} minutes. "
        f"If you didn't request this, you can ignore this email."
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
