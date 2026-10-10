from app.types.content import StreakResponse
from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.auth_dependencies import get_current_user
from app.dependencies.profile_dependencies import get_profile_service
from app.models.user import User
from app.services.profile_service import ProfileService
from app.types.profile import UserProfileResponse

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get(
    "/stats",
    response_model=UserProfileResponse,
    summary="Get user language proficiency profile",
)
async def get_my_profile_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: ProfileService = Depends(get_profile_service),
) -> UserProfileResponse:
    """Retrieve the authenticated user's profile and language proficiencies."""
    return await profile_service.get_user_profile(current_user)


@router.get(
    "/streak",
    response_model=StreakResponse,
    summary="Get user streak stats",
)
async def get_user_streak_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: ProfileService = Depends(get_profile_service),
) -> StreakResponse:
    """Retrieve the authenticated user's streak stats."""
    return await profile_service.get_user_streak_stats(current_user)