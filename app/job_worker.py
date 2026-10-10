import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Optional
import uuid
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.services.session_processor import SessionProcessorService

logger = logging.getLogger("app.job_worker")

# PostgreSQL Atomic Dequeue Query with Exponential Backoff and SKIP LOCKED
DEQUEUE_JOB_SQL = text("""
    UPDATE jobs 
    SET attempts = attempts + 1,
        status = 'processing',
        updated_at = NOW(),
        run_after = NOW() + LEAST(
            (INTERVAL '30 seconds') * POWER(2, attempts),
            INTERVAL '1 hour'
        )
    WHERE id = (
        SELECT id FROM jobs 
        WHERE run_after <= NOW()
          AND status IN ('pending', 'processing')
          AND attempts < :max_attempts
        ORDER BY run_after, id
        FOR UPDATE SKIP LOCKED 
        LIMIT 1
    )
    RETURNING id, session_id, type, attempts, max_attempts, payload
""")


class JobWorker:
    """Transactional PostgreSQL background job worker using FOR UPDATE SKIP LOCKED."""

    def __init__(self, poll_interval: float = 2.0, max_attempts: int = 3) -> None:
        self.poll_interval = poll_interval
        self.max_attempts = max_attempts
        self._is_running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Starts the background worker as an asyncio Task."""
        if self._is_running:
            logger.warning("JobWorker is already running.")
            return

        self._is_running = True
        self._task = asyncio.create_task(self.run_loop(), name="PostgresJobWorker")
        logger.info("JobWorker started successfully (poll_interval=%ss).", self.poll_interval)

    async def stop(self, timeout: float = 5.0) -> None:
        """Gracefully stops the worker."""
        if not self._is_running:
            return

        logger.info("Stopping JobWorker...")
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=timeout)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info("JobWorker stopped.")

    async def run_loop(self) -> None:
        """Continuous polling loop."""
        while self._is_running:
            try:
                claimed = await self.process_next_job()
                if not claimed:
                    # Sleep only if no jobs were found to process
                    await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Unexpected error in JobWorker loop: %s", e, exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def process_next_job(self) -> bool:
        """Claims a single pending job using FOR UPDATE SKIP LOCKED and executes it."""
        job_data = None

        # 1. Atomic claim in a dedicated transaction
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                DEQUEUE_JOB_SQL,
                {"max_attempts": self.max_attempts},
            )
            row = res.mappings().first()
            if row:
                job_data = dict(row)
                await session.commit()

        if not job_data:
            return False

        job_id = job_data["id"]
        job_type = job_data["type"]
        session_id = job_data["session_id"]
        attempts = job_data["attempts"]
        max_attempts = job_data["max_attempts"]

        logger.info(
            "Claimed Job %s (type=%s, attempt=%d/%d, session=%s)",
            job_id,
            job_type,
            attempts,
            max_attempts,
            session_id,
        )

        # 2. Execute job handler
        try:
            if job_type == "generate_summary":
                await self._handle_generate_summary(job_data)
                # Delete job once successfully processed
                await self._delete_job(job_id)
            else:
                raise ValueError(f"Unknown job type: {job_type}")

            logger.info("Job %s processed and deleted successfully.", job_id)
            return True

        except Exception as e:
            logger.error("Job %s failed on attempt %d: %s", job_id, attempts, e, exc_info=True)
            await self._mark_failed_or_retry(job_id, attempts, max_attempts, str(e))
            return True

    async def _handle_generate_summary(self, job_data: dict[str, Any]) -> None:
        """Executes the summary generation and saves feedback with mistakes & scores."""
        from sqlalchemy import select
        from app.models.feedback import SessionFeedback
        from app.models.session import Session

        session_id = job_data["session_id"]
        payload = job_data.get("payload") or {}
        transcript = payload.get("transcript")

        async with AsyncSessionLocal() as session:
            if not transcript:
                stmt = select(Session).where(Session.id == session_id)
                res = await session.execute(stmt)
                session_record = res.scalar_one_or_none()
                if not session_record:
                    raise ValueError(f"Session {session_id} not found")
                transcript = session_record.transcript or []

            summary_data = await SessionProcessorService._generate_ai_summary(transcript)

            # Update or create SessionFeedback with all AI conclusions
            fb_stmt = select(SessionFeedback).where(SessionFeedback.session_id == session_id)
            fb_res = await session.execute(fb_stmt)
            feedback = fb_res.scalar_one_or_none()

            if not feedback:
                feedback = SessionFeedback(
                    session_id=session_id,
                    summary=summary_data.get("summary"),
                    sentiment=summary_data.get("sentiment"),
                    key_points=summary_data.get("key_points", []),
                    action_items=summary_data.get("action_items", []),
                    mistakes=summary_data.get("mistakes", []),
                    scores=summary_data.get("scores", {}),
                    key_vocabulary=summary_data.get("key_vocabulary", []),
                    processed_at=datetime.now(timezone.utc),
                )
                session.add(feedback)
            else:
                feedback.summary = summary_data.get("summary")
                feedback.sentiment = summary_data.get("sentiment")
                feedback.key_points = summary_data.get("key_points", [])
                feedback.action_items = summary_data.get("action_items", [])
                feedback.mistakes = summary_data.get("mistakes", [])
                feedback.scores = summary_data.get("scores", {})
                feedback.key_vocabulary = summary_data.get("key_vocabulary", [])
                feedback.processed_at = datetime.now(timezone.utc)

            # Update UserLanguageProficiency ratings if session has a started_by user
            s_stmt = select(Session).where(Session.id == session_id)
            s_res = await session.execute(s_stmt)
            s_rec = s_res.scalar_one_or_none()
            if s_rec and s_rec.started_by:
                duration_mins = 1
                if s_rec.started_at and s_rec.ended_at:
                    duration_mins = max(1, int((s_rec.ended_at - s_rec.started_at).total_seconds() / 60))
                await SessionProcessorService.update_user_language_proficiency(
                    db=session,
                    user_id=s_rec.started_by,
                    scores=summary_data.get("scores", {}),
                    language_id=s_rec.language_id,
                    duration_mins=duration_mins,
                )

            await session.commit()

    async def _delete_job(self, job_id: uuid.UUID) -> None:
        """Deletes the job once successfully processed."""
        from app.models.job import Job
        from sqlalchemy import delete

        async with AsyncSessionLocal() as session:
            await session.execute(delete(Job).where(Job.id == job_id))
            await session.commit()

    async def _mark_failed_or_retry(
        self,
        job_id: uuid.UUID,
        attempts: int,
        max_attempts: int,
        error_msg: str,
    ) -> None:
        """Marks job as failed if max attempts reached, or resets to pending for exponential retry."""
        from app.models.job import Job
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            stmt = select(Job).where(Job.id == job_id)
            res = await session.execute(stmt)
            job = res.scalar_one_or_none()
            if job:
                if attempts >= max_attempts:
                    job.status = "failed"
                else:
                    # Keep pending; run_after has already been updated with exponential backoff!
                    job.status = "pending"
                job.error_message = error_msg
                await session.commit()


# Singleton instance
job_worker = JobWorker()


if __name__ == "__main__":
    # Allows running standalone worker process: python -m app.job_worker
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger.info("Running standalone JobWorker process...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    worker = JobWorker()
    try:
        loop.run_until_complete(worker.run_loop())
    except KeyboardInterrupt:
        logger.info("JobWorker interrupted by user.")
    finally:
        loop.close()
