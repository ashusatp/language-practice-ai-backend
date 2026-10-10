import logging
from fastapi import APIRouter, Depends, status

from app.dependencies.auth_dependencies import get_current_user
from app.dependencies.subscription_dependencies import get_subscription_service
from app.models.user import User
from app.services.subscription_service import SubscriptionService
from app.types.subscription import (
    SubscriptionPlansResponse,
    SubscriptionStatusResponse,
    SubscriptionUpgradeRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription", tags=["Subscription & Credits"])


@router.get(
    "/me",
    response_model=SubscriptionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user subscription and practice credit status",
)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionStatusResponse:
    """Returns the authenticated user's tier, usage, remaining minutes, and verification status."""
    return await subscription_service.get_user_credit_status(current_user)


@router.get(
    "/plans",
    response_model=SubscriptionPlansResponse,
    status_code=status.HTTP_200_OK,
    summary="Get available subscription plans",
)
async def get_plans(
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionPlansResponse:
    """Returns all available subscription plans with pricing and quota details."""
    return subscription_service.get_plans()


# @router.post(
#     "/upgrade",
#     response_model=SubscriptionStatusResponse,
#     status_code=status.HTTP_200_OK,
#     summary="Upgrade user subscription tier",
# )
# async def upgrade_subscription(
#     request: SubscriptionUpgradeRequest,
#     current_user: User = Depends(get_current_user),
#     subscription_service: SubscriptionService = Depends(get_subscription_service),
# ) -> SubscriptionStatusResponse:
#     """Upgrades user subscription to Pro ($20/mo) or Pro Max ($30/mo)."""
#     return await subscription_service.upgrade_subscription(current_user, request.tier)


@router.get(
    "/check-access",
    response_model=SubscriptionStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check if user has remaining quota and verified email for practice",
)
async def check_access(
    current_user: User = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionStatusResponse:
    """Validates email verification and quota availability. Raises 403 if blocked."""
    return await subscription_service.check_can_start_session(current_user)
