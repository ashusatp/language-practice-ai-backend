from datetime import date
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class UserStreakFreeze(BaseModel):
    """Stores dates on which a user's practice streak was shielded by a freeze."""

    __tablename__ = "user_streak_freezes"
    __table_args__ = (
        UniqueConstraint("user_id", "freeze_date", name="uq_user_streak_freeze_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    freeze_date: Mapped[date] = mapped_column(
        Date,
        index=True,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="streak_freezes",
    )

    def __repr__(self) -> str:
        return f"<UserStreakFreeze user_id={self.user_id} freeze_date={self.freeze_date}>"
