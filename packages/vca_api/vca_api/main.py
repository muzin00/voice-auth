"""FastAPI application for VCA Server."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, create_engine
from vca_infra.settings import db_settings

from .settings import settings

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"


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

    # Root redirect to demo
    @app.get("/")
    async def root() -> RedirectResponse:
        """Redirect root to demo page."""
        return RedirectResponse(url="/demo/")

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Check server health status."""
        return {"status": "healthy", "version": "1.0.0"}

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Import and include routers
    from .routes.demo import router as demo_router
    from .websocket.enrollment import router as enrollment_router
    from .websocket.verify import router as verify_router

    app.include_router(demo_router)
    app.include_router(enrollment_router)
    app.include_router(verify_router)

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
