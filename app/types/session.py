from datetime import datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class SessionStatusResponse(BaseModel):
    """Status response polled by the frontend animation."""

    session_id: Optional[uuid.UUID] = None
    room_id: Optional[str] = None
    session_status: str = "connecting"  # 'connecting', 'active', 'completed', 'failed'
    job_status: Optional[str] = None  # 'pending', 'processing', 'completed', 'failed'
    is_ready: bool = False  # True when summary is completely generated
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SessionSummaryResponse(BaseModel):
    """Full session summary and conversation conclusions."""

    session_id: uuid.UUID
    room_id: str
    status: str
    topic: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    user_rating: Optional[int] = None
    user_review: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    key_points: Optional[list[str]] = None
    action_items: Optional[list[str]] = None
    mistakes: Optional[list[dict[str, Any]]] = None
    scores: Optional[dict[str, float]] = None
    key_vocabulary: Optional[list[str]] = None
    transcript: Optional[list[dict[str, Any]]] = None

    model_config = ConfigDict(from_attributes=True)


class SessionRatingRequest(BaseModel):
    """User rating and review submission."""

    rating: Optional[int] = Field(default=None, ge=1, le=5, description="Optional feedback rating 1-5")
    user_review: Optional[str] = Field(default=None, description="Optional text feedback")


class SessionLanguageSummary(BaseModel):
    id: uuid.UUID
    code: str
    name: str


class SessionVoiceSummary(BaseModel):
    id: str
    name: str
    gender: str


class SessionHistoryItemResponse(BaseModel):
    """Past session item for history list."""

    id: uuid.UUID
    room_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0
    language: Optional[SessionLanguageSummary] = None
    voice: Optional[SessionVoiceSummary] = None
    topic: Optional[str] = None
    overall_rating: Optional[float] = None
    user_rating: Optional[int] = None
    scores: Optional[dict[str, float]] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    mistakes_count: int = 0
    key_points: Optional[list[str]] = None
    action_items: Optional[list[str]] = None
    mistakes: Optional[list[dict[str, Any]]] = None
    key_vocabulary: Optional[list[str]] = None
    transcript: Optional[list[dict[str, Any]]] = None


class SessionHistoryListResponse(BaseModel):
    """Paginated list of user past practice sessions."""

    total: int
    items: list[SessionHistoryItemResponse]