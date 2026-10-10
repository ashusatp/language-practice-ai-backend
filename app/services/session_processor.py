from datetime import datetime, timezone
import logging
import uuid
from typing import Any, Optional

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Job, Language, Session, Voice

logger = logging.getLogger("app.services.session_processor")

class SessionProcessorService:
    @staticmethod
    async def get_or_create_session(
        user_id: str,
        room_id: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Session:
        
        metadata = metadata or {}
        async with AsyncSessionLocal() as db:
            stmt = select(Session).where(Session.room_id == room_id)
            res = await db.execute(stmt)
            session = res.scalar_one_or_none()

            if session: 
                logger.info("Session %s already exists for room %s", session.id, room_id)
                return session

            started_by_id = user_id
            selected_language = metadata.get("language", "english")
            selected_topic = metadata.get("topic", "daily-life")
            skill_level = metadata.get("skillLevel", "intermediate")
            selected_voice = metadata.get("voice", "shubh")

            voice_res = await db.execute(select(Voice).where(Voice.name == selected_voice))
            voice = voice_res.scalar_one_or_none()
            if not voice:
                raise ValueError(f"Voice not found: {selected_voice}")

            language_res = await db.execute(select(Language).where(Language.code == selected_language))
            language = language_res.scalar_one_or_none()
            if not language:
                raise ValueError(f"Language not found: {selected_language}")

            
            if not session:
                session = Session(
                    room_id=room_id,
                    started_by_id= uuid.UUID(str(user_id)),
                    language_id=language.id,
                    voice_id=voice.id,
                    skill_level=skill_level,
                    topic=selected_topic,
                    metadata=metadata,
                )

                db.add(session)
            else:
                # Update with any newly supplied metadata
                if not session.started_by and started_by_id:
                    session.started_by = started_by_id
                if not session.voice_id and voice.id:
                    session.voice_id = voice.id
                if not session.language_id and language.id:
                    session.language_id = language.id
                if selected_topic and not session.topic:
                    session.topic = selected_topic
                if skill_level and not session.skill_level:
                    session.skill_level = skill_level

                session.status = "active"

            
            await db.commit()
            await db.refresh(session)
            logger.info("Session %s registered for room %s (started_by=%s)", session.id, room_id, started_by_id)
            return session

    @staticmethod
    async def finish_session_and_enqueue_summary(
        session_id: uuid.UUID,
        transcript_messages: list[dict[str, Any]],
    ) -> Job:

        async with AsyncSessionLocal() as db:
            stmt = select(Session).where(Session.id == session_id)
            res = await db.execute(stmt)
            session = res.scalar_one_or_none()

            if not session:
                logger.error("Cannot finish session: Session %s not found", session_id)
                raise ValueError(f"Session {session_id} not found")
            
            session.status = "completed"
            session.ended_at = datetime.now(timezone.utc)
            session.transcript = transcript_messages

             # Enqueue the summary generation job (picked up by JobWorker)
            job = Job(
                session_id=session.id,
                type="generate_summary",
                status="pending",
                attempts=0,
                max_attempts=3,
                payload={
                    "session_id": str(session.id),
                    "transcript": transcript_messages,
                },
                run_after=datetime.now(timezone.utc),
            )

            db.add(job)
            await db.commit()
            await db.refresh(job)

            logger.info(
                "Session %s completed. Created Job %s in queue for worker processing.",
                session_id,
                job.id,
            )
        
        return job