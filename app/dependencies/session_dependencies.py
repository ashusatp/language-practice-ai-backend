from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.session_repository import SessionRepository
from app.services.session_service import SessionService


def get_session_repository(
    db: AsyncSession = Depends(get_db),
) -> SessionRepository:
    return SessionRepository(db=db)


def get_session_service(
    session_repository: SessionRepository = Depends(get_session_repository),
) -> SessionService:
    return SessionService(session_repository=session_repository)
