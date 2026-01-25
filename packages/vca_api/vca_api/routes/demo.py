from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from vca_core.services.auth_service import AuthService

from vca_api.dependencies.auth import get_auth_service

# テンプレートディレクトリのパス
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """デモ画面を表示."""
    return templates.TemplateResponse("demo/index.html", {"request": request})


@router.post("/register", response_class=HTMLResponse)
async def demo_register(
    request: Request,
    speaker_id: str = Form(...),
    speaker_name: str = Form(None),
    audio_data: str = Form(...),
    audio_format: str = Form("webm"),
    auth_service: AuthService = Depends(get_auth_service),
):
    """登録デモ."""
    try:
        result = auth_service.register(
            speaker_id=speaker_id,
            audio_data=audio_data,
            audio_format=audio_format,
            speaker_name=speaker_name,
        )
        return templates.TemplateResponse(
            "demo/partials/result.html",
            {
                "request": request,
                "success": True,
                "action": "登録",
                "data": {
                    "speaker_id": result.speaker.speaker_id,
                    "voiceprint_id": result.voiceprint.public_id,
                },
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            "demo/partials/result.html",
            {"request": request, "success": False, "action": "登録", "error": str(e)},
        )


@router.post("/verify", response_class=HTMLResponse)
async def demo_verify(
    request: Request,
    speaker_id: str = Form(...),
    audio_data: str = Form(...),
    audio_format: str = Form("webm"),
    auth_service: AuthService = Depends(get_auth_service),
):
    """認証デモ."""
    try:
        result = auth_service.verify(
            speaker_id=speaker_id,
            audio_data=audio_data,
            audio_format=audio_format,
        )
        return templates.TemplateResponse(
            "demo/partials/result.html",
            {
                "request": request,
                "success": True,
                "action": "認証",
                "data": {
                    "authenticated": result.authenticated,
                    "speaker_id": result.speaker_id,
                    "voice_similarity": result.voice_similarity,
                    "message": result.message,
                },
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            "demo/partials/result.html",
            {"request": request, "success": False, "action": "認証", "error": str(e)},
        )
