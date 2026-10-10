import logging
from config import config
from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

# 1. Define GoDaddy SMTP Configuration
conf = ConnectionConfig(
    MAIL_USERNAME=config.mail_username,
    MAIL_PASSWORD=config.mail_password,
    MAIL_FROM=config.mail_from or config.mail_username,
    MAIL_PORT=config.mail_port,
    MAIL_SERVER=config.mail_server,
    MAIL_STARTTLS=config.mail_starttls,
    MAIL_SSL_TLS=config.mail_ssl_tls,
    USE_CREDENTIALS=config.use_credentials,
    VALIDATE_CERTS=config.validate_certs,
    MAIL_FROM_NAME="Khoo AI",
)

# 2. Pydantic schema for email requests
class EmailSchema(BaseModel):
    email: list[EmailStr]
    subject: str
    body: str
    is_html: bool = False


async def send_email(email: EmailSchema) -> dict[str, str]:
    """Sends an email synchronously using FastMail."""
    message = MessageSchema(
        subject=email.subject,
        recipients=email.email,
        body=email.body,
        subtype=MessageType.html if email.is_html else MessageType.plain,
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
    except Exception as e:
        logger.warning("SMTP send failed with MAIL_FROM=%s: %s", conf.MAIL_FROM, e)
        # If rejected due to sender address mismatch, fallback to MAIL_USERNAME
        if conf.MAIL_FROM != config.mail_username and config.mail_username:
            logger.info("Retrying with MAIL_FROM=%s", config.mail_username)
            fallback_conf = ConnectionConfig(
                MAIL_USERNAME=config.mail_username,
                MAIL_PASSWORD=config.mail_password,
                MAIL_FROM=config.mail_username,
                MAIL_PORT=config.mail_port,
                MAIL_SERVER=config.mail_server,
                MAIL_STARTTLS=config.mail_starttls,
                MAIL_SSL_TLS=config.mail_ssl_tls,
                USE_CREDENTIALS=config.use_credentials,
                VALIDATE_CERTS=config.validate_certs,
                MAIL_FROM_NAME="Khoo AI",
            )
            fm_fallback = FastMail(fallback_conf)
            await fm_fallback.send_message(message)
        else:
            raise e

    return {"message": "Email has been sent successfully"}


async def send_email_background(email: EmailSchema, background_tasks: BackgroundTasks):
    """Schedules email sending as a FastAPI background task."""
    background_tasks.add_task(send_email, email)
    return {"message": "Email sending has been scheduled in the background"}


async def send_verification_email_to_user(
    to_email: str,
    token: str,
    user_name: str = "",
    background_tasks: BackgroundTasks | None = None,
) -> None:
    """Sends a formatted email verification message asynchronously in the background."""
    # Build verification link pointing to frontend
    verification_url = f"{config.client_endpoint}/verify-email?token={token}"
    display_name = user_name.strip() if user_name else "Learner"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Verify Your Khoo AI Email</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="padding: 40px 16px;">
            <tr>
                <td align="center">
                    <table width="100%" max-width="560px" cellpadding="0" cellspacing="0" style="max-width: 560px; background-color: #1e293b; border-radius: 16px; border: 1px solid #334155; overflow: hidden; padding: 36px 32px; color: #f8fafc;">
                        <tr>
                            <td>
                                <div style="display: flex; align-items: center; margin-bottom: 24px;">
                                    <h1 style="color: #6366f1; font-size: 24px; margin: 0; font-weight: 800; letter-spacing: -0.5px;">Khoo AI</h1>
                                </div>
                                <h2 style="color: #f1f5f9; font-size: 20px; margin-top: 0; margin-bottom: 12px; font-weight: 600;">
                                    Verify your email address
                                </h2>
                                <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
                                    Hi <strong style="color: #f8fafc;">{display_name}</strong>,<br>
                                    Welcome to Khoo AI! To access interactive voice practice and start your fluency journey, please confirm your email address.
                                </p>
                                <div style="text-align: center; margin: 32px 0;">
                                    <a href="{verification_url}" style="background-color: #6366f1; color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 10px; font-size: 15px; font-weight: 600; display: inline-block; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);">
                                        Verify Email Address
                                    </a>
                                </div>
                                <p style="color: #64748b; font-size: 13px; line-height: 1.5; margin-bottom: 8px;">
                                    Or copy and paste this link in your browser:
                                </p>
                                <p style="color: #818cf8; font-size: 12px; word-break: break-all; margin-top: 0; margin-bottom: 24px;">
                                    {verification_url}
                                </p>
                                <div style="border-top: 1px solid #334155; padding-top: 20px; margin-top: 24px;">
                                    <p style="color: #64748b; font-size: 12px; margin: 0;">
                                        This verification link will expire in 24 hours. If you did not create this account, you can safely disregard this message.
                                    </p>
                                </div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    email_schema = EmailSchema(
        email=[to_email],
        subject="Verify your Khoo AI email address",
        body=html_content,
        is_html=True,
    )

    if background_tasks is not None:
        background_tasks.add_task(send_email, email_schema)
        logger.info("Verification email delivery scheduled via FastAPI BackgroundTasks for %s", to_email)
    else:
        import asyncio
        asyncio.create_task(send_email(email_schema))
        logger.info("Verification email delivery scheduled via asyncio background task for %s", to_email)


async def send_verification_success_email(
    to_email: str,
    user_name: str = "",
    background_tasks: BackgroundTasks | None = None,
) -> None:
    """Sends a confirmation email after successful email verification."""
    practice_url = f"{config.client_endpoint}"
    display_name = user_name.strip() if user_name else "Learner"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Email Verified – Khoo AI</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="padding: 40px 16px;">
            <tr>
                <td align="center">
                    <table width="100%" max-width="560px" cellpadding="0" cellspacing="0" style="max-width: 560px; background-color: #1e293b; border-radius: 16px; border: 1px solid #334155; overflow: hidden; padding: 36px 32px; color: #f8fafc;">
                        <tr>
                            <td>
                                <div style="display: flex; align-items: center; margin-bottom: 24px;">
                                    <h1 style="color: #6366f1; font-size: 24px; margin: 0; font-weight: 800; letter-spacing: -0.5px;">Khoo AI</h1>
                                </div>
                                <div style="display: inline-block; padding: 6px 12px; background-color: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 9999px; color: #34d399; font-size: 13px; font-weight: 600; margin-bottom: 16px;">
                                    ✓ Email Verified
                                </div>
                                <h2 style="color: #f1f5f9; font-size: 20px; margin-top: 0; margin-bottom: 12px; font-weight: 600;">
                                    You're all set, {display_name}! 🎉
                                </h2>
                                <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin-bottom: 16px;">
                                    Your email address (<strong style="color: #f8fafc;">{to_email}</strong>) has been confirmed.
                                </p>
                                <p style="color: #94a3b8; font-size: 15px; line-height: 1.6; margin-bottom: 24px;">
                                    Your free practice credits are unlocked. Jump into interactive, real-time voice sessions and start practicing languages today.
                                </p>
                                <div style="text-align: center; margin: 32px 0;">
                                    <a href="{practice_url}" style="background-color: #6366f1; color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 10px; font-size: 15px; font-weight: 600; display: inline-block; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);">
                                        Start Practicing Now →
                                    </a>
                                </div>
                                <div style="border-top: 1px solid #334155; padding-top: 20px; margin-top: 24px;">
                                    <p style="color: #64748b; font-size: 12px; margin: 0;">
                                        Happy learning from the Khoo AI team! Need help? Just reply to this email.
                                    </p>
                                </div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    email_schema = EmailSchema(
        email=[to_email],
        subject="Email Verified – Welcome to Khoo AI! 🎉",
        body=html_content,
        is_html=True,
    )

    if background_tasks is not None:
        background_tasks.add_task(send_email, email_schema)
        logger.info("Verification success email scheduled via FastAPI BackgroundTasks for %s", to_email)
    else:
        import asyncio
        asyncio.create_task(send_email(email_schema))
        logger.info("Verification success email scheduled via asyncio background task for %s", to_email)