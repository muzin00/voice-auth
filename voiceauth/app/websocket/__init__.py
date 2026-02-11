"""WebSocket handlers."""

from voiceauth.app.websocket.enrollment import router as enrollment_router
from voiceauth.app.websocket.verify import router as verify_router

__all__ = ["enrollment_router", "verify_router"]
