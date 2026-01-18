import logging
import tempfile
from typing import TYPE_CHECKING

from vca_infra.settings import whisper_settings

if TYPE_CHECKING:
    from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class TranscriptionService:
    """文字起こしサービス."""

    def __init__(self, model: "WhisperModel"):
        self.model = model

    def transcribe(self, audio_bytes: bytes) -> str:
        """音声バイト列を文字起こし.

        Args:
            audio_bytes: 音声データ（WAV, MP3等）

        Returns:
            文字起こしテキスト
        """
        logger.info(f"Transcribing audio: {len(audio_bytes)} bytes")

        # faster-whisperはファイルパスが必要なので一時ファイル経由
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            f.write(audio_bytes)
            f.flush()

            segments, _info = self.model.transcribe(  # type: ignore[reportUnknownMemberType]
                f.name,
                language=whisper_settings.WHISPER_LANGUAGE,
            )

            # セグメントを結合
            text = "".join(segment.text for segment in segments)

        logger.info(f"Transcription complete: {len(text)} characters")
        return text
