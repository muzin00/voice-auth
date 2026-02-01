from fastapi import APIRouter, Depends, status
from vca_auth.services import AuthService

from vca_api.dependencies.auth import get_auth_service
from vca_api.schemas.auth import (
    AuthRegisterRequest,
    AuthRegisterResponse,
    AuthVerifyRequest,
    AuthVerifyResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=AuthRegisterResponse,
)
async def register(
    request: AuthRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthRegisterResponse:
    """話者登録（音声ファイル + 声紋）."""
    result = auth_service.register(
        speaker_id=request.speaker_id,
        audio_data=request.audio_data,
        audio_format=request.audio_format or "wav",
        speaker_name=request.speaker_name,
    )

    return AuthRegisterResponse(
        speaker_id=result.speaker.speaker_id,
        speaker_name=result.speaker.speaker_name,
        voiceprint_id=result.voiceprint.public_id,
        status="registered",
    )


@router.post("/verify", response_model=AuthVerifyResponse)
async def verify(
    request: AuthVerifyRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthVerifyResponse:
    """認証（1:1照合）."""
    result = auth_service.verify(
        speaker_id=request.speaker_id,
        audio_data=request.audio_data,
        audio_format=request.audio_format or "wav",
    )

    return AuthVerifyResponse(
        authenticated=result.authenticated,
        speaker_id=result.speaker_id,
        voice_similarity=result.voice_similarity,
        message=result.message,
    )
