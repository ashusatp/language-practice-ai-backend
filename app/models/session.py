import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.feedback import SessionFeedback
    from app.models.job import Job
    from app.models.language import Language
    from app.models.user import User
    from app.models.voice import Voice


class Session(BaseModel):
    """Voice agent call session entity."""

    __tablename__ = "sessions"

    started_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    voice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("voices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    language_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("languages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    room_id: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    topic: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
    )  # 'active', 'completed', 'failed', 'cancelled'
    transcript: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="sessions",
    )
    voice: Mapped[Optional["Voice"]] = relationship(
        "Voice",
        back_populates="sessions",
    )
    language: Mapped[Optional["Language"]] = relationship(
        "Language",
        back_populates="sessions",
    )
    feedback: Mapped[Optional["SessionFeedback"]] = relationship(
        "SessionFeedback",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} room_id={self.room_id} status={self.status}>"
