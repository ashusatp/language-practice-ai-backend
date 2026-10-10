from sqlalchemy.ext.asyncio import AsyncSession
import json
from config import config
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
        room_id: str,
        participant_identity: str = "",
        user_id: Optional[str] = None,
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

            target_user = user_id or participant_identity
            user_uuid = None
            if target_user:
                try:
                    user_uuid = uuid.UUID(str(target_user))
                except (ValueError, TypeError):
                    user_uuid = None

            selected_language = metadata.get("language", "english")
            selected_topic = metadata.get("topic", "daily-life")
            selected_voice = metadata.get("voice", "shubh")

            # Match voice by name or voice_id with fallback to first active voice
            voice_stmt = select(Voice).where(
                (Voice.voice_id.ilike(selected_voice)) | (Voice.name.ilike(selected_voice))
            )
            voice_res = await db.execute(voice_stmt)
            voice = voice_res.scalar_one_or_none()
            if not voice:
                voice_fallback = await db.execute(select(Voice).where(Voice.is_active == True).limit(1))
                voice = voice_fallback.scalar_one_or_none()
                if not voice:
                    raise ValueError(f"Voice not found: {selected_voice}")

            # Match language by code or name with fallback to first active language
            lang_stmt = select(Language).where(
                (Language.code.ilike(selected_language))
                | (Language.name.ilike(f"%{selected_language}%"))
                | (Language.code.ilike(f"%{selected_language[:2]}%"))
            )
            language_res = await db.execute(lang_stmt)
            language = language_res.scalar_one_or_none()
            if not language:
                lang_fallback = await db.execute(select(Language).where(Language.is_active == True).limit(1))
                language = lang_fallback.scalar_one_or_none()
                if not language:
                    raise ValueError(f"Language not found: {selected_language}")

            session = Session(
                room_id=room_id,
                started_by=user_uuid,
                language_id=language.id,
                voice_id=voice.id,
                topic=selected_topic,
                status="active",
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
            logger.info("Session %s registered for room %s (started_by=%s)", session.id, room_id, user_uuid)
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


    @staticmethod
    async def _generate_ai_summary(transcript: list[dict[str, Any]]) -> dict[str, Any]:
        """Generates summary, sentiment, key points, mistakes, and dynamic scores from conversation."""
        user_turns = [t.get("text", "") for t in transcript if t.get("role") in ("user", "human")]
        word_count = sum(len(text.split()) for text in user_turns)

        if not transcript or not user_turns or word_count == 0:
            return {
                "summary": "The practice session was initiated, but no speech was detected from the learner.",
                "sentiment": "neutral",
                "key_points": [
                    "Session was started successfully with the voice assistant.",
                    "No spoken input was captured from the microphone.",
                ],
                "action_items": [
                    "Ensure microphone permissions are granted in the browser.",
                    "Practice answering the assistant's opening questions out loud.",
                ],
                "mistakes": [],
                "scores": {
                    "overall": 3.0,
                    "fluency": 3.0,
                    "pronunciation": 3.0,
                    "grammar": 3.0,
                    "vocabulary": 3.0,
                },
                "key_vocabulary": [],
            }

        # Build clean dialogue text
        conversation_text = "\n".join(
            [f"{turn.get('role', 'speaker').capitalize()}: {turn.get('text', '')}" for turn in transcript]
        )

        # Attempt OpenAI if key is configured
        if config.openai_api_key:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=config.openai_api_key)
                prompt = (
                    "You are an expert language proficiency tutor evaluating a real conversation transcript between a learner ('User') and an AI conversation partner ('Assistant').\n\n"
                    "Carefully analyze what the User said and return a JSON object with:\n"
                    "- 'summary': A comprehensive 2-3 sentence overview of how the learner communicated, their fluency, and main topics discussed.\n"
                    "- 'sentiment': 'positive', 'neutral', or 'constructive'.\n"
                    "- 'key_points': list of 3-4 key strengths or conversational highlights demonstrated by the user.\n"
                    "- 'action_items': list of 2-3 specific practice tips or focus areas for their next session.\n"
                    "- 'key_vocabulary': list of 4-6 notable, advanced, or relevant vocabulary words used or suitable for this practice topic (e.g., ['Perspective', 'Consequently', 'Substantial', 'Articulation']).\n"
                    "- 'mistakes': list of up to 4 actual linguistic or grammar mistakes made by the User during the conversation. Each mistake must be an object with:\n"
                    "   * 'spoken': the exact words or phrase the user said\n"
                    "   * 'correction': the natural, grammatically correct native phrasing\n"
                    "   * 'explanation': a clear, friendly explanation of why the correction is better\n"
                    "   * 'type': 'grammar' | 'vocabulary' | 'pronunciation'\n"
                    "   If the user made no noticeable mistakes, return an empty array [].\n"
                    "- 'scores': an object with realistic ratings from 1.0 to 5.0 (decimals allowed, e.g., 4.2):\n"
                    "   * 'overall': float (1.0 to 5.0)\n"
                    "   * 'fluency': float (1.0 to 5.0)\n"
                    "   * 'pronunciation': float (1.0 to 5.0)\n"
                    "   * 'grammar': float (1.0 to 5.0)\n"
                    "   * 'vocabulary': float (1.0 to 5.0)\n\n"
                    f"Transcript:\n{conversation_text}\n\n"
                    "Respond with ONLY valid JSON."
                )
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                )
                content = resp.choices[0].message.content
                if content:
                    parsed = json.loads(content)
                    if "mistakes" not in parsed:
                        parsed["mistakes"] = []
                    if "key_vocabulary" not in parsed:
                        parsed["key_vocabulary"] = ["Perspective", "Consequently", "Substantial", "Articulation"]
                    if "scores" not in parsed:
                        parsed["scores"] = {
                            "overall": 4.5,
                            "fluency": 4.5,
                            "pronunciation": 4.5,
                            "grammar": 4.5,
                            "vocabulary": 4.5,
                        }
                    return parsed
            except Exception as e:
                logger.warning("OpenAI summary generation failed, falling back to heuristic: %s", e)

        # Intelligent structured fallback analyzer
        turns_count = len(transcript)
        user_turns_count = len(user_turns)

        # Calculate heuristic scores based on engagement
        fluency = min(5.0, max(2.5, round(3.0 + (word_count / 30.0) * 1.5, 1)))
        grammar = min(5.0, max(3.0, round(3.5 + min(1.0, user_turns_count * 0.2), 1)))
        pronunciation = min(5.0, max(3.0, round(3.8 + min(1.0, user_turns_count * 0.15), 1)))
        vocabulary = min(5.0, max(2.8, round(3.2 + (word_count / 40.0) * 1.2, 1)))
        overall = round((fluency + pronunciation + grammar + vocabulary) / 4.0, 1)

        summary = (
            f"The participant engaged in a conversation with {turns_count} total turns and approximately "
            f"{word_count} words spoken. Topics were explored interactively with the voice agent."
        )

        key_points = [
            f"Completed {user_turns_count} user speech exchanges with the voice assistant.",
            "Demonstrated active listening and responded to prompt questions.",
            "Maintained conversational flow across dialogue turns.",
        ]

        action_items = [
            "Practice expanding answers with descriptive examples.",
            "Focus on varied vocabulary and fluent pacing.",
        ]

        return {
            "summary": summary,
            "sentiment": "positive" if word_count > 15 else "neutral",
            "key_points": key_points,
            "action_items": action_items,
            "mistakes": [],
            "scores": {
                "overall": overall,
                "fluency": fluency,
                "pronunciation": pronunciation,
                "grammar": grammar,
                "vocabulary": vocabulary,
            },
            "key_vocabulary": ["Perspective", "Consequently", "Substantial", "Articulation"],
        }

    @staticmethod
    async def update_user_language_proficiency(
        db: AsyncSession,
        user_id: uuid.UUID,
        scores: dict[str, Any],
        language_id: Optional[uuid.UUID] = None,
        duration_mins: int = 1,
    ) -> Any:
        """Updates user's language-specific proficiency ratings (out of 5 stars) using a recency-weighted rolling average."""
        from app.models.language import Language
        from app.models.profile import UserLanguageProficiency

        # If language_id not provided, fallback to first active language
        if not language_id:
            lang_stmt = select(Language).where(Language.is_active == True).limit(1)
            lang_res = await db.execute(lang_stmt)
            default_lang = lang_res.scalar_one_or_none()
            if default_lang:
                language_id = default_lang.id

        if not language_id:
            logger.warning("Cannot update language proficiency: No language found.")
            return None

        def _calc_rolling_rating(old_rating: float, new_score: float, session_count: int) -> float:
            if session_count == 0 or old_rating == 0.0:
                return round(float(new_score), 2)
            # Recency-weighted rolling average with effective window capped at 10 sessions
            n = min(session_count, 10)
            updated = ((old_rating * n) + float(new_score)) / (n + 1)
            return round(min(5.0, max(1.0, updated)), 2)

        prof_stmt = select(UserLanguageProficiency).where(
            UserLanguageProficiency.user_id == user_id,
            UserLanguageProficiency.language_id == language_id,
        )
        prof_res = await db.execute(prof_stmt)
        proficiency = prof_res.scalar_one_or_none()

        if not proficiency:
            proficiency = UserLanguageProficiency(
                user_id=user_id,
                language_id=language_id,
                overall_rating=0.0,
                fluency_rating=0.0,
                grammar_rating=0.0,
                pronunciation_rating=0.0,
                vocabulary_rating=0.0,
                total_sessions=0,
                total_minutes=0,
            )
            db.add(proficiency)
            await db.flush()

        # Extract scores
        fluency = float(scores.get("fluency", 3.5))
        grammar = float(scores.get("grammar", 3.5))
        pronunciation = float(scores.get("pronunciation", 3.5))
        vocabulary = float(scores.get("vocabulary", 3.5))

        proficiency.fluency_rating = _calc_rolling_rating(proficiency.fluency_rating, fluency, proficiency.total_sessions)
        proficiency.grammar_rating = _calc_rolling_rating(proficiency.grammar_rating, grammar, proficiency.total_sessions)
        proficiency.pronunciation_rating = _calc_rolling_rating(proficiency.pronunciation_rating, pronunciation, proficiency.total_sessions)
        proficiency.vocabulary_rating = _calc_rolling_rating(proficiency.vocabulary_rating, vocabulary, proficiency.total_sessions)

        # Overall proficiency for this specific language is the average of 4 core language competencies (out of 5 stars)
        proficiency.overall_rating = round(
            (proficiency.fluency_rating + proficiency.grammar_rating + proficiency.pronunciation_rating + proficiency.vocabulary_rating) / 4.0,
            2,
        )

        proficiency.total_sessions += 1
        proficiency.total_minutes += max(1, duration_mins)

        logger.info(
            "Updated UserLanguageProficiency for user %s (language_id=%s): overall=%.2f (fluency=%.2f, grammar=%.2f, pronunciation=%.2f, vocabulary=%.2f, sessions=%d)",
            user_id,
            language_id,
            proficiency.overall_rating,
            proficiency.fluency_rating,
            proficiency.grammar_rating,
            proficiency.pronunciation_rating,
            proficiency.vocabulary_rating,
            proficiency.total_sessions,
        )
        return proficiency