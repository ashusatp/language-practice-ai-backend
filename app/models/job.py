from datetime import datetime
import uuid
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.session import Session


class Job(BaseModel):
    """Background job entity for session processing with transactional queue & retry support."""

    __tablename__ = "jobs"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        String(50),
        default="generate_summary",
        nullable=False,
    )  # e.g., 'generate_summary'
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        index=True,
        nullable=False,
    )  # 'pending', 'processing', 'completed', 'failed'
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    payload: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    result: Mapped[Optional[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="jobs")

    def __repr__(self) -> str:
        return f"<Job id={self.id} type={self.type} status={self.status} attempts={self.attempts}>"
