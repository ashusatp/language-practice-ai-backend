from app.job_worker import job_worker
from app.agent_worker import agent_worker_manager
import logging
from config import config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.apis import auth, content, livekit, profile, session, user
from contextlib import asynccontextmanager


# Configure centralized root logger
logging.basicConfig(
    level=config.log_level.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan managing startup and shutdown tasks."""
    logger.info("Initializing FastAPI application (%s)...", config.environment)

    # If configured, run LiveKit agent worker in background thread
    if config.run_agent_worker_with_api:
        logger.info("Auto-start agent worker enabled. Launching worker thread...")
        agent_worker_manager.start()
    else:
        logger.info(
            "Agent worker auto-start disabled (RUN_AGENT_WORKER_WITH_API=false). "
            "Running in standalone API mode."
        )

    # If configured, run PostgreSQL queue worker for summaries/background jobs
    if config.run_job_worker_with_api:
        logger.info("Auto-start job queue worker enabled. Launching SKIP LOCKED queue worker...")
        job_worker.start()

    yield

    logger.info("Shutting down FastAPI application...")
    if config.run_job_worker_with_api:
        await job_worker.stop()
    if config.run_agent_worker_with_api:
        agent_worker_manager.stop()
    logger.info("Application shutdown complete.")



def create_app() -> FastAPI:
    """Application factory for FastAPI."""
    app = FastAPI(
        title="Call Engine API Portal",
        version="0.1.0",
        description="FastAPI Backend & Agent Management Portal",
        lifespan=lifespan,
        debug=config.debug,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust for production origins as needed
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers
    from app.exceptions.handlers import register_exception_handlers
    register_exception_handlers(app)

    # Register API routes
    app.include_router(auth.router)
    app.include_router(user.router)
    app.include_router(livekit.router)
    app.include_router(session.router)
    app.include_router(content.router)
    app.include_router(profile.router)

    # Convenience root health check
    @app.get("/health", tags=["Health"])
    async def root_health():
        return {
            "status": "healthy",
            "environment": config.environment,
            "worker_bundled": config.run_agent_worker_with_api,
        }

    return app


app = create_app()
