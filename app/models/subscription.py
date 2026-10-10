from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class UserSubscription(BaseModel):
    """User subscription entity defining their plan tier and free lifetime usage."""

    __tablename__ = "user_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    tier: Mapped[str] = mapped_column(
        String(50),
        default="free",
        nullable=False,
    )  # 'free', 'pro', 'pro_max'
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
    )  # 'active', 'cancelled', 'expired'
    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    free_lifetime_minutes_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="subscription",
    )

    def __repr__(self) -> str:
        return f"<UserSubscription user_id={self.user_id} tier={self.tier} status={self.status}>"


class UserDailyUsage(BaseModel):
    """Tracks daily practice minutes consumed by a user on an IST calendar date."""

    __tablename__ = "user_daily_usages"
    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", name="uq_user_daily_usage_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    usage_date: Mapped[date] = mapped_column(
        Date,
        index=True,
        nullable=False,
    )  # IST calendar date
    minutes_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    sessions_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="daily_usages",
    )

    def __repr__(self) -> str:
        return f"<UserDailyUsage user_id={self.user_id} usage_date={self.usage_date} minutes_used={self.minutes_used}>"
