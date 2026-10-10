import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.session import Session


class SessionFeedback(BaseModel):
    """Session summary and AI processed feedback entity."""

    __tablename__ = "session_feedbacks"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # Overall AI summary / conclusion
    sentiment: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # 'positive', 'neutral', 'negative'
    key_points: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )  # List of conclusions/points extracted from transcript
    action_items: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )  # Action items/next steps
    mistakes: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )  # List of detected speech/grammar mistakes and suggested corrections
    scores: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )  # Fluency, pronunciation, grammar, vocabulary, overall scores (1.0 to 5.0)
    key_vocabulary: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )  # List of notable vocabulary words learned/discussed
    user_rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )  # Optional user satisfaction rating (1 to 5)
    user_review: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # Direct textual feedback from user
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="feedback",
    )

    def __repr__(self) -> str:
        return f"<SessionFeedback id={self.id} session_id={self.session_id}>"
