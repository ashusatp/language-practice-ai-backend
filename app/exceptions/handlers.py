from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.exceptions.custom import AppException


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers on the FastAPI app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )
