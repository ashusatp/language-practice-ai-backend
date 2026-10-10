import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, UserLanguageProficiency
from app.types.profile import LanguageProficiencyResponse, UserProfileResponse


class ProfileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_proficiencies(
        self, user_id: uuid.UUID
    ) -> list[UserLanguageProficiency]:
        """Fetch all language proficiencies for a user with the Language relation eagerly loaded."""
        stmt = (
            select(UserLanguageProficiency)
            .where(UserLanguageProficiency.user_id == user_id)
            .options(selectinload(UserLanguageProficiency.language))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_profile(self, user: User) -> UserProfileResponse:
        """Fetch user proficiencies and construct UserProfileResponse."""
        proficiencies = await self.get_user_proficiencies(user.id)

        language_items = [
            LanguageProficiencyResponse(
                language_id=p.language_id,
                language_code=p.language.code if p.language else "",
                language_name=p.language.name if p.language else "",
                overall_rating=p.overall_rating,
                fluency_rating=p.fluency_rating,
                grammar_rating=p.grammar_rating,
                pronunciation_rating=p.pronunciation_rating,
                vocabulary_rating=p.vocabulary_rating,
                total_sessions=p.total_sessions,
                total_minutes=p.total_minutes,
            )
            for p in proficiencies
        ]

        total_sessions = sum(p.total_sessions for p in proficiencies)
        total_minutes = sum(p.total_minutes for p in proficiencies)

        return UserProfileResponse(
            user_id=user.id,
            name=user.name,
            email=user.email,
            avatar_url=user.avatar_url,
            total_sessions=total_sessions,
            total_minutes=total_minutes,
            languages=language_items,
        )