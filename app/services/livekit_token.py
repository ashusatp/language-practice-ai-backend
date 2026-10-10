import json
import logging
import uuid
from typing import Any, Optional
from google.protobuf.json_format import ParseDict
from livekit import api
from sqlalchemy.ext.asyncio import AsyncSession
from config import config
from app.models.session import Session
from app.models.user import User
from app.types.livekit import LiveKitTokenRequest, LiveKitTokenResponse
from app.types.subscription import SubscriptionStatusResponse

logger = logging.getLogger(__name__)


class LiveKitTokenService:
    """Service to generate standardized LiveKit access tokens and manage sessions."""

    async def generate_token(
        self,
        request: LiveKitTokenRequest,
        user: Optional[User] = None,
        credit_status: Optional[SubscriptionStatusResponse] = None,
    ) -> LiveKitTokenResponse:
        """Generates a LiveKit JWT token adhering to LiveKit standard endpoint specification."""

        config.validate_livekit()

        # Generate or resolve room name and participant identity
        room_name = (
            request.room_name.strip()
            if request.room_name
            else f"room_{uuid.uuid4().hex[:10]}"
        )
        participant_identity = (
            request.participant_identity.strip()
            if request.participant_identity
            else (f"user_{user.id}" if user else f"guest_{uuid.uuid4().hex[:8]}")
        )
        participant_name = (
            request.participant_name.strip()
            if request.participant_name
            else (user.email.split("@")[0] if user else participant_identity)
        )

        # Build LiveKit AccessToken
        token = (
            api.AccessToken(config.livekit_api_key, config.livekit_api_secret)
            .with_identity(participant_identity)
            .with_name(participant_name)
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
        )

        # Consolidate metadata dictionary for LiveKit participant
        meta_dict: dict[str, Any] = {}
        if isinstance(request.participant_metadata, dict):
            meta_dict.update(request.participant_metadata)
        elif isinstance(request.participant_metadata, str):
            try:
                meta_dict.update(json.loads(request.participant_metadata))
            except Exception:
                meta_dict["raw"] = request.participant_metadata

        if request.voice and "voice" not in meta_dict:
            meta_dict["voice"] = str(request.voice)
        if request.language and "language" not in meta_dict:
            meta_dict["language"] = str(request.language)
        if user and "user_id" not in meta_dict:
            meta_dict["user_id"] = str(user.id)
        if credit_status:
            meta_dict["tier"] = str(credit_status.tier)
            meta_dict["remaining_minutes"] = int(credit_status.remaining_minutes)

        if meta_dict:
            token.with_metadata(json.dumps(meta_dict))


        if request.participant_attributes:
            token.with_attributes(request.participant_attributes)

        if request.room_config:
            try:
                room_cfg = ParseDict(request.room_config, api.RoomConfiguration())
                token.with_room_config(room_cfg)
            except Exception as e:
                logger.warning("Failed to parse room_config for LiveKit token: %s", e)

        jwt_token = token.to_jwt()

        # Database session is NOT created here. It is agent-driven,
        # created when user actually connects to the room in rtc_entrypoint.py.
        return LiveKitTokenResponse(
            server_url=config.livekit_url,
            participant_token=jwt_token,
            room_name=room_name,
            participant_identity=participant_identity,
            session_id=None,
        )
