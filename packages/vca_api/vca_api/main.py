"""FastAPI application for VCA Server."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine
from vca_infra.settings import db_settings

from .settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Initializes database tables on startup.
    """
    # Create database tables
    engine = create_engine(db_settings.database_url)
    SQLModel.metadata.create_all(engine)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="VCA Server",
        description="Voice Cognition Authentication Server",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Check server health status."""
        return {"status": "healthy", "version": "1.0.0"}

    # Import and include routers
    from .websocket.enrollment import router as enrollment_router

    app.include_router(enrollment_router)

    return app


def run_server() -> None:
    """Run the server using uvicorn."""
    app = create_app()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )


# Application instance for ASGI servers
app = create_app()
