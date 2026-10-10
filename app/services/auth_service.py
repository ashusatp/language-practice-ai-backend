from datetime import datetime, timedelta, timezone
import logging
import secrets
from typing import Optional
from fastapi import BackgroundTasks


from app.exceptions.custom import (
    AppException,
    InvalidCredentialsException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from app.models.subscription import UserSubscription
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.types.auth import SendVerificationResponse, TokenResponse
from app.types.user import UserResponse
from app.utils.jwt import create_access_token
from app.utils.password import hash_password, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def register(
        self,
        email: str,
        name: str,
        password: str,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> TokenResponse:
        user = await self.user_repository.get_user_by_email(email)
        if user:
            logger.error(f"auth_service: User with email '{email}' already taken")
            raise UserAlreadyExistsException(f"User with email '{email}' already taken")
        
        password_hash = hash_password(password)
        verification_token = secrets.token_urlsafe(32)
        token_expires_at = datetime.now(timezone.utc) + timedelta(days=1)

        try:
            user = User(
                email=email,
                name=name,
                password_hash=password_hash,
                is_email_verified=False,
                verification_token=verification_token,
                verification_token_expires_at=token_expires_at,
            )
            created_user = await self.user_repository.create_user(user)

            # Create default Free tier subscription for the new user
            sub = UserSubscription(
                user_id=created_user.id,
                tier="free",
                status="active",
                free_lifetime_minutes_used=0,
            )
            self.user_repository.db.add(sub)
            await self.user_repository.db.commit()

            logger.info(
                "New user %s registered. Verification token: %s",
                created_user.email,
                verification_token,
            )

            # Dispatch initial verification email in background
            try:
                from app.utils.smtp import send_verification_email_to_user
                await send_verification_email_to_user(
                    to_email=created_user.email,
                    token=verification_token,
                    user_name=created_user.name or "",
                    background_tasks=background_tasks,
                )
            except Exception as mail_err:
                logger.warning("Could not dispatch verification email to %s: %s", created_user.email, mail_err)

            user_response = UserResponse.model_validate(created_user)
            access_token = create_access_token(data={"user_id": str(created_user.id)})

            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_response,
            )
        except Exception as e:
            logger.error(f"auth_service: Failed to create user: {str(e)}", exc_info=True)
            raise AppException("Unable to complete registration. Please try again later.", status_code=500)

    async def send_verification_email(
        self,
        user: User,
        background_tasks: Optional[BackgroundTasks] = None,
    ) -> SendVerificationResponse:
        """Generates a fresh email verification token and logs/sends the verification link in background."""
        if user.is_email_verified:
            return SendVerificationResponse(
                message="Email is already verified.",
                sent_to=user.email,
            )

        token = secrets.token_urlsafe(32)
        user.verification_token = token
        user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        await self.user_repository.update_user(user)

        logger.info("Email verification link generated for %s: token=%s", user.email, token)

        from app.utils.smtp import send_verification_email_to_user
        try:
            await send_verification_email_to_user(
                to_email=user.email,
                token=token,
                user_name=user.name or "",
                background_tasks=background_tasks,
            )
            logger.info("Verification email delivery scheduled in background for %s", user.email)
        except Exception as e:
            logger.error("Failed to schedule verification email for %s: %s", user.email, e, exc_info=True)
            raise AppException(f"Failed to send verification email: {str(e)}", status_code=500)


        return SendVerificationResponse(
            message="Verification link has been sent to your email address.",
            sent_to=user.email,
            preview_token=token,
        )


    async def verify_email(self, token: str) -> User:
        """Validates the verification token and activates user's verified status."""
        user = await self.user_repository.get_user_by_verification_token(token)
        if not user:
            raise AppException("Invalid or expired verification token.", status_code=400)

        if user.verification_token_expires_at:
            if datetime.now(timezone.utc) > user.verification_token_expires_at:
                raise AppException("Verification token has expired. Please request a new one.", status_code=400)

        user.is_email_verified = True
        user.verification_token = None
        user.verification_token_expires_at = None
        await self.user_repository.update_user(user)

        logger.info("User %s successfully verified email.", user.email)
        return user

    
    async def login(self, email: str, password: str) -> TokenResponse:
        try: 
            user = await self.user_repository.get_user_by_email(email)
            if not user:
                logger.error(f"auth_service: User with email '{email}' not found")
                raise UserNotFoundException(f"User with email '{email}' not found")
            
            if not verify_password(password, user.password_hash):
                logger.error(f"auth_service: Invalid password for email '{email}'")
                raise InvalidCredentialsException(f"Invalid password for email '{email}'")
            
            user_response = UserResponse.model_validate(user)
            access_token = create_access_token(data={"user_id": str(user.id)})

            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_response,
            )
        except Exception as e:
            logger.error(f"auth_service: Failed to login: {str(e)}", exc_info=True)
            raise AppException("Unable to complete login. Please try again later.", status_code=500)
        
    