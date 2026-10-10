import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth_dependencies import get_current_user
from app.dependencies.session_dependencies import get_session_service
from app.models.user import User
from app.services.session_service import SessionService
from app.types.session import (
    SessionHistoryListResponse,
    SessionRatingRequest,
    SessionStatusResponse,
    SessionSummaryResponse,
)

logger = logging.getLogger("app.api.routes.session")

router = APIRouter(prefix="/session", tags=["Session"])


@router.get(
    "",
    response_model=SessionHistoryListResponse,
    summary="Get user practice session history",
)
async def get_session_history(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    language: Optional[str] = Query(default=None, description="Optional language filter (UUID or code)"),
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> SessionHistoryListResponse:
    """Returns paginated history of past voice practice sessions for the logged-in user."""
    return await session_service.get_user_sessions(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        language_filter=language,
    )


@router.get(
    "/status/{room_id}",
    response_model=SessionStatusResponse,
    summary="Get background processing status for a session room",
)
async def get_session_status(
    room_id: str,
    session_service: SessionService = Depends(get_session_service),
) -> SessionStatusResponse:
    """Polled by the frontend to check if the session summary and AI feedback are ready."""
    return await session_service.get_session_status(room_id=room_id)


@router.post(
    "/{session_id}/rating",
    response_model=SessionSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit rating and feedback for a session",
)
async def submit_session_rating(
    session_id: str,
    request: SessionRatingRequest,
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> SessionSummaryResponse:
    """Submit a 1-5 satisfaction rating and optional written review for a completed session."""
    return await session_service.submit_session_rating(
        identifier=session_id,
        rating_request=request,
    )


@router.get(
    "/{session_id}",
    response_model=SessionSummaryResponse,
    summary="Get session details by ID or room ID",
)
async def get_session_details(
    session_id: str,
    session_service: SessionService = Depends(get_session_service),
) -> SessionSummaryResponse:
    """Convenience endpoint to retrieve full session details and feedback by UUID or room name."""
    return await session_service.get_session_summary(identifier=session_id)
