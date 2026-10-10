from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.profile import UserLanguageProficiency
    from app.models.session import Session
    from app.models.streak_freeze import UserStreakFreeze
    from app.models.subscription import UserDailyUsage, UserSubscription


class User(BaseModel):
    """User database model."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    verification_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    verification_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    language_proficiencies: Mapped[list["UserLanguageProficiency"]] = relationship(
        "UserLanguageProficiency",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    streak_freezes: Mapped[list["UserStreakFreeze"]] = relationship(
        "UserStreakFreeze",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    subscription: Mapped[Optional["UserSubscription"]] = relationship(
        "UserSubscription",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    daily_usages: Mapped[list["UserDailyUsage"]] = relationship(
        "UserDailyUsage",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
