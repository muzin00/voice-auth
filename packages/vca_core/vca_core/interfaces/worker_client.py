from typing import Protocol


class WorkerClientProtocol(Protocol):
    """Workerクライアントのプロトコル."""

    def transcribe(self, audio_bytes: bytes, audio_format: str = "wav") -> str:
        """音声を文字起こし.

        Args:
            audio_bytes: 音声データ
            audio_format: 音声フォーマット（wav, webm, mp3等）

        Returns:
            文字起こしテキスト（正規化済み）
        """
        ...

    def extract_voiceprint(
        self, audio_bytes: bytes, audio_format: str = "wav"
    ) -> bytes:
        """声紋を抽出.

        Args:
            audio_bytes: 音声データ
            audio_format: 音声フォーマット（wav, webm, mp3等）

        Returns:
            声紋ベクトル（256次元）
        """
        ...
