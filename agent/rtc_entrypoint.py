from app.utils.jwt import decode_access_token
import asyncio
import ctypes
import json
import logging
import os
from agent.providers import STT, TTS
from app.services.session_processor import SessionProcessorService
from livekit import agents
from livekit.agents import AgentSession, inference, TurnHandlingOptions, room_io
from livekit.plugins import ai_coustics

# Suppress benign AssertionError in LiveKit FfiHandle.__del__ on worker subprocess teardown
try:
    from livekit.rtc._ffi_client import FfiClient, FfiHandle, INVALID_HANDLE

    def _safe_ffi_dispose(self) -> None:
        if self.handle != INVALID_HANDLE and not self._disposed:
            self._disposed = True
            ffi = FfiClient._instance
            if ffi is None or ffi._pid != os.getpid():
                return
            try:
                ffi._ffi_lib.livekit_ffi_drop_handle(ctypes.c_uint64(self.handle))
            except Exception:
                pass

    FfiHandle.dispose = _safe_ffi_dispose
except Exception:
    pass

from .agent import Assistant

logger = logging.getLogger("agent.rtc_entrypoint")


async def rtc_entrypoint(ctx: agents.JobContext):
    # 1. Connect to the room first
    await ctx.connect()

    # 2. Wait for the user to join
    participant = await ctx.wait_for_participant()

    # 3. Parse the JSON metadata sent by frontend
    metadata = {}
    if participant.metadata:
        try:
            metadata = json.loads(participant.metadata)
        except json.JSONDecodeError:
            pass

    selected_language = metadata.get("language", "english")  # "english" | "hindi"
    selected_topic = metadata.get("topic", "daily-life")
    skill_level = metadata.get("skillLevel", "intermediate")
    selected_voice = metadata.get("voice", "shubh")

    # Get user_id from metadata (passed by frontend)
    user_access_token = metadata.get("access_token")
    if not user_access_token:
        logger.error("No access token provided in metadata")
        return

    # Decode access token
    try:
        payload = decode_access_token(user_access_token)
        user_id = payload.get("user_id")
        if not user_id:
            logger.error("Invalid access token payload")
            return
    except Exception as e:
        logger.error(f"Failed to decode access token: {str(e)}")
        return

    # 4. Initialize / link database session
    db_session = await SessionProcessorService.get_or_create_session(
        user_id=user_id,
        room_id=ctx.room.name,
        metadata=metadata,
    )

    stt_provider = STT(selected_language)
    tts_provider = TTS(selected_language, speaker=selected_voice)

    session = AgentSession(
        stt=stt_provider.stt,
        llm=inference.LLM(model="google/gemma-4-31b-it"),
        tts=tts_provider.tts,
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
        ),
    )

    agent = Assistant(
        language=selected_language,
        topic=selected_topic,
        skill_level=skill_level,
    )

    # 5. Setup session end event listener to save transcript and enqueue summary job
    session_ended = False

    async def on_session_ended():
        nonlocal session_ended
        if session_ended:
            return
        session_ended = True

        logger.info("Session %s ending. Extracting transcripts...", db_session.id)
        transcript_turns = []
        try:
            if hasattr(session, "history") and session.history:
                msgs = (
                    session.history.messages()
                    if callable(session.history.messages)
                    else session.history.messages
                )
                for msg in msgs:
                    text = getattr(msg, "text_content", None)
                    if not text and hasattr(msg, "content"):
                        content_val = msg.content
                        if isinstance(content_val, list):
                            text = " ".join(str(c) for c in content_val)
                        else:
                            text = str(content_val)
                    if text and str(text).strip():
                        role_str = (
                            str(getattr(msg, "role", "user"))
                            .replace("ChatMessageRole.", "")
                            .replace("ChatRole.", "")
                            .lower()
                        )
                        transcript_turns.append({
                            "role": role_str,
                            "text": str(text).strip(),
                        })
        except Exception as e:
            logger.warning("Error reading session history messages: %s", e)

        try:
            await SessionProcessorService.finish_session_and_enqueue_summary(
                session_id=db_session.id,
                transcript_messages=transcript_turns,
            )
        except Exception as e:
            logger.error("Failed to finish session and enqueue summary: %s", e, exc_info=True)

    # Attach listeners for room disconnect and job shutdown
    ctx.add_shutdown_callback(on_session_ended)

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(p):
        logger.info("Participant %s disconnected from room %s", p.identity, ctx.room.name)
        asyncio.create_task(on_session_ended())

    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S
                ),
            ),
        ),
    )

    await session.generate_reply(
        instructions=(
            f"Warmly greet the user in {selected_language}, introduce yourself as their conversation partner, "
            f"and ask an opening question about {selected_topic}."
        )
    )
