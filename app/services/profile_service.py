import logging

from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.types.profile import UserProfileResponse

logger = logging.getLogger(__name__)


class ProfileService:
    def __init__(self, profile_repository: ProfileRepository):
        self.profile_repository = profile_repository

    async def get_user_profile(self, user: User) -> UserProfileResponse:
        """Retrieve user language proficiency profile."""
        return await self.profile_repository.get_user_profile(user)