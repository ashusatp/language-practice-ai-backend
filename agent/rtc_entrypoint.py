import asyncio
from collections.abc import AsyncGenerator, AsyncIterable
import ctypes
from datetime import datetime, timezone
import json
import logging
import os
import re

from agent.providers import STT, TTS
from app.services.session_processor import SessionProcessorService
from app.utils.jwt import decode_access_token
from livekit import agents
from livekit.agents import AgentSession, inference, TurnHandlingOptions, room_io
from livekit.agents.voice import CloseEvent, CloseReason, ErrorEvent
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


async def clean_speech_for_tts(text_stream: AsyncIterable[str]) -> AsyncGenerator[str, None]:
    """Filters out empty chunks, isolated asterisks, and stage directions before passing to TTS."""
    async for chunk in text_stream:
        # Strip stage directions in asterisks or brackets (e.g. *smiles*, [sigh])
        cleaned = re.sub(r"\*[^*]+\*", "", chunk)
        cleaned = re.sub(r"\[[^\]]+\]", "", cleaned)
        cleaned = cleaned.replace("*", "").replace("`", "").replace("#", "")
        # Only yield if meaningful speech tokens remain
        if cleaned.strip():
            yield cleaned


async def rtc_entrypoint(ctx: agents.JobContext):
    session_killed = False
    db_session = None
    session: AgentSession | None = None

    async def wrap_session_and_kill(
        status: str = "completed",
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        nonlocal session_killed
        if session_killed:
            return
        session_killed = True

        is_error = bool(error_code or error_message or status == "failed")
        logger.info(
            "Terminating session %s (is_error=%s, status=%s, code=%s, message=%s)",
            ctx.room.name if ctx.room else "unknown",
            is_error,
            status,
            error_code,
            error_message,
        )

        # 1. If an error occurred, notify the UI immediately over reliable LiveKit data channel
        if is_error and ctx.room and ctx.room.local_participant:
            try:
                error_payload = json.dumps({
                    "type": "agent_error",
                    "code": error_code or "AGENT_ERROR",
                    "message": error_message or "An unexpected session error occurred.",
                })
                await ctx.room.local_participant.publish_data(
                    payload=error_payload.encode("utf-8"),
                    reliable=True,
                )
                await asyncio.sleep(0.5)
            except Exception as pe:
                logger.warning("Failed to publish error payload to UI: %s", pe)

        # 2. Extract transcript messages from session history
        transcript_turns = []
        if session:
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
            except Exception as te:
                logger.warning("Error extracting session history: %s", te)

        # 3. Update DB session: check turn count, skip summary & timing if < 2 user turns
        if db_session:
            try:
                await SessionProcessorService.finish_session_and_enqueue_summary(
                    session_id=db_session.id,
                    transcript_messages=transcript_turns,
                    status=status,
                )
            except Exception as se:
                logger.error("Failed to wrap database session %s: %s", db_session.id, se, exc_info=True)

        # 4. Kill the session immediately
        if session:
            try:
                if hasattr(session, "aclose"):
                    await session.aclose()
            except Exception as ae:
                logger.debug("Error closing agent session: %s", ae)

        try:
            if ctx.room and ctx.room.isconnected():
                await ctx.room.disconnect()
        except Exception as de:
            logger.debug("Error disconnecting room: %s", de)

        # 5. Shut down JobContext
        try:
            ctx.shutdown(reason=f"Session terminated: status={status}, error={error_code}")
        except Exception as sde:
            logger.debug("Error shutting down JobContext: %s", sde)

    try:
        # 1. Connect to the room
        await ctx.connect()

        # 2. Wait for the user to join
        participant = await ctx.wait_for_participant()

        # 3. Parse JSON metadata sent by frontend
        metadata = {}
        if participant.metadata:
            try:
                metadata = json.loads(participant.metadata)
            except json.JSONDecodeError:
                pass

        selected_language = metadata.get("language", "english")
        selected_topic = metadata.get("topic", "daily-life")
        skill_level = metadata.get("skillLevel", "intermediate")
        selected_voice = metadata.get("voice", "shubh")

        # Get access token from metadata
        user_access_token = metadata.get("access_token")
        if not user_access_token:
            logger.error("No access token provided in metadata")
            await wrap_session_and_kill(
                status="failed",
                error_code="AUTH_REQUIRED",
                error_message="Authentication required: Please log in to start a practice session.",
            )
            return

        # Decode access token
        try:
            payload = decode_access_token(user_access_token)
            user_id = payload.get("user_id")
            if not user_id:
                raise ValueError("Missing user_id in access token payload")
        except Exception as e:
            logger.error("Failed to decode access token: %s", e)
            await wrap_session_and_kill(
                status="failed",
                error_code="AUTH_INVALID",
                error_message="Authentication failed: Invalid or expired access token.",
            )
            return

        # 4. Initialize / link database session
        try:
            db_session = await SessionProcessorService.get_or_create_session(
                user_id=user_id,
                room_id=ctx.room.name,
                metadata=metadata,
            )
        except Exception as e:
            logger.error("Failed to create database session: %s", e)
            await wrap_session_and_kill(
                status="failed",
                error_code="DATABASE_ERROR",
                error_message="Failed to initialize practice session in database.",
            )
            return

        # 5. Initialize providers & AgentSession
        stt_provider = STT(selected_language)
        tts_provider = TTS(selected_language, speaker=selected_voice)

        session = AgentSession(
            stt=stt_provider.stt,
            llm=inference.LLM(model="google/gemma-4-31b-it"),
            tts=tts_provider.tts,
            turn_handling=TurnHandlingOptions(
                turn_detection=inference.TurnDetector(),
            ),
            tts_text_transforms=[
                "filter_markdown",
                "filter_emoji",
                clean_speech_for_tts,
            ],
        )

        agent = Assistant(
            language=selected_language,
            topic=selected_topic,
            skill_level=skill_level,
        )

        # 6. Lifecycle & error event listeners
        ctx.add_shutdown_callback(lambda: wrap_session_and_kill(status="completed"))

        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(p):
            logger.info("Participant %s disconnected from room %s", p.identity, ctx.room.name)
            asyncio.create_task(wrap_session_and_kill(status="completed"))

        @session.on("error")
        def on_session_error(event: ErrorEvent):
            err = getattr(event, "error", event)
            err_str = str(err)
            logger.error("Agent error event: %s", err_str)
            is_tts = "TTS" in type(err).__name__ or "tts" in err_str.lower() or "sarvam" in err_str.lower()
            code = "TTS_ERROR" if is_tts else "AGENT_ERROR"
            msg = "Voice synthesis failed. Please switch voice or retry." if is_tts else f"Agent error: {err_str}"
            asyncio.create_task(wrap_session_and_kill(status="failed", error_code=code, error_message=msg))

        @session.on("close")
        def on_session_close(event: CloseEvent):
            reason = getattr(event, "reason", None)
            err = getattr(event, "error", None)
            if reason == CloseReason.ERROR or err is not None:
                err_str = str(err) if err else "Session terminated due to an error"
                logger.error("Agent session closed with error: %s (reason: %s)", err_str, reason)
                is_tts = "TTS" in str(type(err)) or "tts" in err_str.lower() or "sarvam" in err_str.lower()
                code = "TTS_ERROR" if is_tts else "AGENT_ERROR"
                msg = "Voice synthesis failed. Please switch voice or retry." if is_tts else f"Session terminated: {err_str}"
                asyncio.create_task(wrap_session_and_kill(status="failed", error_code=code, error_message=msg))
            else:
                asyncio.create_task(wrap_session_and_kill(status="completed"))

        # 7. Start session in room
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

        # 8. Initial greeting
        await session.generate_reply(
            instructions=(
                f"Warmly greet the user in {selected_language}, introduce yourself as their conversation partner, "
                f"and ask an opening question about {selected_topic}. Speak in pure conversational text only without "
                f"any asterisks, markdown formatting, emojis, or stage directions."
            )
        )

    except Exception as exc:
        logger.exception("Exception in rtc_entrypoint lifecycle: %s", exc)
        err_str = str(exc)
        is_tts = "TTS" in type(exc).__name__ or "tts" in err_str.lower() or "sarvam" in err_str.lower()
        code = "TTS_ERROR" if is_tts else "AGENT_ERROR"
        msg = "Voice synthesis failed from provider. Please switch voice or retry." if is_tts else f"Session error: {err_str}"
        await wrap_session_and_kill(status="failed", error_code=code, error_message=msg)
