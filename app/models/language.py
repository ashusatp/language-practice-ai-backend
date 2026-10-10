from typing import TYPE_CHECKING
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.session import Session
    from app.models.voice import Voice


class Language(BaseModel):
    """Supported language entity."""

    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)  # e.g., 'en-US', 'hi-IN'
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., 'English (US)', 'Hindi'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    voices: Mapped[list["Voice"]] = relationship("Voice", back_populates="language")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="language")

    def __repr__(self) -> str:
        return f"<Language code={self.code} name={self.name}>"
