import base64
from uuid import uuid4

from vca_core.constants import MAX_AUDIO_SIZE
from vca_core.interfaces.storage import StorageProtocol
from vca_core.interfaces.voice_repository import VoiceRepositoryProtocol
from vca_core.models import Voice


class VoiceService:
    def __init__(
        self,
        voice_repository: VoiceRepositoryProtocol,
        storage: StorageProtocol,
    ):
        self.voice_repository = voice_repository
        self.storage = storage

    def register_voice(
        self,
        speaker_id: int,
        audio_data: str,
        audio_format: str,
        sample_rate: int | None = None,
        channels: int | None = None,
    ) -> Voice:
        # Base64デコード（Data URL形式にも対応）
        if audio_data.startswith("data:"):
            audio_data = audio_data.split(",", 1)[1]

        audio_bytes = base64.b64decode(audio_data)

        # サイズチェック
        if len(audio_bytes) > MAX_AUDIO_SIZE:
            raise ValueError(
                f"Audio size {len(audio_bytes)} bytes exceeds "
                f"maximum {MAX_AUDIO_SIZE} bytes"
            )

        # ストレージに保存
        file_path = f"voices/{speaker_id}/{uuid4()}.{audio_format}"
        storage_path = self.storage.upload(
            data=audio_bytes,
            path=file_path,
            content_type=f"audio/{audio_format}",
        )

        # データベースに登録
        voice = self.voice_repository.create(
            speaker_id=speaker_id,
            audio_file_path=storage_path,
            audio_format=audio_format,
            sample_rate=sample_rate,
            channels=channels,
        )

        return voice
