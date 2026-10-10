from datetime import date
from typing import Optional
import uuid

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, UserLanguageProficiency, UserStreakFreeze
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

    # Alias so both method names work seamlessly
    get_user_profile_stats = get_user_profile

    async def get_user_streak_freezes(self, user_id: uuid.UUID) -> list[date]:
        """Fetch all dates on which a streak freeze was applied for the user."""
        stmt = (
            select(UserStreakFreeze.freeze_date)
            .where(UserStreakFreeze.user_id == user_id)
            .order_by(UserStreakFreeze.freeze_date.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_monthly_used_freezes(
        self, user_id: uuid.UUID, year: int, month: int
    ) -> int:
        """Count how many streak freezes the user has used in a given month and year."""
        stmt = select(func.count(UserStreakFreeze.id)).where(
            UserStreakFreeze.user_id == user_id,
            extract("year", UserStreakFreeze.freeze_date) == year,
            extract("month", UserStreakFreeze.freeze_date) == month,
        )
        res = await self.db.execute(stmt)
        return res.scalar() or 0

    async def apply_streak_freeze(self, user_id: uuid.UUID, freeze_date: date) -> bool:
        """Record an applied streak freeze for a specific date."""
        freeze = UserStreakFreeze(user_id=user_id, freeze_date=freeze_date)
        self.db.add(freeze)
        try:
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False