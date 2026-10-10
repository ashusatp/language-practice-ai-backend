from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

SubscriptionTierType = Literal["free", "pro", "pro_max"]


class SubscriptionStatusResponse(BaseModel):
    """Current subscription credit status and quota allowance."""

    tier: str = Field(..., description="Plan tier: free, pro, pro_max")
    plan_name: str = Field(..., description="Display name of the plan")
    status: str = Field("active", description="Subscription status")
    price_usd: float = Field(..., description="Monthly plan price in USD")
    minutes_limit: int = Field(..., description="Minutes limit: lifetime for free, daily for pro/pro_max")
    minutes_used: int = Field(..., description="Minutes used in current period")
    remaining_minutes: int = Field(..., description="Minutes left to practice")
    reset_type: str = Field(..., description="'lifetime' or 'daily_ist'")
    next_reset_at: Optional[datetime] = Field(None, description="Next midnight IST reset time for daily plans")
    can_practice: bool = Field(..., description="True if remaining_minutes > 0 and email is verified")
    is_email_verified: bool = Field(..., description="Whether user email is verified")


class SubscriptionPlanItem(BaseModel):
    tier: str
    name: str
    price_usd: float
    minutes_allowance: int
    renewal_type: str
    description: str
    features: list[str]


class SubscriptionPlansResponse(BaseModel):
    plans: list[SubscriptionPlanItem]


class SubscriptionUpgradeRequest(BaseModel):
    tier: Literal["pro", "pro_max"] = Field(..., description="Target tier to upgrade to")
