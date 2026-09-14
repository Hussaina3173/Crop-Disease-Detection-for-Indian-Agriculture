import os
import smtplib
from email.message import EmailMessage


def send_email(destination, token):
    host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    username = os.environ.get('GMAIL_USERNAME') or os.environ.get('SMTP_USERNAME')
    password = os.environ.get('GMAIL_APP_PASSWORD') or os.environ.get('SMTP_PASSWORD')
    if password:
        password = ''.join(password.split())
    sender = os.environ.get('SMTP_FROM', username)
    if not all((host, username, password, sender)):
        return False, 'Free Gmail delivery needs GMAIL_USERNAME and a Google App Password in .env.'
    message = EmailMessage()
    message['Subject'] = 'AgriScanner password reset'
    message['From'] = sender
    message['To'] = destination
    message.set_content(f'Your AgriScanner password reset code is: {token}\nThis 6-digit code expires in 15 minutes. If you did not request it, ignore this email.')
    try:
        with smtplib.SMTP_SSL(host, int(os.environ.get('SMTP_PORT', '465')), timeout=20) as server:
            server.login(username, password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        return False, 'Gmail could not send the message. Check the Gmail address and App Password in .env.'
    return True, 'Password reset instructions were sent to your email.'


def send_sms(destination, token):
    sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_FROM_NUMBER')
    if not all((sid, auth_token, from_number)):
        return False, 'SMS delivery is not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER.'
    try:
        from twilio.rest import Client
        Client(sid, auth_token).messages.create(body=f'AgriScanner password reset code: {token}', from_=from_number, to=destination)
    except ImportError as error:
        raise RuntimeError('Install the Twilio package with: pip install twilio') from error
    return True, 'Password reset instructions were sent by SMS.'
