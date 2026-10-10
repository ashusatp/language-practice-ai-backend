import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.language import Language
    from app.models.user import User


class UserLanguageProficiency(BaseModel):
    """Per-language proficiency ratings and practice metrics for a user."""

    __tablename__ = "user_language_proficiencies"
    __table_args__ = (
        UniqueConstraint("user_id", "language_id", name="uq_user_language_proficiency"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    language_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("languages.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    overall_rating: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    fluency_rating: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    grammar_rating: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    pronunciation_rating: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    vocabulary_rating: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    total_sessions: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_minutes: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="language_proficiencies",
    )
    language: Mapped["Language"] = relationship(
        "Language",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<UserLanguageProficiency user_id={self.user_id} language_id={self.language_id} overall_rating={self.overall_rating}>"
