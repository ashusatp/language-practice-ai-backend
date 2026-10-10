from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.subscription_service import SubscriptionService


def get_subscription_repository(
    db: AsyncSession = Depends(get_db),
) -> SubscriptionRepository:
    return SubscriptionRepository(db=db)


def get_subscription_service(
    subscription_repository: SubscriptionRepository = Depends(get_subscription_repository),
) -> SubscriptionService:
    return SubscriptionService(subscription_repository=subscription_repository)
