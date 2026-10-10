from config import config
from fastapi import FastAPI, BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import BaseModel, EmailStr

app = FastAPI()

# 1. Define GoDaddy SMTP Configuration
conf = ConnectionConfig(
    MAIL_USERNAME= config.mail_username,  # Replace with your full GoDaddy email
    MAIL_PASSWORD= config.mail_password,   # Replace with your mailbox password
    MAIL_FROM= config.mail_from,      # Must match your username
    MAIL_PORT= config.mail_port,                            # Secure Port
    MAIL_SERVER= config.mail_server,
    MAIL_STARTTLS= config.mail_starttls,                      # False because we are using SSL directly on 465
    MAIL_SSL_TLS= config.mail_ssl_tls,                        # True for Port 465 SSL encryption
    USE_CREDENTIALS= config.use_credentials,
    VALIDATE_CERTS= config.validate_certs
)

# 2. Pydantic schema for incoming requests
class EmailSchema(BaseModel):
    email: list[EmailStr]
    subject: str
    body: str

async def send_email(email: EmailSchema):
    message = MessageSchema(
        subject=email.subject,
        recipients=email.email,
        body=email.body,
        subtype=MessageType.plain # Switch to MessageType.html if sending HTML emails
    )

    fm = FastMail(conf)
    await fm.send_message(message)
    return {"message": "Email has been sent successfully"}

async def send_email_background(email: EmailSchema, background_tasks: BackgroundTasks):
    message = MessageSchema(
        subject=email.subject,
        recipients=email.email,
        body=email.body,
        subtype=MessageType.plain
    )

    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)
    return {"message": "Email sending has been scheduled in the background"}