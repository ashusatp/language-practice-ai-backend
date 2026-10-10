import logging
from config import config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.apis import auth


# Configure centralized root logger
logging.basicConfig(
    level=config.log_level.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")


def create_app() -> FastAPI:
    """Application factory for FastAPI."""
    app = FastAPI(
        title="Call Engine API Portal",
        version="0.1.0",
        description="FastAPI Backend & Agent Management Portal",
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
