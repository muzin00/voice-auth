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
        description="音声データ（Base64エンコードまたはData URL形式）",
        min_length=1,
    )
    audio_format: str | None = Field(
        default=None,
        description="音声フォーマット（省略時は自動判定）",
        pattern="^(wav|mp3|ogg|webm|aac|flac|m4a)$",
    )
    sample_rate: int | None = Field(
        default=None,
        description="サンプリングレート（Hz）例: 16000, 44100, 48000",
        ge=8000,
        le=96000,
    )
    channels: int | None = Field(
        default=None,
        description="チャンネル数（1=モノラル, 2=ステレオ）",
        ge=1,
        le=2,
    )


class VoiceRegistrationResponse(BaseModel):
    """音声登録レスポンス."""

    voice_id: str = Field(..., description="登録された音声ID")
    speaker_id: str = Field(..., description="話者ID")
    speaker_name: str | None = Field(None, description="話者名")
    status: str = Field(..., description="登録ステータス")
