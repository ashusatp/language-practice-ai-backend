from datetime import date, datetime, timedelta, timezone
import logging
from typing import Set

from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.repositories.session_repository import SessionRepository
from app.types.content import StreakResponse
from app.types.profile import UserProfileResponse

logger = logging.getLogger(__name__)

MONTHLY_FREEZE_LIMIT = 2


class ProfileService:
    def __init__(
        self,
        profile_repository: ProfileRepository,
        session_repository: SessionRepository,
    ):
        self.profile_repository = profile_repository
        self.session_repository = session_repository

    async def get_user_profile(self, user: User) -> UserProfileResponse:
        """Retrieve user language proficiency profile."""
        return await self.profile_repository.get_user_profile(user)

    async def get_user_streak_stats(self, user: User) -> StreakResponse:
        """Calculate and return practice streak stats with monthly streak freeze protection."""
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)

        # 1. Fetch all completed session start timestamps
        session_timestamps = await self.session_repository.get_completed_sessions(user.id)
        active_dates: Set[date] = {
            ts.date() if isinstance(ts, datetime) else ts
            for ts in session_timestamps
            if ts
        }

        # 2. Fetch all applied streak freeze dates from database
        freeze_dates_list = await self.profile_repository.get_user_streak_freezes(user.id)
        freeze_dates: Set[date] = set(freeze_dates_list)

        # 3. Calculate remaining streak freezes for the current calendar month (renewed monthly)
        used_this_month = await self.profile_repository.get_monthly_used_freezes(
            user_id=user.id,
            year=today.year,
            month=today.month,
        )
        available_freezes = max(0, MONTHLY_FREEZE_LIMIT - used_this_month)

        # 4. Auto-shield logic: If user missed yesterday, had an active streak before,
        # and has available monthly freezes, automatically apply a freeze for yesterday!
        combined_dates = active_dates.union(freeze_dates)
        day_before_yesterday = yesterday - timedelta(days=1)

        had_active_streak_before = day_before_yesterday in combined_dates
        missed_yesterday = yesterday not in combined_dates

        if missed_yesterday and had_active_streak_before and available_freezes > 0:
            applied = await self.profile_repository.apply_streak_freeze(
                user_id=user.id,
                freeze_date=yesterday,
            )
            if applied:
                freeze_dates.add(yesterday)
                combined_dates.add(yesterday)
                available_freezes -= 1
                logger.info(
                    "Auto-applied monthly streak freeze for user %s on %s (Remaining this month: %d)",
                    user.id,
                    yesterday,
                    available_freezes,
                )

        # 5. If no practice or freeze history exists, return default zero streak
        if not combined_dates:
            return StreakResponse(
                current_streak=0,
                longest_streak=0,
                today_completed=False,
                active_dates=[],
                freeze_dates=[],
                available_freezes=available_freezes,
                total_active_days=0,
            )

        # 6. Calculate longest streak across historical timeline
        sorted_streak_dates = sorted(list(combined_dates))
        longest = 0
        current_run = 0
        prev_date = None
        for d in sorted_streak_dates:
            if prev_date is None:
                current_run = 1
            elif (d - prev_date).days == 1:
                current_run += 1
            elif (d - prev_date).days > 1:
                current_run = 1
            prev_date = d
            if current_run > longest:
                longest = current_run

        # 7. Calculate current active streak
        current_streak = 0
        latest = sorted_streak_dates[-1]
        days_diff = (today - latest).days

        if days_diff <= 1:
            current_streak = 1
            idx = len(sorted_streak_dates) - 1
            while idx > 0 and (sorted_streak_dates[idx] - sorted_streak_dates[idx - 1]).days == 1:
                current_streak += 1
                idx -= 1
        else:
            current_streak = 0

        today_completed = today in active_dates
        active_date_strs = sorted([d.strftime("%Y-%m-%d") for d in active_dates])
        freeze_date_strs = sorted([d.strftime("%Y-%m-%d") for d in freeze_dates])

        return StreakResponse(
            current_streak=current_streak,
            longest_streak=max(longest, current_streak),
            today_completed=today_completed,
            active_dates=active_date_strs,
            freeze_dates=freeze_date_strs,
            available_freezes=available_freezes,
            total_active_days=len(active_dates),
        )