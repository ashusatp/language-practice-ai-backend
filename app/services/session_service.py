import logging
import uuid
from typing import Optional

from app.exceptions.custom import SessionNotFoundException
from app.repositories.session_repository import SessionRepository
from app.types.session import (
    SessionHistoryListResponse,
    SessionRatingRequest,
    SessionStatusResponse,
    SessionSummaryResponse,
)

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self, session_repository: SessionRepository):
        self.session_repository = session_repository

    async def get_user_sessions(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 10,
        language_filter: Optional[str] = None,
    ) -> SessionHistoryListResponse:
        """Fetch paginated history of past practice sessions for a user."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size

        return await self.session_repository.get_user_sessions(
            user_id=user_id,
            offset=offset,
            limit=page_size,
            language_filter=language_filter,
        )

    async def get_session_summary(self, identifier: str) -> SessionSummaryResponse:
        """Fetch session and feedback by UUID or room_id and return SessionSummaryResponse."""
        session = await self.session_repository.get_session_by_id_or_room(identifier)
        if not session:
            logger.warning("Session not found for identifier: %s", identifier)
            raise SessionNotFoundException(f"Session '{identifier}' not found")

        fb = session.feedback
        return SessionSummaryResponse(
            session_id=session.id,
            room_id=session.room_id,
            status=session.status,
            topic=session.topic or "General Conversation",
            started_at=session.started_at,
            ended_at=session.ended_at,
            user_rating=fb.user_rating if fb else None,
            user_review=fb.user_review if fb else None,
            summary=fb.summary if fb else "No speech was detected during this session.",
            sentiment=fb.sentiment if fb else "neutral",
            key_points=fb.key_points if fb else [],
            action_items=fb.action_items if fb else [],
            mistakes=fb.mistakes if fb else [],
            scores=fb.scores if fb else {},
            key_vocabulary=fb.key_vocabulary if fb else [],
            transcript=session.transcript,
        )

    async def get_session_status(self, room_id: str) -> SessionStatusResponse:
        """Get background summary processing status for a given room."""
        return await self.session_repository.get_session_status_by_room_id(room_id)

    async def submit_session_rating(
        self,
        identifier: str,
        rating_request: SessionRatingRequest,
    ) -> SessionSummaryResponse:
        """Submit or update user rating and review for a session."""
        session = await self.session_repository.get_session_by_id_or_room(identifier)
        if not session:
            logger.warning("Cannot rate session: Session not found for %s", identifier)
            raise SessionNotFoundException(f"Session '{identifier}' not found")

        await self.session_repository.update_session_rating(
            session_id=session.id,
            rating=rating_request.rating,
            user_review=rating_request.user_review,
        )

        return await self.get_session_summary(str(session.id))
