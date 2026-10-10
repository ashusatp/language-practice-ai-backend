from fastapi import HTTPException
from app.exceptions.custom import AppException
from fastapi import APIRouter, Depends, status

from app.dependencies.auth_dependencies import get_auth_service
from app.services.auth_service import AuthService
from app.types.auth import LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    request: SignupRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Register a new user account and return an access token."""
    try:
        return await auth_service.register(
            email=request.email,
            name=request.name,
            password=request.password,
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