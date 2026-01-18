from pydantic import BaseModel, Field


class AuthRegisterRequest(BaseModel):
    """話者登録リクエスト."""

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


class AuthRegisterResponse(BaseModel):
    """話者登録レスポンス."""

    speaker_id: str = Field(..., description="話者ID")
    speaker_name: str | None = Field(None, description="話者名")
    voice_sample_id: str = Field(..., description="音声サンプルID")
    voiceprint_id: str = Field(..., description="声紋ID")
    passphrase: str = Field(..., description="抽出されたパスフレーズ")
    status: str = Field(..., description="登録ステータス")


class AuthVerifyRequest(BaseModel):
    """認証リクエスト（1:1照合）."""

    speaker_id: str = Field(
        ...,
        description="話者ID（照合対象）",
        min_length=1,
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


class AuthVerifyResponse(BaseModel):
    """認証レスポンス."""

    authenticated: bool = Field(..., description="認証成功フラグ")
    speaker_id: str = Field(..., description="話者ID")
    passphrase_match: bool = Field(..., description="パスフレーズ一致フラグ")
    voice_similarity: float = Field(..., description="声紋類似度（0.0〜1.0）")
    detected_passphrase: str = Field(..., description="音声から検出されたパスフレーズ")
    message: str = Field(..., description="認証結果メッセージ")
