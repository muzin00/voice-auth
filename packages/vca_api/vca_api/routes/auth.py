from fastapi import APIRouter, Depends
from vca_core.services.auth_service import AuthService

from vca_api.dependencies.auth import get_auth_service
from vca_api.schemas.auth import AuthRegisterRequest, AuthRegisterResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=AuthRegisterResponse)
async def register(
    request: AuthRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthRegisterResponse:
    """話者登録（音声ファイル + パスフレーズ + 声紋）."""
    result = auth_service.register(
        speaker_id=request.speaker_id,
        audio_data=request.audio_data,
        audio_format=request.audio_format or "wav",
        speaker_name=request.speaker_name,
    )

    return AuthRegisterResponse(
        speaker_id=result.speaker.speaker_id,
        speaker_name=result.speaker.speaker_name,
        voice_sample_id=result.voice_sample.public_id,
        voiceprint_id=result.voiceprint.public_id,
        passphrase=result.passphrase.phrase,
        status="registered",
    )
