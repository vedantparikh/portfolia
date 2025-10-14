import smtplib
from email.message import EmailMessage

from environs import Env

from config import settings
from core.logging_config import get_logger

env = Env()
logger = get_logger(__name__)


def _send_email(recipient_email: str, subject: str, html_content: str):
    """
    A single, reusable function to handle sending emails via Brevo using Port 587.
    """
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        # This 'From' address must be a verified sender in your Brevo account
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = recipient_email
        msg.add_alternative(html_content, subtype="html")

        # Use smtplib.SMTP for port 587 (STARTTLS)
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as smtp:
            # Upgrade the connection to a secure one
            smtp.starttls()
            # Log in using the now-secure connection
            smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            # Send the message
            smtp.send_message(msg)
            logger.info(f"Email with subject '{subject}' sent successfully to {recipient_email}")
            return True

    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        return False


def send_forgot_password_email(recipient_email: str, reset_url: str):
    """
    Prepares and sends a password reset email.
    """
    logger.info(f"Preparing forgot password email for {recipient_email}")
    try:
        html_template_path = settings.STATIC_FILE_PATH / "password_reset_email.html"
        if not html_template_path.exists():
            logger.error(f"HTML template not found: {html_template_path}")
            return

        html_content = html_template_path.read_text().replace("{{reset_link}}", reset_url)
        subject = "Password Reset Request"

        _send_email(recipient_email, subject, html_content)

    except Exception as e:
        logger.error(f"An error occurred in send_forgot_password_email: {e}")


def send_verification_email(recipient_email: str, verification_url: str):
    """
    Prepares and sends an email verification email.
    """
    logger.info(f"Preparing verification email for {recipient_email}")
    try:
        html_template_path = settings.STATIC_FILE_PATH / "email_verification.html"
        if not html_template_path.exists():
            logger.error(f"HTML template not found: {html_template_path}")
            return

        html_content = html_template_path.read_text().replace("{{verification_link}}", verification_url)
        subject = "Verify Your Email Address - Portfolia"

        _send_email(recipient_email, subject, html_content)

    except Exception as e:
        logger.error(f"An error occurred in send_verification_email: {e}")
