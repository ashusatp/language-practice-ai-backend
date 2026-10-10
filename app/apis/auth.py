from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from config import config
from app.dependencies.auth_dependencies import get_auth_service, get_current_user
from app.exceptions.custom import AppException

from app.models.user import User
from app.services.auth_service import AuthService
from app.types.auth import (
    LoginRequest,
    SendVerificationResponse,
    SignupRequest,
    TokenResponse,
    VerificationStatusResponse,
    VerifyEmailRequest,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    request: SignupRequest,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Register a new user account and return an access token, sending verification email in background."""
    try:
        return await auth_service.register(
            email=request.email,
            name=request.name,
            password=request.password,
            background_tasks=background_tasks,
        )
    except AppException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in user",
)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate user credentials and return an access token."""
    try:
        return await auth_service.login(
            email=request.email,
            password=request.password,
        )
    except AppException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )


@router.post(
    "/send-verification",
    response_model=SendVerificationResponse,
    summary="Send or resend email verification token",
)
async def send_verification(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> SendVerificationResponse:
    """Generates and schedules an email verification link to the current authenticated user in the background."""
    return await auth_service.send_verification_email(current_user, background_tasks=background_tasks)


@router.get(
    "/verify-email",
    summary="Verify user email address via direct link click (GET)",
)
async def verify_email_get(
    background_tasks: BackgroundTasks,
    token: str = Query(..., description="Verification token from email link"),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Handles direct browser clicks from email. Validates token, activates user, and redirects to frontend."""
    try:
        user = await auth_service.verify_email(token, background_tasks=background_tasks)
        return RedirectResponse(
            url=f"{config.client_endpoint}/?email_verified=true&email={user.email}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    except AppException as e:
        return RedirectResponse(
            url=f"{config.client_endpoint}/?email_verified=false&error={e.message}",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )


@router.post(
    "/verify-email",
    response_model=VerificationStatusResponse,
    summary="Verify user email address using token (POST JSON)",
)
async def verify_email(
    request: VerifyEmailRequest,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service),
) -> VerificationStatusResponse:
    """Verifies user's email using the token provided in the verification link."""
    user = await auth_service.verify_email(request.token, background_tasks=background_tasks)
    return VerificationStatusResponse(
        is_email_verified=True,
        email=user.email,
    )




@router.get(
    "/verification-status",
    response_model=VerificationStatusResponse,
    summary="Get current user email verification status",
)
async def get_verification_status(
    current_user: User = Depends(get_current_user),
) -> VerificationStatusResponse:
    """Returns whether the logged-in user's email has been verified."""
    return VerificationStatusResponse(
        is_email_verified=current_user.is_email_verified,
        email=current_user.email,
    )
    