import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User



logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        try: 
            query = select(User).where(User.email == email)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get user by email: {str(e)}", exc_info=True)
            raise e

    async def get_user_by_id(self, user_id: str) -> User | None:
        try:
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get user by id: {str(e)}", exc_info=True)
            raise e

    async def create_user(self, user: User) -> User:
        try:
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)
            logger.info(f"User created successfully: {user.id}")
            return user
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise e