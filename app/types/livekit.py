from typing import Any, Optional
import uuid
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, computed_field


class LiveKitTokenRequest(BaseModel):
    """LiveKit standardized token generation request schema with flexible aliases."""

    room_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("room_name", "roomName", "room", "room_id", "roomId"),
        description="Room name to join",
    )
    participant_identity: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "participant_identity", "participantIdentity", "identity", "userId", "user_id"
        ),
        description="Unique identity for participant",
    )
    participant_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("participant_name", "participantName", "name", "username"),
        description="Display name for participant",
    )
    participant_metadata: Optional[Any] = Field(
        default=None,
        validation_alias=AliasChoices("participant_metadata", "participantMetadata", "metadata"),
        description="Custom application metadata (string or dict)",
    )
    participant_attributes: Optional[dict[str, str]] = Field(
        default=None,
        validation_alias=AliasChoices(
            "participant_attributes", "participantAttributes", "attributes"
        ),
        description="Custom application key-value attributes",
    )
    room_config: Optional[dict[str, Any]] = Field(
        default=None,
        validation_alias=AliasChoices("room_config", "roomConfig"),
        description="Room level configuration including agent dispatch",
    )

    # Optional voice & language preferences (accepts UUID or name string)
    voice: Optional[Any] = Field(
        default=None,
        validation_alias=AliasChoices("voice", "voice_id", "voiceId"),
        description="Voice name or voice UUID",
    )
    language: Optional[Any] = Field(
        default=None,
        validation_alias=AliasChoices("language", "language_id", "languageId"),
        description="Language code or language UUID",
    )

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class LiveKitTokenResponse(BaseModel):
    """LiveKit standardized token generation response schema."""

    server_url: str = Field(description="LiveKit server connection WebSocket URL")
    participant_token: str = Field(description="Generated LiveKit JWT access token")
    room_name: str = Field(description="Room name joined")
    participant_identity: str = Field(description="Participant unique identity")
    session_id: Optional[uuid.UUID] = Field(
        default=None, description="Internal database session ID"
    )

    # Convenience aliases for standard React client libraries
    @computed_field
    @property
    def token(self) -> str:
        return self.participant_token

    @computed_field
    @property
    def url(self) -> str:
        return self.server_url

    model_config = ConfigDict(from_attributes=True)
