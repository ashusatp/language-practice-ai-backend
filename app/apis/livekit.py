from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.dependencies.auth_dependencies import get_current_user
from app.models.user import User
from app.types.livekit import LiveKitTokenRequest, LiveKitTokenResponse
from app.services.livekit_token import LiveKitTokenService

router = APIRouter(prefix="/livekit", tags=["LiveKit Authentication"])

def get_livekit_token_service() -> LiveKitTokenService:
    return LiveKitTokenService()


@router.post(
    "/token",
    response_model=LiveKitTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate LiveKit participant token (Standard Endpoint)",
    description=(
        "Adheres to LiveKit's standardized endpoint token generation specification. "
        "Returns server_url and participant_token. Supports optional Bearer auth."
    ),
)
async def generate_token_post(
    body: Optional[LiveKitTokenRequest] = None,
    room: Optional[str] = Query(default=None, description="Room name"),
    room_name: Optional[str] = Query(default=None, description="Room name alias"),
    identity: Optional[str] = Query(default=None, description="Participant identity"),
    participant_identity: Optional[str] = Query(
        default=None, description="Participant identity alias"
    ),
    name: Optional[str] = Query(default=None, description="Participant display name"),
    voice: Optional[str] = Query(default=None, description="Voice ID or name"),
    language: Optional[str] = Query(default=None, description="Language code or name"),
    current_user: Optional[User] = Depends(get_current_user),
    token_service: LiveKitTokenService = Depends(get_livekit_token_service),
) -> LiveKitTokenResponse:
    """Standard POST endpoint used by LiveKit frontend TokenSource."""
    req = body or LiveKitTokenRequest()
    if not req.room_name and (room or room_name):
        req.room_name = room or room_name
    if not req.participant_identity and (identity or participant_identity):
        req.participant_identity = identity or participant_identity
    if not req.participant_name and name:
        req.participant_name = name
    if not req.voice and voice:
        req.voice = voice
    if not req.language and language:
        req.language = language

    return await token_service.generate_token(req, user=current_user)


@router.get(
    "/token",
    response_model=LiveKitTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate LiveKit token via GET (Query parameters)",
    description="Convenience GET endpoint compatible with React quickstart hooks and Sandbox.",
)
async def generate_token_get(
    room: Optional[str] = Query(default=None, description="Room name"),
    room_name: Optional[str] = Query(default=None, description="Room name alias"),
    identity: Optional[str] = Query(default=None, description="Participant identity"),
    participant_identity: Optional[str] = Query(
        default=None, description="Participant identity alias"
    ),
    name: Optional[str] = Query(default=None, description="Participant display name"),
    current_user: Optional[User] = Depends(get_current_user),
    token_service: LiveKitTokenService = Depends(get_livekit_token_service),
) -> LiveKitTokenResponse:
    """Convenience GET endpoint for React frontend fetchers."""
    req = LiveKitTokenRequest(
        room_name=room or room_name,
        participant_identity=identity or participant_identity,
        participant_name=name,
    )
    return await token_service.generate_token(req, user=current_user)
