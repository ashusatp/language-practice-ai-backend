from datetime import date, datetime, timedelta, timezone
import logging
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import UserDailyUsage, UserSubscription

logger = logging.getLogger(__name__)


class SubscriptionRepository:
    """Repository handling database operations for user subscriptions and daily usage tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_subscription(self, user_id: uuid.UUID) -> Optional[UserSubscription]:
        """Fetches the user's subscription record if it exists."""
        try:
            query = select(UserSubscription).where(UserSubscription.user_id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get subscription for user %s: %s", user_id, e, exc_info=True)
            raise e

    async def get_or_create_subscription(self, user_id: uuid.UUID) -> UserSubscription:
        """Retrieves user subscription or creates a default 'free' tier subscription if none exists."""
        subscription = await self.get_subscription(user_id)
        if subscription:
            return subscription

        try:
            subscription = UserSubscription(
                user_id=user_id,
                tier="free",
                status="active",
                free_lifetime_minutes_used=0,
                current_period_start=datetime.now(timezone.utc),
            )
            self.db.add(subscription)
            await self.db.commit()
            await self.db.refresh(subscription)
            logger.info("Created default free subscription for user %s", user_id)
            return subscription
        except Exception as e:
            logger.error("Failed to create subscription for user %s: %s", user_id, e, exc_info=True)
            await self.db.rollback()
            # In case of concurrent creation race condition, retry fetch
            existing = await self.get_subscription(user_id)
            if existing:
                return existing
            raise e

    async def get_daily_usage(self, user_id: uuid.UUID, usage_date: date) -> Optional[UserDailyUsage]:
        """Fetches daily usage for a user on a given IST calendar date."""
        try:
            query = select(UserDailyUsage).where(
                UserDailyUsage.user_id == user_id,
                UserDailyUsage.usage_date == usage_date,
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get daily usage for user %s on date %s: %s", user_id, usage_date, e, exc_info=True)
            raise e

    async def get_or_create_daily_usage(self, user_id: uuid.UUID, usage_date: date) -> UserDailyUsage:
        """Retrieves or initializes a daily usage record for the specified user and IST date."""
        usage = await self.get_daily_usage(user_id, usage_date)
        if usage:
            return usage

        try:
            usage = UserDailyUsage(
                user_id=user_id,
                usage_date=usage_date,
                minutes_used=0,
                sessions_count=0,
            )
            self.db.add(usage)
            await self.db.commit()
            await self.db.refresh(usage)
            return usage
        except Exception as e:
            logger.error("Failed to create daily usage for user %s on %s: %s", user_id, usage_date, e, exc_info=True)
            await self.db.rollback()
            existing = await self.get_daily_usage(user_id, usage_date)
            if existing:
                return existing
            raise e

    async def record_usage(
        self,
        user_id: uuid.UUID,
        duration_mins: int,
        usage_date: date,
    ) -> UserSubscription:
        """Deducts / records practice minutes based on the user's active tier."""
        subscription = await self.get_or_create_subscription(user_id)

        if subscription.tier == "free":
            subscription.free_lifetime_minutes_used += duration_mins
            await self.db.commit()
            await self.db.refresh(subscription)
            logger.info(
                "Updated free lifetime minutes for user %s: +%d mins (total used: %d)",
                user_id,
                duration_mins,
                subscription.free_lifetime_minutes_used,
            )
        else:
            daily_usage = await self.get_or_create_daily_usage(user_id, usage_date)
            daily_usage.minutes_used += duration_mins
            daily_usage.sessions_count += 1
            await self.db.commit()
            await self.db.refresh(daily_usage)
            logger.info(
                "Updated daily usage for %s user %s on %s: +%d mins (today used: %d)",
                subscription.tier,
                user_id,
                usage_date,
                duration_mins,
                daily_usage.minutes_used,
            )

        return subscription

    async def update_tier(self, user_id: uuid.UUID, new_tier: str) -> UserSubscription:
        """Upgrades or updates the tier of a user's subscription."""
        subscription = await self.get_or_create_subscription(user_id)
        now = datetime.now(timezone.utc)
        subscription.tier = new_tier
        subscription.status = "active"
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=30)

        await self.db.commit()
        await self.db.refresh(subscription)
        logger.info("Updated user %s subscription to tier '%s'", user_id, new_tier)
        return subscription
