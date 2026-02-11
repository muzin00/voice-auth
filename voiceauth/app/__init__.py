"""Application layer - FastAPI application and composition root."""

from voiceauth.app.main import app, create_app, run_server

__all__ = ["app", "create_app", "run_server"]
