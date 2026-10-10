from app.repositories.session_repository import SessionRepository
from app.types.content import StreakResponse
import logging
from datetime import datetime, timezone
from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.types.profile import UserProfileResponse

logger = logging.getLogger(__name__)


class ProfileService:
    def __init__(self, profile_repository: ProfileRepository , session_repository: SessionRepository):
        self.profile_repository = profile_repository
        self.session_repository = session_repository

    async def get_user_profile(self, user: User) -> UserProfileResponse:
        """Retrieve user language proficiency profile."""
        return await self.profile_repository.get_user_profile(user)

    async def get_user_streak_stats(self, user: User) -> StreakResponse:
        """Retrieve user streak stats."""
        dates = await self.session_repository.get_completed_sessions(user.id)
        if not dates:
            return StreakResponse(
                current_streak=0,
                longest_streak=0,
                today_completed=False,
                active_dates=[],
                freeze_dates=[],
                available_freezes=2,
                total_active_days=0,
            ) 

        
        date_strs = sorted(list({d.strftime("%Y-%m-%d") for d in dates if d}))
        date_objs = sorted(list({datetime.strptime(s, "%Y-%m-%d").date() for s in date_strs}))

        today = datetime.now(timezone.utc).date()
        today_str = today.strftime("%Y-%m-%d")
        today_completed = today_str in date_strs

        # Longest streak calculation
        longest = 0
        current_run = 0
        prev_date = None
        for d in date_objs:
            if prev_date is None:
                current_run = 1
            elif (d - prev_date).days == 1:
                current_run += 1
            elif (d - prev_date).days > 1:
                current_run = 1
            prev_date = d
            if current_run > longest:
                longest = current_run

        # Current streak calculation
        current_streak = 0
        if date_objs:
            latest = date_objs[-1]
            days_diff = (today - latest).days
            if days_diff <= 1:
                current_streak = 1
                idx = len(date_objs) - 1
                while idx > 0 and (date_objs[idx] - date_objs[idx - 1]).days == 1:
                    current_streak += 1
                    idx -= 1
            else:
                current_streak = 0

        return StreakResponse(
            current_streak=current_streak,
            longest_streak=max(longest, current_streak),
            today_completed=today_completed,
            active_dates=date_strs,
            freeze_dates=[],
            available_freezes=2,
            total_active_days=len(date_strs),
        )