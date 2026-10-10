import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.language import Language
    from app.models.session import Session


class Voice(BaseModel):
    """Voice configuration entity."""

    __tablename__ = "voices"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    voice_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'cartesia', 'elevenlabs', 'sarvam'
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'male', 'female', 'neutral'
    language_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("languages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    preview_audio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    language: Mapped[Optional["Language"]] = relationship("Language", back_populates="voices")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="voice")

    def __repr__(self) -> str:
        return f"<Voice name={self.name} provider={self.provider}>"
