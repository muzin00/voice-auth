import logging

from vca_core.interfaces.worker_client import WorkerClientProtocol
from vca_core.utils import normalize_text

from vca_infra.model_loader import get_speaker_model, get_whisper_model
from vca_infra.services import TranscriptionService, VoiceprintService

logger = logging.getLogger(__name__)


class DirectWorkerClient(WorkerClientProtocol):
    """Workerを直接呼び出すクライアント（Celery非経由）."""

    def transcribe(self, audio_bytes: bytes, audio_format: str = "wav") -> str:
        """音声を文字起こし.

        Args:
            audio_bytes: 音声データ
            audio_format: 音声フォーマット（wav, webm, mp3等）

        Returns:
            文字起こしテキスト（正規化済み）
        """
        logger.info(
            f"Starting transcription: {len(audio_bytes)} bytes, format={audio_format}"
        )
        model = get_whisper_model()
        service = TranscriptionService(model)
        text = service.transcribe(audio_bytes, audio_format)

        # テキスト正規化
        normalized = normalize_text(text)
        logger.info(f"Transcription complete: '{normalized}'")
        return normalized

    def extract_voiceprint(
        self, audio_bytes: bytes, audio_format: str = "wav"
    ) -> bytes:
        """声紋を抽出.

        Args:
            audio_bytes: 音声データ
            audio_format: 音声フォーマット（wav, webm, mp3等）

        Returns:
            声紋ベクトル（256次元のfloat32、1024バイト）
        """
        logger.info(
            f"Starting voiceprint extraction: {len(audio_bytes)} bytes, format={audio_format}"
        )
        speaker = get_speaker_model()
        service = VoiceprintService(speaker)
        embedding = service.extract(audio_bytes, audio_format)
        logger.info(f"Voiceprint extraction complete: {len(embedding)} bytes")
        return embedding
