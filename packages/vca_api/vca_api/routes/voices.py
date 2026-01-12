from fastapi import APIRouter, Depends
from vca_core.services.speaker_service import SpeakerService

from vca_api.dependencies.speaker import get_speaker_service
from vca_api.schemas.voices import VoiceRegistrationRequest, VoiceRegistrationResponse

router = APIRouter(prefix="/api/v1/voices", tags=["voices"])


@router.post("/register", status_code=201, response_model=VoiceRegistrationResponse)
async def register_voice(
    request: VoiceRegistrationRequest,
    speaker_service: SpeakerService = Depends(get_speaker_service),
) -> VoiceRegistrationResponse:
    # Speaker を登録
    speaker = speaker_service.register_speaker(
        speaker_id=request.speaker_id,
        speaker_name=request.speaker_name,
    )

    # TODO: 音声データの処理 (audio_data)

    return VoiceRegistrationResponse(
        voice_id="voice_stub_12345",  # TODO: 実装
        speaker_id=speaker.speaker_id,
        speaker_name=speaker.speaker_name,
        status="registered",
    )
