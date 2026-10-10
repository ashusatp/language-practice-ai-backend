from datetime import date, datetime, timedelta, timezone
import logging
from typing import Optional
import uuid
from zoneinfo import ZoneInfo

from app.exceptions.custom import (
    AppException,
    CreditsExhaustedException,
    EmailNotVerifiedException,
)
from app.models.user import User
from app.repositories.subscription_repository import SubscriptionRepository
from app.types.subscription import (
    SubscriptionPlanItem,
    SubscriptionPlansResponse,
    SubscriptionStatusResponse,
)

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")

PLAN_CONFIGS = {
    "free": {
        "tier": "free",
        "name": "Free Tier",
        "price_usd": 0.0,
        "minutes_allowance": 10,
        "renewal_type": "lifetime",
        "description": "10 minutes lifetime practice limit. No daily renewals.",
        "features": [
            "10 minutes total voice practice",
            "Access to all practice languages",
            "AI audio conversation with instant responses",
            "Post-session feedback and grammar review",
        ],
    },
    "pro": {
        "tier": "pro",
        "name": "Pro Plan",
        "price_usd": 20.0,
        "minutes_allowance": 60,
        "renewal_type": "daily_ist",
        "description": "60 minutes daily practice quota, renewed every midnight IST ($20/month).",
        "features": [
            "60 minutes practice allowance daily",
            "Daily quota reset at 00:00 IST",
            "Comprehensive pronunciation & grammar ratings",
            "Interactive AI voice practice",
            "Complete session transcripts & vocabulary cards",
        ],
    },
    "pro_max": {
        "tier": "pro_max",
        "name": "Pro Max Plan",
        "price_usd": 30.0,
        "minutes_allowance": 100,
        "renewal_type": "daily_ist",
        "description": "100 minutes daily practice quota, renewed every midnight IST ($30/month).",
        "features": [
            "100 minutes practice allowance daily",
            "Daily quota reset at 00:00 IST",
            "Highest priority processing",
            "In-depth fluency progress tracking & streaks",
            "Unlimited conversation feedback review",
        ],
    },
}


class SubscriptionService:
    """Handles business logic for tier plans, quota calculations, IST daily resets, and deductions."""

    def __init__(self, subscription_repository: SubscriptionRepository):
        self.subscription_repository = subscription_repository

    @staticmethod
    def get_today_ist() -> date:
        """Returns the current calendar date in Indian Standard Time (IST)."""
        return datetime.now(timezone.utc).astimezone(IST).date()

    @staticmethod
    def get_next_reset_ist() -> datetime:
        """Returns the next midnight IST timestamp in UTC."""
        now_ist = datetime.now(timezone.utc).astimezone(IST)
        tomorrow_midnight_ist = (now_ist + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return tomorrow_midnight_ist.astimezone(timezone.utc)

    def get_plans(self) -> SubscriptionPlansResponse:
        """Returns the available subscription tiers with pricing and quotas."""
        items = [SubscriptionPlanItem(**info) for info in PLAN_CONFIGS.values()]
        return SubscriptionPlansResponse(plans=items)

    async def get_user_credit_status(self, user: User) -> SubscriptionStatusResponse:
        """Calculates current plan usage, remaining minutes, and practice eligibility."""
        subscription = await self.subscription_repository.get_or_create_subscription(user.id)
        tier = subscription.tier if subscription.tier in PLAN_CONFIGS else "free"
        plan_meta = PLAN_CONFIGS[tier]

        if tier == "free":
            limit = plan_meta["minutes_allowance"]
            used = subscription.free_lifetime_minutes_used
            remaining = max(0, limit - used)
            reset_type = "lifetime"
            next_reset = None
        else:
            today_ist = self.get_today_ist()
            daily_usage = await self.subscription_repository.get_daily_usage(user.id, today_ist)
            limit = plan_meta["minutes_allowance"]
            used = daily_usage.minutes_used if daily_usage else 0
            remaining = max(0, limit - used)
            reset_type = "daily_ist"
            next_reset = self.get_next_reset_ist()

        is_verified = bool(user.is_email_verified)
        can_practice = is_verified and (remaining > 0)

        return SubscriptionStatusResponse(
            tier=tier,
            plan_name=plan_meta["name"],
            status=subscription.status,
            price_usd=plan_meta["price_usd"],
            minutes_limit=limit,
            minutes_used=used,
            remaining_minutes=remaining,
            reset_type=reset_type,
            next_reset_at=next_reset,
            can_practice=can_practice,
            is_email_verified=is_verified,
        )

    async def check_can_start_session(self, user: User) -> SubscriptionStatusResponse:
        """Enforces access gatekeeping before connecting to voice practice.

        Raises:
            EmailNotVerifiedException: If user email is unverified.
            CreditsExhaustedException: If the user has exhausted their free lifetime or daily allowance.
        """
        if not user.is_email_verified:
            logger.warning("Access denied: User %s (%s) has not verified email.", user.id, user.email)
            raise EmailNotVerifiedException(
                "Please verify your email address to access voice practice sessions."
            )

        status = await self.get_user_credit_status(user)
        if status.remaining_minutes <= 0:
            logger.warning(
                "Access denied: User %s has exhausted practice minutes (%d/%d used, tier=%s).",
                user.id,
                status.minutes_used,
                status.minutes_limit,
                status.tier,
            )
            if status.tier == "free":
                message = "You have exhausted your 10 minutes free lifetime allowance. Please upgrade to Pro to continue practicing."
            else:
                message = f"You have reached your daily allowance of {status.minutes_limit} minutes. Your quota resets at midnight IST."
            raise CreditsExhaustedException(message)

        return status

    async def deduct_session_minutes(self, user_id: uuid.UUID, duration_mins: int) -> None:
        """Deducts consumed practice minutes from user's quota."""
        if duration_mins <= 0:
            return

        today_ist = self.get_today_ist()
        await self.subscription_repository.record_usage(
            user_id=user_id,
            duration_mins=duration_mins,
            usage_date=today_ist,
        )

    async def upgrade_subscription(self, user: User, target_tier: str) -> SubscriptionStatusResponse:
        """Upgrades user subscription to a paid tier ('pro' or 'pro_max')."""
        # if target_tier not in ("pro", "pro_max"):
        #     raise AppException(f"Invalid target tier: '{target_tier}'. Must be 'pro' or 'pro_max'.", status_code=400)

        # await self.subscription_repository.update_tier(user.id, target_tier)
        # return await self.get_user_credit_status(user)
        pass
