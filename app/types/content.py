from datetime import datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class LanguageItemResponse(BaseModel):
    """Supported language option."""

    id: uuid.UUID
    code: str
    name: str
    native_name: str
    flag: str
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class VoiceItemResponse(BaseModel):
    """AI Voice partner configuration."""

    id: str  # e.g. 'simran', 'shubh'
    name: str  # e.g. 'Simran'
    gender: str  # 'Female', 'Male'
    accent: str  # 'Indian (Warm & Natural)'
    gradient: str  # 'from-violet-500 to-indigo-600'
    preview_audio_url: Optional[str] = None
    sample_audio_text: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class TopicItemResponse(BaseModel):
    """Practice discussion topic."""

    id: str
    label: str
    hindi_label: str
    category: str

    model_config = ConfigDict(from_attributes=True)


class StreakResponse(BaseModel):
    """User practice streak and heatmap activity."""

    current_streak: int = Field(0, description="Consecutive active practice days")
    longest_streak: int = Field(0, description="Highest consecutive streak achieved")
    today_completed: bool = Field(False, description="Whether user completed a session today")
    active_dates: list[str] = Field(default_factory=list, description="ISO dates YYYY-MM-DD")
    freeze_dates: list[str] = Field(default_factory=list, description="Dates with applied streak freeze")
    available_freezes: int = Field(2, description="Remaining streak freezes")
    total_active_days: int = Field(0, description="Total unique active practice days")


class SessionLanguageSummary(BaseModel):
    id: uuid.UUID
    code: str
    name: str


class SessionVoiceSummary(BaseModel):
    id: str
    name: str
    gender: str

