from app.repositories.profile_repository import ProfileRepository
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.profile_service import ProfileService


def get_profile_repository(
    db: AsyncSession = Depends(get_db),
) -> ProfileRepository:
    return ProfileRepository(db=db)


def get_profile_service(
    profile_repository: ProfileRepository = Depends(get_profile_repository),
) -> ProfileService:
    return ProfileService(profile_repository=profile_repository)
