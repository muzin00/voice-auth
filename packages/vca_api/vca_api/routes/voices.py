from fastapi import APIRouter

from vca_api.schemas.voices import VoiceRegistrationRequest, VoiceRegistrationResponse

router = APIRouter(prefix="/api/v1/voices", tags=["voices"])


@router.post("/register", status_code=201, response_model=VoiceRegistrationResponse)
async def register_voice(
    request: VoiceRegistrationRequest,
) -> VoiceRegistrationResponse:
    return VoiceRegistrationResponse(
        voice_id="voice_stub_12345",
        speaker_id=request.speaker_id,
        speaker_name=request.speaker_name,
        status="registered",
    )
