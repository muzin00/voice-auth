from pydantic import BaseModel, Field


class VoiceRegistrationRequest(BaseModel):
    """音声登録リクエスト."""

    speaker_id: str = Field(
        ...,
        description="話者ID（一意識別子）",
        min_length=1,
        max_length=100,
    )
    speaker_name: str | None = Field(
        None,
        description="話者名（オプショナル）",
        max_length=100,
    )
    audio_data: str = Field(
        ...,
        description="音声データ（Base64エンコード）",
        min_length=1,
    )


class VoiceRegistrationResponse(BaseModel):
    """音声登録レスポンス."""

    voice_id: str = Field(..., description="登録された音声ID")
    speaker_id: str = Field(..., description="話者ID")
    speaker_name: str | None = Field(None, description="話者名")
    status: str = Field(..., description="登録ステータス")
