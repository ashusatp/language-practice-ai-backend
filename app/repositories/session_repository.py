import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Job, Language, Session, SessionFeedback
from app.types.session import (
    SessionHistoryItemResponse,
    SessionHistoryListResponse,
    SessionLanguageSummary,
    SessionStatusResponse,
    SessionVoiceSummary,
)


class SessionRepository:
    def __init__(self , db: AsyncSession): 
        self.db = db
        
    async def get_user_sessions(self, user_id: uuid.UUID, offset: int, limit: int,  language_filter: Optional[str]) -> SessionHistoryListResponse:
        base_query = select(Session).where(Session.started_by == user_id)

        if language_filter:
            try:
                lang_uuid = uuid.UUID(language_filter)
                base_query = base_query.where(Session.language_id == lang_uuid)
            except ValueError:
                base_query = base_query.join(Session.language).where(Language.code == language_filter)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_count = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            base_query.order_by(Session.started_at.desc())
            .offset(offset)
            .limit(limit)
            .options(
                selectinload(Session.language),
                selectinload(Session.voice),
                selectinload(Session.feedback),
            )
        )

        res = await self.db.execute(stmt)
        sessions = res.scalars().all()

        items: list[SessionHistoryItemResponse] = []
        for s in sessions:
            fb = s.feedback
            duration_sec = (
                int((s.ended_at - s.started_at).total_seconds())
                if s.ended_at and s.started_at
                else 0
            )

            lang_summary = None
            if s.language:
                lang_summary = SessionLanguageSummary(
                    id=s.language.id,
                    code=s.language.code,
                    name=s.language.name,
                )

            voice_summary = None
            if s.voice:
                voice_summary = SessionVoiceSummary(
                    id=s.voice.voice_id,
                    name=s.voice.name,
                    gender=(s.voice.gender or "female").capitalize(),
                )

            formatted_transcript = []
            if s.transcript:
                for turn in s.transcript:
                    role = turn.get("role", "speaker")
                    speaker = "you" if role in ("user", "human") else "ai"
                    text_content = turn.get("text", "")
                    timestamp = turn.get("timestamp") or turn.get("time") or ""
                    formatted_transcript.append({
                        "speaker": speaker,
                        "text": text_content,
                        "time": timestamp,
                    })

            scores = fb.scores if fb and fb.scores else None
            overall_rating = scores.get("overall") if scores else None

            items.append(
                SessionHistoryItemResponse(
                    id=s.id,
                    room_id=s.room_id,
                    started_at=s.started_at,
                    ended_at=s.ended_at,
                    duration_seconds=duration_sec,
                    language=lang_summary,
                    voice=voice_summary,
                    topic=s.topic or "General Conversation",
                    overall_rating=overall_rating,
                    user_rating=fb.user_rating if fb else None,
                    scores=scores,
                    summary=fb.summary if fb else None,
                    sentiment=fb.sentiment if fb else None,
                    mistakes_count=len(fb.mistakes) if fb and fb.mistakes else 0,
                    key_points=fb.key_points if fb else [],
                    action_items=fb.action_items if fb else [],
                    mistakes=fb.mistakes if fb else [],
                    key_vocabulary=fb.key_vocabulary if fb else [],
                    transcript=formatted_transcript if formatted_transcript else s.transcript,
                )
            )

        return SessionHistoryListResponse(total=total_count, items=items)
    
        
    async def get_session_by_id_or_room(self, identifier: str) -> Optional[Session]:
        """Fetch a session by UUID id or room_id, with feedback, language, and voice eagerly loaded."""
        try:
            session_uuid = uuid.UUID(str(identifier))
            condition = (Session.id == session_uuid) | (Session.room_id == str(identifier))
        except (ValueError, AttributeError):
            condition = (Session.room_id == str(identifier))

        stmt = (
            select(Session)
            .where(condition)
            .options(
                selectinload(Session.feedback),
                selectinload(Session.language),
                selectinload(Session.voice),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    # Alias so both method names work seamlessly
    get_session_by_id = get_session_by_id_or_room

    async def get_session_status_by_room_id(self, room_id: str) -> SessionStatusResponse:
        base_query = select(Session).where(Session.room_id == room_id)

        res = await self.db.execute(base_query)
        session = res.scalar_one_or_none()
        
        if not session:
            return SessionStatusResponse(
                session_id=None,
                room_id=room_id,
                session_status="connecting",
                job_status="pending",
                is_ready=False,
                error_message=None,
            )

        # Check the latest summary generation job for this session
        job_stmt = (
            select(Job)
            .where(Job.session_id == session.id, Job.type == "generate_summary")
            .order_by(Job.created_at.desc())
        )
        job_res = await self.db.execute(job_stmt)
        latest_job = job_res.scalars().first()

        # Check if feedback record already exists
        fb_stmt = select(SessionFeedback).where(SessionFeedback.session_id == session.id)
        fb_res = await self.db.execute(fb_stmt)
        feedback = fb_res.scalar_one_or_none()

        # Session is ready if feedback summary exists, or if the session is completed without background jobs (e.g. 0-turn session)
        is_ready = (
            (feedback is not None and feedback.summary is not None)
            or (session.status == "completed" and latest_job is None)
        )

        job_status = (
            "completed"
            if is_ready
            else (latest_job.status if latest_job else ("completed" if session.status == "completed" else "pending"))
        )

        return SessionStatusResponse(
            session_id=session.id,
            room_id=session.room_id,
            session_status=session.status,
            job_status=job_status,
            is_ready=is_ready,
            error_message=latest_job.error_message if latest_job else None,
        )

    async def update_session_rating(
        self,
        session_id: uuid.UUID,
        rating: Optional[int],
        user_review: Optional[str],
    ) -> SessionFeedback:
        stmt = select(SessionFeedback).where(SessionFeedback.session_id == session_id)
        res = await self.db.execute(stmt)
        feedback = res.scalar_one_or_none()

        if not feedback:
            feedback = SessionFeedback(
                session_id=session_id,
                user_rating=rating,
                user_review=user_review,
            )
            self.db.add(feedback)
        else:
            if rating is not None:
                feedback.user_rating = rating
            if user_review is not None:
                feedback.user_review = user_review

        await self.db.commit()
        await self.db.refresh(feedback)
        return feedback
    
    async def get_completed_sessions(self, user_id: Any) -> list:
        """Fetch all completed sessions for a user."""
        target_id = getattr(user_id, "id", user_id)
        if isinstance(target_id, str):
            try:
                target_id = uuid.UUID(target_id)
            except ValueError:
                pass

        stmt = (
            select(Session.started_at)
            .where(
                Session.started_by == target_id,
                Session.status == "completed",
                or_(
                    Session.ended_at != Session.started_at,
                    Session.ended_at.is_(None),
                ),
            )
            .order_by(Session.started_at.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())