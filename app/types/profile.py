from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class LanguageProficiencyResponse(BaseModel):
    """Proficiency ratings and statistics for a specific language."""

    language_id: uuid.UUID
    language_code: str = Field(..., description="e.g. en-IN, hi-IN")
    language_name: str = Field(..., description="e.g. English, Hindi")
    overall_rating: float = Field(0.0, description="Overall proficiency in this language (1-5 stars)")
    fluency_rating: float = Field(0.0, description="Fluency score (1-5 stars)")
    grammar_rating: float = Field(0.0, description="Grammar score (1-5 stars)")
    pronunciation_rating: float = Field(0.0, description="Pronunciation score (1-5 stars)")
    vocabulary_rating: float = Field(0.0, description="Vocabulary score (1-5 stars)")
    total_sessions: int = Field(0, description="Total completed sessions for this language")
    total_minutes: int = Field(0, description="Total practice minutes for this language")

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    """User proficiency profile and breakdown by language."""

    user_id: uuid.UUID
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    total_sessions: int = Field(0, description="Total completed practice sessions across all languages")
    total_minutes: int = Field(0, description="Total practice duration in minutes")
    languages: list[LanguageProficiencyResponse] = Field(
        default_factory=list,
        description="Per-language proficiency ratings breakdown",
    )

    model_config = ConfigDict(from_attributes=True)


class UpdateUserProfileRequest(BaseModel):
    """Update profile attributes like name or avatar URL."""

    name: Optional[str] = Field(None, max_length=255, description="User full name")
    avatar_url: Optional[str] = Field(None, max_length=1024, description="Avatar image URL")
