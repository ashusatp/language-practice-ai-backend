import asyncio
import logging
from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401 - ensure all models are registered

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db() -> None:
    async with engine.begin() as conn:
        logger.info("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
